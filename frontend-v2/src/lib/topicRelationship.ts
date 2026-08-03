// #168 — attention-relationship chip model + cached fetch.
//
// GET /api/v2/topic/{id}/relationship classifies a topic's press-vs-public
// relationship from typed topic_members role counts (media-led / public-led /
// social-led / silent-risk / uncoupled-attention — topic_relationship.py).
// This lib is the ONE place that response is parsed and turned into chip
// copy, shared by NarrativeThreads rows (compact) and ThemeDetail (full).
//
// Honesty rules:
//  * discussion/mood are unverified forum & social signals — the tip always
//    says so; the chip never lets attention read as evidence;
//  * compact mode renders ONLY the differentiating classes (public-led /
//    social-led / silent-risk). media-led is the field's default state —
//    badging every row with it is noise (de-densify), and uncoupled-attention
//    on a list row is a substrate-coverage artifact, not a measurement
//    (the 2026-07-16 false-differentiation lesson);
//  * any fetch/parse failure -> null -> no chip. Absence, never an error.

export interface TopicRelationship {
    relationship: string
    evidenceCount: number
    discussionCount: number
    moodCount: number
    rationale: string
}

export interface RelationshipChipModel {
    text: string
    /** rel-chip modifier class, e.g. "rel-chip--public" */
    className: string
    tip: string
}

const HONESTY_NOTE =
    'Discussion and mood are unverified forum/social signals — never counted as evidence.'

const PRESENTATION: Record<string, { text: string; cls: string; gloss: string }> = {
    'media-led': {
        text: 'MEDIA-LED',
        cls: 'media',
        gloss: 'Press coverage outweighs public discussion',
    },
    'public-led': {
        text: 'PUBLIC-LED',
        cls: 'public',
        gloss: 'Public conversation is ahead of the press coverage',
    },
    'social-led': {
        text: 'SOCIAL-LED',
        cls: 'social',
        gloss: 'Forum/social discussion with negligible press coverage',
    },
    'silent-risk': {
        text: 'SILENT RISK',
        cls: 'silent',
        gloss: 'Public concern measured while press coverage is near-absent',
    },
    'uncoupled-attention': {
        text: 'UNCOUPLED',
        cls: 'uncoupled',
        gloss: 'No press or public narrative members measured in this window',
    },
}

/** The classes worth a badge on a dense list row. */
const COMPACT_CLASSES = new Set(['public-led', 'social-led', 'silent-risk'])

export function parseTopicRelationship(d: unknown): TopicRelationship | null {
    if (!d || typeof d !== 'object') return null
    const r = d as Record<string, unknown>
    if (typeof r.relationship !== 'string' || !(r.relationship in PRESENTATION)) return null
    return {
        relationship: r.relationship,
        evidenceCount: Number(r.evidence_count ?? 0) || 0,
        discussionCount: Number(r.discussion_count ?? 0) || 0,
        moodCount: Number(r.mood_count ?? 0) || 0,
        rationale: typeof r.rationale === 'string' ? r.rationale : '',
    }
}

export function relationshipChip(
    rel: TopicRelationship | null | undefined,
    opts?: { compact?: boolean },
): RelationshipChipModel | null {
    if (!rel) return null
    const p = PRESENTATION[rel.relationship]
    if (!p) return null
    if (opts?.compact && !COMPACT_CLASSES.has(rel.relationship)) return null
    const counts =
        `press ${rel.evidenceCount} · discussion ${rel.discussionCount}` +
        (rel.moodCount ? ` · mood ${rel.moodCount}` : '')
    return {
        text: p.text,
        className: `rel-chip--${p.cls}`,
        tip: `${p.gloss}. Measured from typed membership: ${counts}. ${HONESTY_NOTE}`,
    }
}

// ── Cached fetch ─────────────────────────────────────────────────────────────
// The endpoint is Redis-cached 180s server-side; the client cache exists so a
// polling list doesn't re-issue ~20 fetches per refresh cycle. Failures are
// cached too (as null) so a down endpoint is not hammered — the cost is a
// badge staying absent for one TTL, which is the honest degradation anyway.

const CACHE_TTL_MS = 5 * 60_000
const cache = new Map<string, { at: number; value: TopicRelationship | null }>()
const inflight = new Map<string, Promise<TopicRelationship | null>>()

export async function fetchTopicRelationship(topicId: string): Promise<TopicRelationship | null> {
    const hit = cache.get(topicId)
    if (hit && Date.now() - hit.at < CACHE_TTL_MS) return hit.value
    const pending = inflight.get(topicId)
    if (pending) return pending
    const p = (async () => {
        try {
            const res = await fetch(`/api/v2/topic/${encodeURIComponent(topicId)}/relationship`)
            const value = res.ok ? parseTopicRelationship(await res.json()) : null
            cache.set(topicId, { at: Date.now(), value })
            return value
        } catch {
            cache.set(topicId, { at: Date.now(), value: null })
            return null
        } finally {
            inflight.delete(topicId)
        }
    })()
    inflight.set(topicId, p)
    return p
}
