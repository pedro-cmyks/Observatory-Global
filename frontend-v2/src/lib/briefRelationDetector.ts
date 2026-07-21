/**
 * Client-side "these pins connect on topic X" detector for the Exploration
 * Flywheel (brief-side surfacing of relations between the analyst's pinned
 * anchors and the brief's already-fetched thread headlines).
 *
 * Reuses the SAME threshold gate as the dossier connection graph
 * (`headlineMentionTerm` / `labelKeyTokens` from `./dossierConnections`) so a
 * "text" relation here means exactly what it means there: ≥2 shared key
 * tokens between a label and a headline (or the lone token of a 1-token
 * label) — never a fuzzy/semantic guess.
 *
 * Only two tiers are reachable from this surface:
 *   - 'text'    — a label's key tokens are mentioned in the other side's
 *                 headline (or vice versa).
 *   - 'context' — no text match, but pin and thread share a SUBJECT country
 *                 (coverage overlap only, not identity or causality).
 * 'strong' (rarity-weighted shared actor, computed server-side from full
 * NER person sets) and 'weak' (semantic-only) are NOT computable from the
 * headline+country data available on the brief, so they are structurally
 * unreachable here — the result is measured-not-asserted by construction,
 * never inflated to a confidence tier this surface can't actually back.
 */

import { labelKeyTokens, headlineMentionTerm } from './dossierConnections'

export type BriefRelationTier = 'text' | 'context'

export interface BriefRelation {
  /** the brief thread this pin relates to */
  threadId: string
  threadLabel: string
  /** the pin the relation was found from */
  pinAnchorId: string
  pinLabel: string
  tier: BriefRelationTier
  /** the matched term, when tier === 'text' */
  term?: string
  /** the shared subject country code, when tier === 'context' */
  sharedCountry?: string
}

export interface BriefPinLike {
  anchorId: string
  anchorType?: string
  label: string
  snapshot?: {
    countryCode?: string | null
    evidence?: Array<{ headline?: string | null; country_code?: string | null }>
  }
}

export interface BriefThreadLike {
  thread_id: string
  label: string
  evidence_samples?: Array<{ headline?: string | null; country_code?: string | null }>
  top_countries?: string[] | null
}

interface DetectOpts {
  /** max relations returned, strongest-first (text before context). Default 6. */
  cap?: number
}

function pinHeadlines(pin: BriefPinLike): string[] {
  return (pin.snapshot?.evidence ?? [])
    .map(e => e.headline)
    .filter((h): h is string => !!h)
}

function pinCountries(pin: BriefPinLike): Set<string> {
  const out = new Set<string>()
  if (pin.snapshot?.countryCode) out.add(pin.snapshot.countryCode)
  for (const e of pin.snapshot?.evidence ?? []) {
    if (e.country_code) out.add(e.country_code)
  }
  return out
}

function threadHeadlines(thread: BriefThreadLike): string[] {
  return (thread.evidence_samples ?? [])
    .map(e => e.headline)
    .filter((h): h is string => !!h)
}

function threadCountries(thread: BriefThreadLike): Set<string> {
  const out = new Set<string>()
  for (const c of thread.top_countries ?? []) out.add(c)
  for (const e of thread.evidence_samples ?? []) {
    if (e.country_code) out.add(e.country_code)
  }
  return out
}

/** Try a text-mention match in both directions: thread text against the
 *  pin's label tokens, then pin text against the thread's label tokens.
 *  Returns the first match found, or null. */
function findTextMatch(pin: BriefPinLike, thread: BriefThreadLike): string | null {
  const pinTokens = labelKeyTokens(pin.label)
  const threadTokens = labelKeyTokens(thread.label)

  if (pinTokens.length > 0) {
    const haystacks = [thread.label, ...threadHeadlines(thread)]
    for (const text of haystacks) {
      const term = headlineMentionTerm(text, pinTokens)
      if (term) return term
    }
  }

  if (threadTokens.length > 0) {
    const haystacks = [pin.label, ...pinHeadlines(pin)]
    for (const text of haystacks) {
      const term = headlineMentionTerm(text, threadTokens)
      if (term) return term
    }
  }

  return null
}

/** Shared subject-country between a pin and a thread, or null. */
function findSharedCountry(pin: BriefPinLike, thread: BriefThreadLike): string | null {
  const pc = pinCountries(pin)
  if (pc.size === 0) return null
  const tc = threadCountries(thread)
  for (const c of pc) {
    if (tc.has(c)) return c
  }
  return null
}

/**
 * Detect "these pins connect on topic X" relations between the analyst's
 * pinned anchors and the brief's threads. Pure, synchronous, no network.
 *
 * For each thread, checks every pin for the best reachable tier (text beats
 * context) and emits at most one relation per thread. Results are ranked
 * text-first, then context, and capped.
 */
export function detectBriefRelations(
  pins: BriefPinLike[],
  threads: BriefThreadLike[],
  opts: DetectOpts = {},
): BriefRelation[] {
  const cap = opts.cap ?? 6
  const textRelations: BriefRelation[] = []
  const contextRelations: BriefRelation[] = []

  for (const thread of threads) {
    let best: BriefRelation | null = null

    for (const pinItem of pins) {
      const term = findTextMatch(pinItem, thread)
      if (term) {
        best = {
          threadId: thread.thread_id,
          threadLabel: thread.label,
          pinAnchorId: pinItem.anchorId,
          pinLabel: pinItem.label,
          tier: 'text',
          term,
        }
        break // text is the best reachable tier — no need to keep scanning pins
      }
      if (!best) {
        const sharedCountry = findSharedCountry(pinItem, thread)
        if (sharedCountry) {
          best = {
            threadId: thread.thread_id,
            threadLabel: thread.label,
            pinAnchorId: pinItem.anchorId,
            pinLabel: pinItem.label,
            tier: 'context',
            sharedCountry,
          }
        }
      }
    }

    if (best) {
      if (best.tier === 'text') textRelations.push(best)
      else contextRelations.push(best)
    }
  }

  return [...textRelations, ...contextRelations].slice(0, cap)
}
