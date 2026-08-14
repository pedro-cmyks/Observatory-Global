/**
 * What LEVEL is this rail row?
 *
 * P1 established the vocabulary — a **Story** is a dynamic thread (one real
 * event), a **Theme/Category** is the R3 lens that aggregates every story
 * filed under it. The rail never got the visual distinction, so a category
 * row rendered as a peer of the stories beneath it: same title slot, same
 * number slot, same entity chips. Read live by Pedro (2026-08-14), a row
 * reading `Earthquake · EARTHQUAKE OR VOLCANIC DISASTER · 80 · 7d · gated`
 * was taken for a story — its 80 read as that story's signal count and its
 * entity chips (led by US) read as describing the Colombian quake.
 *
 * Two separate mechanisms produced that read, and both are handled here:
 *
 *  1. `threadRowKind` types the row, so a genuine CATEGORY row can carry its
 *     own affordance and its own count basis instead of impersonating a
 *     story. Category rows enter `/threads` whenever the
 *     `ATLAS_THREADS_CATEGORY_ROWS` / `ATLAS_COUNTRY_CATEGORY_ROWS`
 *     kill-switches are flipped on, or through the atlas-only path
 *     (`topic_slug` / multi-country) — see thread_intelligence.fetch_threads.
 *
 *  2. `storyTitle` replaces the old `stripCountrySuffix`, which was the
 *     LIVE cause of the misread: it deleted every trailing " in …" clause,
 *     so `Earthquake in Colombia` (a real dynamic story) rendered as the
 *     bare word `Earthquake` directly under an uppercase
 *     `EARTHQUAKE OR VOLCANIC DISASTER` kicker. The title had been reduced
 *     to a restatement of its own category. Measured on the live rail the
 *     same day: `Houthi Attacks in Yemen` → `Houthi Attacks`, and
 *     `…indicts Nick Reiner in fatal stabbing of parents Rob and Michele
 *     Reiner` → truncated at the first preposition.
 *
 * Pure module: no React, no fetch — the rules are testable on their own.
 */

import type { CountBase } from './countQualifier'

export type ThreadRowKind = 'category' | 'umbrella' | 'story'

export interface ThreadRowKindInput {
    thread_id: string
    /** Dynamic rows carry `dynamic_topics.identity_key` here; an R2 umbrella's
     *  key is `umbrella:<largest active child id>` (R3.3 stable id). */
    anchor_topics?: string[] | null
    /** The story-lens siblings payload states the level directly
     *  (`story-siblings-v1` gained `kind` in Z3), because a lens row is
     *  synthesized from that payload and carries no `identity_key` to read the
     *  umbrella marker off. Never a guess: absent means "not stated". */
    lens_kind?: 'story' | 'family' | null
}

/** An atlas topic slug: lowercase, hyphen-separated, at least two segments
 *  (`earthquake-volcano-disaster`). Same shape `threadVoice.canHaveThreadVoice`
 *  tests — atlas slugs are what `topic_members.topic_id` holds alongside
 *  `dynamic-topic-<n>`. */
const ATLAS_SLUG_RE = /^[a-z][a-z0-9]*(-[a-z0-9]+)+$/

/** Prefixes that are unambiguously NOT atlas categories. Checked before the
 *  slug regex because `dynamic-topic-242` and `emergent-cluster-17` would
 *  otherwise both satisfy it. */
const STORY_PREFIXES = ['dynamic-topic-', 'emergent-cluster-', 'cluster-']

export function threadRowKind(row: ThreadRowKindInput): ThreadRowKind {
    const id = String(row.thread_id ?? '')
    if (!id) return 'story'
    if (id.startsWith('query-thread::')) return 'story'
    // Country-scoped atlas ids are `slug--CC`; the country part never changes
    // the level of the row.
    const base = id.split('--', 1)[0]
    if (STORY_PREFIXES.some(p => base.startsWith(p))) {
        // The lens states the level outright for rows it synthesized (Z3) —
        // checked before the identity_key because a synthesized row has none.
        // Only ever consulted inside the dynamic family: a family and a
        // category are different LEVELS, and an atlas slug must stay a
        // category even if some future payload marked it.
        if (row.lens_kind === 'family') return 'umbrella'
        // Dynamic family: an R2 umbrella is still an EVENT (one real-world
        // story rolled up over its fragments), so it is deliberately NOT a
        // category — it just counts differently. Scan every anchor rather
        // than [0] alone so an extra anchor can never hide the marker.
        const anchors = row.anchor_topics ?? []
        return anchors.some(a => String(a ?? '').startsWith('umbrella:')) ? 'umbrella' : 'story'
    }
    return ATLAS_SLUG_RE.test(base) ? 'category' : 'story'
}

/**
 * Which `countQualifier` base explains this row's number.
 *
 * Story/umbrella keep the pre-existing lineage split (2026-07-17 item 2):
 * atlas-style rows that serve the gate fields print `raw`, dynamic rows print
 * `gated` (the served membership for the window). A CATEGORY row gets its own
 * base because its number answers a different question entirely — it is the
 * signal total for the whole lens, summed across every story inside it.
 */
export function rowCountBase(
    kind: ThreadRowKind,
    row: { gated_signal_count?: number | null },
): CountBase {
    if (kind === 'category') return 'category'
    return row.gated_signal_count != null ? 'raw' : 'gated'
}

/**
 * The category row's count tooltip. States the two things the flat rail was
 * silently mixing: this is a CATEGORY (not a story), and the number is
 * SIGNALS across every story filed under it (measured — the atlas list path
 * counts `signal_topic_assignments` rows, not distinct stories).
 */
export function categoryRowTip(
    categoryLabel: string,
    count: number,
    windowLabel: string | null,
): string {
    const w = windowLabel ? ` in the last ${windowLabel}` : ''
    return (
        `CATEGORY, not a story: ${count.toLocaleString('en-US')} signals filed under ` +
        `“${categoryLabel}”${w}, summed across every story in it — not one story's count. ` +
        `The countries and entities on this row describe the whole category too. ` +
        `Open it to see the individual stories.`
    )
}

/**
 * The FAMILY row's badge — same affordance class as `◫ CATEGORY`, deliberately
 * not a second visual language (Pedro, Z3).
 *
 * An R2 umbrella can now be returned as a story-lens sibling
 * (docs/research/recall-229/2026-08-14-duplicate-live-stories.md: `NOT
 * is_umbrella` had excluded dt-12927 from dt-242's universe entirely, though
 * their whitened cosine 0.6489 beat the anchor's then-#1 hermano). It is a
 * CONTAINER of N stories, so its headline must not read like one story's.
 *
 * An unknown count degrades to the bare marker. It never degrades to silence:
 * "how many" is the soft fact here, "this is a family" is the hard one.
 */
export function familyRowBadge(childCount?: number | null): string {
    if (childCount == null || !Number.isFinite(childCount) || childCount <= 0) {
        return '◫ FAMILY'
    }
    return `◫ FAMILY · ${childCount.toLocaleString('en-US')} ${childCount === 1 ? 'story' : 'stories'}`
}

/**
 * The family row's tooltip. Two things, both load-bearing:
 *
 *  1. it is a family (opening it opens the family, not a leaf story), and
 *  2. the measured relation was taken against the family's AGGREGATE centroid.
 *
 * (2) is the honesty rail. dt-12927's centroid averages two different
 * earthquakes plus four Ebola rows (§2 of the measurement), so an edge to a
 * family is a weaker claim than a leaf-to-leaf match — and the row says so
 * rather than letting the number pass for the same kind of evidence.
 */
export function familyRowTip(label: string, childCount?: number | null): string {
    const n = (childCount != null && Number.isFinite(childCount) && childCount > 0)
        ? `${childCount.toLocaleString('en-US')} ${childCount === 1 ? 'story' : 'stories'}`
        : 'several stories'
    return (
        `A FAMILY, not a story: “${label}” rolls up ${n} of the same event. ` +
        `The measured relation was taken against the family's aggregate centroid, ` +
        `so it is a weaker claim than a match to a single story. Open it to see ` +
        `the stories inside.`
    )
}

/** Words in a phrase, ignoring punctuation-only fragments. */
const wordCount = (s: string): number => s.trim().split(/\s+/).filter(Boolean).length

/** Longest tail the " in …" clause may have and still read as a place rather
 *  than prose. "in Colombia" / "in Southern Italy" / "in the United States"
 *  qualify; "in fatal stabbing of parents Rob and Michele Reiner" does not. */
const MAX_PLACE_TAIL_WORDS = 3
/** Shortest remainder that can still stand alone as a story title. Below
 *  this, stripping turns a headline into a generic noun ("Earthquake"). */
const MIN_TITLE_WORDS = 3

const norm = (s: string): string => s.toLowerCase().replace(/\s+/g, ' ').trim()

/**
 * The rail's display title.
 *
 * Keeps the original intent — a trailing country is redundant next to the
 * country chips the row already renders — but refuses the three strips that
 * destroyed meaning on the live rail:
 *
 *   - remainder shorter than {@link MIN_TITLE_WORDS} ("Earthquake in
 *     Colombia" → "Earthquake", "Houthi Attacks in Yemen" → "Houthi Attacks")
 *   - tail longer than {@link MAX_PLACE_TAIL_WORDS} (prose, not a place)
 *   - remainder that merely restates the row's own category kicker
 *     ("Armed conflict escalation in Sudan" under ARMED CONFLICT ESCALATION)
 *
 * The last rule is the direct guard on Pedro's misread: a title is never
 * allowed to shrink into a copy of the badge printed beside it.
 */
export function storyTitle(label: string, categoryLabel: string | null | undefined): string {
    const full = String(label ?? '').trim()
    if (!full) return ''

    // Strip the LAST " in …" clause: "Floods in Villages Kill Dozens in
    // Pakistan" must lose Pakistan, not everything after the first "in".
    const m = full.match(/^(.*)\s+in\s+(\S.*)$/i)
    if (!m) return full

    const remainder = m[1].trim().replace(/[,;:]$/, '')
    const tail = m[2].trim()

    if (wordCount(tail) > MAX_PLACE_TAIL_WORDS) return full
    if (wordCount(remainder) < MIN_TITLE_WORDS) return full

    const cat = norm(String(categoryLabel ?? ''))
    if (cat) {
        const rem = norm(remainder)
        if (rem === cat || cat.includes(rem) || rem.includes(cat)) return full
    }
    return remainder
}
