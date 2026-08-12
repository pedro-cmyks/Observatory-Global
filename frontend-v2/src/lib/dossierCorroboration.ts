// Web corroboration (contract dossier-corroboration-v1, roadmap P0.6b).
//
// Productizes the manual NATO-Ankara corroboration run: each pin is checked
// against live web coverage (backend lane: GDELT DOC 2.0) with SOURCE-
// INDEPENDENCE weighting — syndicated wire copies collapse to one source,
// independently-operated outlets are counted, never articles (the G2 rule).
// LLM phrases ONE thing: the coverage-asymmetry note over the gathered titles.
//
// Cached per investigation in localStorage; re-run on demand. Degrades
// honestly: if no search path answered, the section SAYS so.
import type { WorkbenchPin } from './workbench'
import type { ConnectionNode } from './dossierConnections'

/** Coarse credibility rollup (#217) measured server-side by
 *  `source_tiers.tier_payload` — the authoritative classification travels with
 *  the citation so the render never re-guesses it. Optional: pre-v2 payloads
 *  carry no credibility block and render without a chip. */
export interface CorroborationCredibility {
  tier: number | string
  label: string
  provenance?: string | null
}

export interface CorroborationCitation {
  title: string
  url: string
  outlet: string
  language?: string | null
  seendate?: string | null
  lane?: string | null
  /** corroborate-v2 R1: ownership key that collapsed this outlet into a shared
   *  VOICE (e.g. 'state:ru' for ria/tass/rt). null/absent = no known shared
   *  owner — the outlet counts as its own voice. */
  ownership_group?: string | null
  credibility?: CorroborationCredibility | null
}

/** Per-pin health of the SEARCH LANE itself (tren B2 V5) — orthogonal to the
 *  corroboration status. `ok` = every query answered (a measured zero is still
 *  ok: "nobody covered this" is an answer). `partial` = some answered.
 *  `throttled` = GDELT DOC 2.0's one-query-per-five-seconds limit.
 *  `timeout` = still in flight when the time budget expired. Absent on pre-V5
 *  payloads, which then render exactly as they did before. */
export type CorroborationSearchStatus =
  'ok' | 'partial' | 'throttled' | 'timeout' | 'unavailable' | 'not_applicable'

export interface CorroborationPin {
  id: string
  label: string
  status: 'established' | 'contested' | 'unverified' | 'not_applicable'
  search_status?: CorroborationSearchStatus
  /** Whether THIS PIN got an answer from any lane — distinct from
   *  `search_status`, which reports the web lane specifically. A pin whose web
   *  query was throttled can still be measured by the client-supplied lane. */
  measured?: boolean
  queries_run?: number
  queries_answered?: number
  /** Distinct outlets after syndication clustering — receipts stay visible. */
  independent_outlets: number
  /** corroborate-v2 R1: outlets AFTER ownership collapse — the number the
   *  status is judged on. Absent on pre-v2 payloads (then outlets == voices by
   *  construction, and the render says nothing it did not measure). */
  independent_voices?: number
  /** How many outlets the ownership collapse absorbed (outlets − voices). */
  state_collapsed?: number
  total_articles: number
  syndicated_clusters: number
  single_source: boolean
  citations: CorroborationCitation[]
  note: string
  queries: string[]
  /** corroborate-v2 verdict block, when one travels with the pin. The dossier
   *  lane (`/api/v2/dossier/corroborate`) does NOT emit it today — it rides
   *  the per-claim lane (`/api/v2/corroborate`). Optional so the consumer is
   *  in place the moment a verdict does arrive, and silent until then: an
   *  absent verdict renders nothing rather than a fabricated zero. */
  verdict?: CorroborationVerdict | null
}

/** Per-claim verdict from `POST /api/v2/corroborate` (corroboration-v1 +
 *  corroborate-v2 fields). `template_matches` = matches that shared only a
 *  casualty TEMPLATE and no entity anchor (F2); `aged` = receipts outside the
 *  `window_days` temporal window (R3), counted as context, never as backing.
 *  All v2 fields optional — an older backend's verdict still parses. */
export interface CorroborationVerdict {
  status: 'corroborated' | 'contradicted' | 'uncorroborated' | string
  corroborating: number
  contradicting: number
  official_corroborating: number
  note: string
  template_matches?: number
  aged?: number
  window_days?: number
}

/** One inspectable piece of a verdict. `setAside` marks the counts the backend
 *  SHOWS but never counts as backing (template-shaped matches, aged receipts)
 *  so the render can mute them instead of letting them read as corroboration. */
export interface VerdictFacet {
  key: 'corroborating' | 'contradicting' | 'official' | 'template' | 'aged'
  label: string
  tip: string
  setAside: boolean
}

/** The verdict block, exploded into facets the report can render one by one.
 *  Every number comes from the backend's own count — nothing is derived here,
 *  and a zero is simply not shown (absence over a decorative "0"). Pure.
 *
 *  PRODUCER NOTE: `verdict` rides `POST /api/v2/corroborate` (contract
 *  `corroboration-v1`), the per-CLAIM lane, which the app does not call today.
 *  `POST /api/v2/dossier/corroborate` — the lane the report DOES call — returns
 *  no verdict block, so these facets render only once a verdict actually
 *  travels with a pin. See the note on `CorroborationPin.verdict`. */
export function verdictFacets(v: CorroborationVerdict | null | undefined): VerdictFacet[] {
  if (!v) return []
  const out: VerdictFacet[] = []
  if (v.corroborating > 0) {
    out.push({
      key: 'corroborating', setAside: false,
      label: `${v.corroborating} corroborating`,
      tip: 'Sources that independently back this claim, inside the measured window.',
    })
    // Answering the claim ledger's question out loud: is any backer official?
    out.push(v.official_corroborating > 0
      ? {
        key: 'official', setAside: false,
        label: `${v.official_corroborating} official/wire`,
        tip: 'Among the corroborating sources: government, UN, or an international wire agency.',
      }
      : {
        key: 'official', setAside: false,
        label: 'none official/wire',
        tip: 'No government, UN, or wire-agency source is among the backers — treat the figure as contested.',
      })
  }
  if (v.contradicting > 0) {
    out.push({
      key: 'contradicting', setAside: false,
      label: `${v.contradicting} contradicting`,
      tip: 'Sources whose figure or account conflicts with this claim.',
    })
  }
  if ((v.template_matches ?? 0) > 0) {
    out.push({
      key: 'template', setAside: true,
      label: `${v.template_matches} template-shaped set aside`,
      tip: 'Matched only shared casualty boilerplate with no shared event anchor — shown so you can inspect them, never counted as backing (corroborate-v2 F2).',
    })
  }
  if ((v.aged ?? 0) > 0) {
    out.push({
      key: 'aged', setAside: true,
      label: `${v.aged} outside the ${v.window_days ?? '?'}-day window`,
      tip: agedTip(v.window_days ?? 0),
    })
  }
  return out
}

export interface CorroborationData {
  contract: string
  measured_at: string
  search_available: boolean
  search_source: string | null
  window_days: number
  pins: CorroborationPin[]
  /** V5: true when at least one evidence pin was not fully measured. Absent on
   *  pre-V5 payloads — absence means "this backend did not measure it", which
   *  is why the banner stays silent rather than claiming a complete run. */
  partial?: boolean
  /** Evidence pins whose lane answered at least one query — a pin measured on
   *  one of two queries still returned real coverage, so it counts. */
  pins_measured?: number
  /** How many of those were only PARTIALLY measured — kept separate so the
   *  banner can say it instead of rounding it away in either direction. */
  pins_partial?: number
  pins_applicable?: number
  coverage_asymmetry: { note: string; provider: string | null } | null
  meta?: {
    independence_rule?: string
    status_rule?: string
    search_note?: string | null
    search_status_rule?: string
    budget_seconds?: number
    elapsed_seconds?: number
    throttle_interval_seconds?: number
  }
}

/** Why this pin is not fully measured, in one line — or null when it is (or
 *  when the backend did not say). Never converts an unmeasured pin into a
 *  zero. Pure. */
export function pinSearchStatusText(p: CorroborationPin): string | null {
  const s = p.search_status
  if (!s || s === 'ok' || s === 'not_applicable') return null
  if (s === 'throttled') {
    return 'web lane throttled — GDELT DOC 2.0 allows one query every five seconds; not measured'
  }
  if (s === 'timeout') {
    return 'web lane did not answer inside the time budget — not measured'
  }
  if (s === 'partial') {
    const run = p.queries_run ?? 0
    const answered = p.queries_answered ?? 0
    return run
      ? `partially measured — ${answered} of ${run} search queries answered`
      : 'partially measured'
  }
  return 'web lane unavailable — not measured'
}

/** The run-level honesty banner: "web lane throttled — 1 of 3 evidence pins
 *  measured". null when the run was complete or the backend is pre-V5. Pure. */
export function corroborationCoverageText(c: CorroborationData): string | null {
  if (!c.partial) return null
  const measured = c.pins_measured ?? 0
  const applicable = c.pins_applicable ?? c.pins.length
  const states = new Set(c.pins.map(p => p.search_status))
  const why = states.has('throttled')
    ? 'web lane throttled'
    : states.has('timeout')
      ? 'web lane timed out'
      : 'web lane degraded'
  const partially = c.pins_partial ?? 0
  const unreached = applicable - measured
  if (unreached <= 0) {
    // Degraded but complete — naming a "rest" that does not exist is its own
    // small lie, and it lands right beside verdicts built on real receipts.
    const partly = partially ? `, ${partially} of them only partially` : ''
    return `${why} — all ${applicable} evidence pins measured${partly}`
  }
  const partly = partially ? ` (${partially} of them only partially)` : ''
  const rest = unreached > 1
    ? `the ${unreached} pins not reached are shown unmeasured`
    : 'the pin not reached is shown unmeasured'
  return `${why} — ${measured} of ${applicable} evidence pins measured${partly}; ${rest}, not as zero coverage`
}

/** ✓ established / ⚠ contested / ? unverified — the per-pin status chip. */
export function statusChip(status: CorroborationPin['status']): string {
  if (status === 'established') return '✓ established'
  if (status === 'contested') return '⚠ contested'
  if (status === 'not_applicable') return '— not applicable'
  return '? unverified'
}

/** The counts line under a pin's note. v2 leads with VOICES (the number the
 *  status is judged on) and keeps outlets visible beside it, naming the
 *  ownership collapse when it changed the number. A pre-v2 payload (no
 *  `independent_voices`) renders the original outlets-only line byte-for-byte
 *  — we never restate an old measurement in new words. Pure. */
export function pinCountsText(p: CorroborationPin): string {
  const clusters = `${p.syndicated_clusters} syndicated cluster${p.syndicated_clusters === 1 ? '' : 's'}`
  if (p.independent_voices === undefined || p.independent_voices === null) {
    return `${p.independent_outlets} independent · ${p.total_articles} articles · ${clusters}`
  }
  const collapse = (p.state_collapsed ?? 0) > 0 ? ' · same-owner outlets counted as one voice' : ''
  return `${p.independent_voices} independent voice${p.independent_voices === 1 ? '' : 's'}`
    + ` · ${p.independent_outlets} outlets · ${p.total_articles} articles · ${clusters}${collapse}`
}

/** The credibility chip for one corroboration citation — from the backend's
 *  own classification, never re-derived here. Returns null when the backend
 *  said nothing (absence over guess) or the tier is 'unknown'. Pure. */
export function citationTierChip(cit: CorroborationCitation): string | null {
  const label = (cit.credibility?.label ?? '').trim()
  if (!label || label.toLowerCase() === 'unknown') return null
  return `[${label.toUpperCase()}]`
}

/** Backend tier vocabulary (source_tiers.TIER_LABELS) → the shared receipt-chip
 *  modifier the L2 surfaces already style (`.l2-tier-chip--*`). Labels without
 *  a hue of their own reuse the nearest established one rather than rendering
 *  an unstyled chip. null when there is nothing to show. Pure. */
const TIER_CHIP_CLASS: Record<string, string> = {
  state: 'state', wire: 'wire', reference: 'wire',
  mainstream: 'major', major: 'major', local: 'local', flagged: 'state',
}

export function citationTierClass(cit: CorroborationCitation): string | null {
  if (!citationTierChip(cit)) return null
  const label = (cit.credibility?.label ?? '').trim().toLowerCase()
  return TIER_CHIP_CLASS[label] ?? 'local'
}

// ── Citation dates + the aged window (corroborate-v2 R3) ─────────────────────
// Frank's fresh test: "citations render no date (an aged receipt would be
// invisible)". The payload has carried `seendate` all along — DOC 2.0 stamps
// it `YYYYMMDDTHHMMSSZ`, a client-supplied row carries null. These mirror the
// backend's `_match_date` rule exactly, including its discipline: an UNDATED
// receipt is never claimed aged, because we do not measure what we lack.

const DOC20_DATE_RE = /^(\d{4})(\d{2})(\d{2})T\d{6}Z$/

/** A citation's measured publication day as `YYYY-MM-DD`, or null when the
 *  backend recorded none / it does not parse. Never guesses. Pure. */
export function citationDay(cit: CorroborationCitation): string | null {
  const raw = (cit.seendate ?? '').trim()
  if (!raw) return null
  const m = DOC20_DATE_RE.exec(raw)
  const iso = m ? `${m[1]}-${m[2]}-${m[3]}` : raw.slice(0, 10)
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) return null
  const d = new Date(`${iso}T00:00:00Z`)
  // Reject impossible calendar dates (Date rolls 2026-13-32 over silently).
  if (Number.isNaN(d.getTime()) || d.toISOString().slice(0, 10) !== iso) return null
  return iso
}

/** The short day the rest of the report uses ("Aug 10"), or null. Pure. */
export function citationDateText(cit: CorroborationCitation): string | null {
  const day = citationDay(cit)
  if (!day) return null
  try {
    return new Date(`${day}T00:00:00Z`).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', timeZone: 'UTC',
    })
  } catch { return day }
}

/** True when this receipt was published outside the window the run measured
 *  (`window_days` back from `measured_at`) — the R3 rule: an aged receipt is
 *  context, never backing. Arithmetic over two fields the payload already
 *  carries; nothing is inferred about an undated row, and a payload with no
 *  window makes no claim at all. Pure. */
export function citationAged(cit: CorroborationCitation, data: CorroborationData): boolean {
  const day = citationDay(cit)
  if (!day || !data.window_days || data.window_days <= 0) return false
  const measured = new Date(data.measured_at)
  if (Number.isNaN(measured.getTime())) return false
  const measuredDay = Date.UTC(
    measured.getUTCFullYear(), measured.getUTCMonth(), measured.getUTCDate())
  const cited = new Date(`${day}T00:00:00Z`).getTime()
  const ageDays = Math.round((measuredDay - cited) / 86_400_000)
  return ageDays > data.window_days
}

export function agedTip(windowDays: number): string {
  return `Published outside the ${windowDays}-day window this run measured — `
    + 'shown as context, never counted as backing.'
}

/** The window as a sentence for the section header — a bare "window 14d" is a
 *  number the reader has to decode. Pure. */
export function corroborationWindowText(data: CorroborationData): string {
  const d = data.window_days
  return `receipts within the last ${d} day${d === 1 ? '' : 's'}`
}

/** Why this citation did not count as its own voice, in one plain line — or
 *  null when it did. Pure. */
export function citationCollapseNote(cit: CorroborationCitation): string | null {
  const group = (cit.ownership_group ?? '').trim()
  if (!group) return null
  const state = group.startsWith('state:') ? group.slice('state:'.length).toUpperCase() : null
  return state
    ? `Same state apparatus (${state}) as other outlets here — counted as one voice, not several.`
    : `Shares an ownership group (${group}) with other outlets here — counted as one voice.`
}

/** Build the request body from the frozen pins (+ measured actors from the
 *  connection nodes, when the measurement already landed). Pure/testable. */
export function buildCorroborationRequest(
  pins: WorkbenchPin[],
  connNodes?: ConnectionNode[] | null,
): { pins: Array<{ id: string; label: string; anchor_type: string; actors: string[]; evidence: string[] }>; days: number } {
  const nodeFor = (p: WorkbenchPin): ConnectionNode | undefined =>
    (connNodes ?? undefined)?.find(n =>
      n.id === p.anchorId || n.base_id === p.anchorId || n.collapsed_from?.includes(p.anchorId)
      || n.label === p.label)
  return {
    pins: pins.map(p => ({
      id: p.anchorId,
      label: p.label,
      anchor_type: p.anchorType,
      actors: (nodeFor(p)?.persons ?? []).slice(0, 3),
      evidence: (p.snapshot?.evidence ?? []).slice(0, 6).map(e => {
        const attribution = e.source
          ? ` — ${e.source}${e.date ? `, ${e.date}` : ''}`
          : (e.date ? ` — ${e.date}` : '')
        return `${e.headline}${attribution}`
      }),
    })),
    days: 14,
  }
}

/** POST the corroboration run. Returns null on any failure (the section
 *  renders its honest empty state; never throws into the report). */
export async function fetchCorroboration(
  body: ReturnType<typeof buildCorroborationRequest>,
  force = false,
): Promise<CorroborationData | null> {
  try {
    const res = await fetch('/api/v2/dossier/corroborate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...body, force }),
    })
    if (!res.ok) return null
    return await res.json() as CorroborationData
  } catch {
    return null
  }
}

// ── Job + poll (the proxy ceiling binds after serialization) ─────────────────
// MEASURED against prod (2026-08-12): a corroboration run costs ~5.75s per
// search query (the DOC 2.0 1-req/5s throttle) + ~12s fixed — 3 evidence pins
// = 46.3s, 4 pins = 57.8s — against a ~30s Vercel rewrite ceiling. Any real
// investigation therefore dies as a silent 502 on a single request (the fresh
// Frank test: 2 of 4 runs). So the client STARTS a run and polls it, the same
// shape as the universe build and the article-enrichment fill.

export interface CorroborationJobProgress {
  queries_total?: number
  queries_done?: number
  pins_total?: number
  pins_applicable?: number
}

export interface CorroborationJob {
  job_id: string | null
  status: 'running' | 'done' | 'error' | 'unknown'
  progress: CorroborationJobProgress
  result: CorroborationData | null
  error?: string | null
}

const JOB_POLL_MS = 2000
const JOB_MAX_WAIT_MS = 6 * 60 * 1000

export async function startCorroboration(
  body: ReturnType<typeof buildCorroborationRequest>,
  force = false,
): Promise<CorroborationJob | null> {
  try {
    const res = await fetch('/api/v2/dossier/corroborate/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...body, force }),
    })
    if (!res.ok) return null
    return await res.json() as CorroborationJob
  } catch {
    return null
  }
}

export async function pollCorroboration(jobId: string): Promise<CorroborationJob | null> {
  try {
    const res = await fetch(`/api/v2/dossier/corroborate/status/${encodeURIComponent(jobId)}`)
    if (!res.ok) return null
    return await res.json() as CorroborationJob
  } catch {
    return null
  }
}

/** Start a run and poll it to completion. Returns the payload, or null when the
 *  run was lost/failed — the caller renders its honest failure state and never
 *  an empty result. Falls back to the synchronous endpoint when the job path is
 *  not available (older backend), so a stale deploy degrades instead of dying. */
export async function runCorroborationJob(
  body: ReturnType<typeof buildCorroborationRequest>,
  force = false,
  opts?: {
    pollMs?: number
    maxWaitMs?: number
    onProgress?: (p: CorroborationJobProgress) => void
    signal?: { aborted: boolean }
  },
): Promise<CorroborationData | null> {
  const pollMs = opts?.pollMs ?? JOB_POLL_MS
  const maxWaitMs = opts?.maxWaitMs ?? JOB_MAX_WAIT_MS
  const started = await startCorroboration(body, force)
  if (!started) return await fetchCorroboration(body, force)
  if (started.status === 'done') return started.result
  if (started.status === 'error' || !started.job_id) return null
  opts?.onProgress?.(started.progress ?? {})

  const deadline = Date.now() + maxWaitMs
  while (Date.now() < deadline) {
    if (opts?.signal?.aborted) return null
    await new Promise(r => setTimeout(r, pollMs))
    const snap = await pollCorroboration(started.job_id)
    if (!snap) continue
    opts?.onProgress?.(snap.progress ?? {})
    if (snap.status === 'done') return snap.result
    if (snap.status === 'error' || snap.status === 'unknown') return null
  }
  return null
}

// ── Per-investigation cache (re-run on demand) ───────────────────────────────
const CACHE_KEY = 'atlas.corroboration.v2'
const CACHE_MAX_AGE_MS = 24 * 3600 * 1000

export function loadCachedCorroboration(invId: string): CorroborationData | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    if (!raw) return null
    const map = JSON.parse(raw) as Record<string, CorroborationData>
    const hit = map[invId]
    if (!hit) return null
    if (Date.now() - new Date(hit.measured_at).getTime() > CACHE_MAX_AGE_MS) return null
    return hit
  } catch {
    return null
  }
}

export function saveCorroboration(invId: string, data: CorroborationData): void {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    const map = raw ? JSON.parse(raw) as Record<string, CorroborationData> : {}
    map[invId] = data
    // keep the map small: drop entries older than the max age
    for (const [k, v] of Object.entries(map)) {
      if (Date.now() - new Date(v.measured_at).getTime() > CACHE_MAX_AGE_MS) delete map[k]
    }
    localStorage.setItem(CACHE_KEY, JSON.stringify(map))
  } catch { /* quota — section still renders from memory */ }
}

export function clearCorroboration(invId: string): void {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    if (!raw) return
    const map = JSON.parse(raw) as Record<string, CorroborationData>
    delete map[invId]
    localStorage.setItem(CACHE_KEY, JSON.stringify(map))
  } catch { /* ignore */ }
}

function fmtMeasured(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  } catch { return iso }
}

/** Markdown block for the export (inserted before Timeline, like the
 *  connection findings). Mirrors the on-screen section 1:1. */
export function corroborationMarkdown(c: CorroborationData): string[] {
  const lines: string[] = []
  lines.push(`## Web corroboration — measured ${fmtMeasured(c.measured_at)}, independent sources weighted`)
  if (!c.search_available) {
    lines.push('')
    lines.push(`_${c.meta?.search_note ?? 'Web-search lane unavailable — corroboration not measured.'}_`)
  } else {
    lines.push(`*Source: ${c.search_source ?? 'unknown'} · ${corroborationWindowText(c)} · syndicated wire copies collapse to one source; independently-operated outlets counted, never articles.*`)
  }
  const coverage = corroborationCoverageText(c)
  if (coverage) {
    lines.push('')
    lines.push(`**⚠ ${coverage}**`)
  }
  lines.push('')
  for (const p of c.pins) {
    lines.push(`### ${statusChip(p.status)} — ${p.label}`)
    lines.push(`${p.note} (${pinCountsText(p)})`)
    const lane = pinSearchStatusText(p)
    if (lane) lines.push(`_${lane}_`)
    const facets = verdictFacets(p.verdict)
    if (facets.length) {
      lines.push(`Verdict: ${facets.map(f => f.label).join(' · ')}`)
    }
    for (const cit of p.citations) {
      const chip = citationTierChip(cit)
      const day = citationDateText(cit)
      // The date is part of the receipt, not decoration — an aged receipt that
      // renders undated is exactly how stale backing hides in plain sight.
      const attribution = `${cit.outlet}${day ? `, ${day}` : ''}`
      const aged = citationAged(cit, c) ? ` _(outside the ${c.window_days}-day window — context only)_` : ''
      lines.push(`- [${cit.title}](${cit.url}) — ${attribution}${chip ? ` ${chip}` : ''}${aged}`)
    }
    lines.push('')
  }
  if (c.coverage_asymmetry?.note) {
    lines.push('**Coverage asymmetry** (phrased from the gathered titles only'
      + (c.coverage_asymmetry.provider ? `, ${c.coverage_asymmetry.provider}` : '') + '):')
    lines.push(c.coverage_asymmetry.note)
    lines.push('')
  }
  return lines
}
