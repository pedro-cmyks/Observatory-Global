/**
 * Which lanes answered — and what the front page is ALLOWED to say when one
 * did not (C1, the last N23 den).
 *
 * The blind judge (2026-08-12, §4.1/§4.7/§5) read a front page that said "No
 * story cleared the quality gate in this window" while the console one click
 * away was full of ranked stories, and an instrument tile that printed
 * "Coverage gaps: 0" beside a section admitting the anomaly lane never
 * answered. Both were the SAME defect: the render collapsed
 *
 *     "we measured, and the answer is nothing"
 *
 * into
 *
 *     "we could not measure"
 *
 * and then spent the page's honesty voice narrating the second as if it were
 * the first. That is worse than a plain error, because the copy is persuasive:
 * the reader believes an editorial verdict that was never reached. The judge's
 * words: the honesty copy ended up "dressing an outage as an editorial
 * principle".
 *
 * The distinction is not a guess here. `/api/v2/briefing` has always served
 * `degraded` + `degraded_segments[]` (backend/app/routers/briefing.py — every
 * section runs through `_fetch_section`, which appends its segment name on any
 * exception, and `top_threads` appends "top_threads" on its own try/except).
 * The payload knew; the page threw the knowledge away and rendered the empty
 * array. So this module is a READER of a truth that already exists — it never
 * infers a failure from emptiness, which would be the same sin pointed the
 * other way.
 *
 * ONE COPY SURFACE. Every empty-state sentence the sections print lives here,
 * which is what makes the witness testable: the phrase "cleared the quality
 * gate" exists in exactly one file, reachable only from `state === 'served'`.
 * A lane that did not answer cannot reach it by construction, not by review.
 */

/** The lanes the front page renders as their own surface. */
export type BriefLane =
  | 'stories'
  | 'gaps'
  | 'countries'
  | 'sources'
  | 'themes'
  | 'categories'

/**
 * `served` = the lane answered, so a zero is a MEASURED zero and the gate's
 * verdict is real. `unanswered` = the lane failed, timed out, or the whole
 * briefing never arrived, so every count it feeds is unknown.
 */
export type LaneState = 'served' | 'unanswered'

export interface LaneEvidence {
  /** `degraded_segments` from the briefing payload — the backend's own truth. */
  degradedSegments?: readonly string[] | null
  /** The briefing fetch itself rejected, timed out, or returned non-2xx. */
  briefUnavailable?: boolean
}

/**
 * Lane → the `degraded_segments` key(s) the backend appends for it, plus the
 * noun the reader sees. `stories` covers BOTH desks: The World and Culture,
 * Sport & Life are two renders of one `top_threads` fetch, so when it fails,
 * both are unknown for the same reason.
 */
const LANE_SEGMENTS: Record<BriefLane, readonly string[]> = {
  stories: ['top_threads'],
  gaps: ['coverage_gaps'],
  countries: ['top_countries'],
  sources: ['top_sources'],
  themes: ['top_themes'],
  categories: ['category_counts'],
}

const LANE_NOUN: Record<BriefLane, string> = {
  stories: 'story lane',
  gaps: 'coverage-gap lane',
  countries: 'country lane',
  sources: 'source lane',
  themes: 'theme lane',
  categories: 'category lane',
}

/** What answered, read off the payload's own degradation report. */
export function laneState(lane: BriefLane, evidence: LaneEvidence): LaneState {
  if (evidence.briefUnavailable) return 'unanswered'
  const degraded = evidence.degradedSegments ?? []
  return LANE_SEGMENTS[lane].some(segment => degraded.includes(segment))
    ? 'unanswered'
    : 'served'
}

/** True when a printed count would be a fabricated zero. */
export function isUnmeasured(lane: BriefLane, evidence: LaneEvidence): boolean {
  return laneState(lane, evidence) === 'unanswered'
}

/** The one-line reason, in the reader's words. Used under headings and in tips. */
export function laneUnansweredNote(lane: BriefLane): string {
  return `The ${LANE_NOUN[lane]} did not answer for this window, so this is unmeasured — not a measured zero.`
}

/** The desks whose empty state carries a gate verdict. */
export type BriefDesk = 'world' | 'culture' | 'gaps' | 'country'

/**
 * The sentence a desk prints when it has nothing to show.
 *
 * `served` keeps the exact copy the page has always used — a real verdict,
 * reached by a gate that ran. `unanswered` says the verdict is UNKNOWN, which
 * is the whole point: an absence of measurement is not a measurement of
 * absence (the 2026-07-22 silent-risk kill, applied to the front page itself).
 */
export function deskEmptyCopy(desk: BriefDesk, state: LaneState): string {
  if (state === 'unanswered') {
    switch (desk) {
      case 'world':
        return 'The story lane did not answer — the gate\'s verdict is unknown for this '
          + 'window. No story is claimed to have failed; none could be judged.'
      case 'culture':
        return 'The story lane did not answer, so the culture desk is unknown for this '
          + 'window — this is a failure to measure, not an empty desk.'
      case 'gaps':
        return 'The coverage-gap lane did not answer, so whether any category went '
          + 'unverified is unknown for this window — no claim of "no gaps" is made.'
      case 'country':
        return 'This country\'s edition could not be assembled for this window, so the '
          + 'gate\'s verdict for it did not answer — unknown, not empty.'
    }
  }
  switch (desk) {
    case 'world':
      return 'No story cleared the quality gate in this window. Open the console to inspect raw coverage.'
    case 'culture':
      return 'No culture, sport or lifestyle thread cleared the quality gate in this window — '
        + 'the section stays honestly empty rather than filled.'
    case 'gaps':
      return 'No coverage gaps in this window — every scored category cleared at least one verified row.'
    case 'country':
      return 'No coherent story cleared the quality gate for this country in the current window.'
  }
}

/** An instrument tile's printed value, and the tip that explains it. */
export interface InstrumentReading {
  /** What the big number slot prints. `—` whenever the lane did not answer. */
  value: string
  unmeasured: boolean
  tip: string
}

/**
 * A count tile, honest about its own lane.
 *
 * "Coverage gaps: 0" was the judge's §4.7: a measured zero printed while the
 * section below it said the lane never ran. A tile is the LOUDEST place on the
 * page to fabricate a number, because it carries no prose to qualify it — so
 * when the lane is down it prints an em dash and puts the reason in the tip.
 */
export function instrumentReading(
  count: number | null | undefined,
  lane: BriefLane,
  evidence: LaneEvidence,
  measuredTip: string,
): InstrumentReading {
  if (laneState(lane, evidence) === 'unanswered') {
    return { value: '—', unmeasured: true, tip: laneUnansweredNote(lane) }
  }
  return {
    value: (count ?? 0).toLocaleString(),
    unmeasured: false,
    tip: measuredTip,
  }
}

/**
 * The line that goes under a back-matter heading with no rows beneath it.
 *
 * Judge §4.5, "empty furniture": MOST ACTIVE, SOURCES and BY THEME rendered as
 * headings over literally nothing, and the signal-density map as a flat grey
 * landmass. A heading with a void under it is the page silently shrugging;
 * every one of those frames now says which of the two things happened.
 * `null` when the section has rows — nothing to explain.
 */
export function furnitureNote(
  lane: BriefLane,
  evidence: LaneEvidence,
  rowCount: number,
): string | null {
  if (rowCount > 0) return null
  if (laneState(lane, evidence) === 'unanswered') return laneUnansweredNote(lane)
  return 'Nothing measured in this window.'
}

/** The map's own version of the same sentence (its "rows" are lit countries). */
export function mapDensityNote(
  evidence: LaneEvidence,
  litCountries: number,
): string | null {
  return furnitureNote('countries', evidence, litCountries)
}
