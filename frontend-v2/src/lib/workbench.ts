// Workbench investigation store (Phase 2, spec §Workbench / #213).
//
// v1 storage is localStorage — per-browser and evictable, NOT a durable
// archive (spec amendment B3). Durability comes from JSON export and the
// server-side pin-event log (#218). Multiple investigations live side by
// side; pins from different investigations never silently mix.

/** #227: a frozen snapshot of the evidence at pin time, so a Phase-3 dossier
 *  reads what the analyst SAW when they pinned — not a live re-fetch that may
 *  have drifted (counts move, the gate re-scores, threads dissolve). */
export interface PinSnapshot {
  capturedAt: string
  summary?: string
  metrics?: Record<string, string | number>
  /** ISO country code for metadata-only pins (event/anomaly) so the typed graph
   *  can join them to same-country stories as coverage context. */
  countryCode?: string
  /** Label Court verdict at PIN TIME (N15): 'entailed' | 'partial' | 'failed'
   *  | null (unchecked). Frozen like the rest of the snapshot — the dossier
   *  marks a failed/partial label under review as the analyst SAW it. */
  labelStatus?: string | null
  /** `date` = signal date (ISO day) when the payload carried one — the report
   *  renders "— outlet, Jul 8" (P0.3: dates everywhere). */
  evidence?: Array<{ headline: string; source?: string; url?: string; date?: string }>
}

/** A gate tier as it reaches the UI. `verified` cleared the strict quality gate
 *  (~90% precision), `extended` the ~75% threshold, `below_gate` neither, and
 *  `unknown` = the row carried no gate signal (dynamic/social/archive rows). */
export type CitationGateStatus = 'verified' | 'extended' | 'below_gate' | 'unknown'

/** RECEIPT-LEVEL pin (council wish 1, W4/#227 lineage). A Citation is ONE
 *  headline — an evidence row / semantic match / archive-day receipt / Brief
 *  tray receipt — pinned with FROZEN provenance so the dossier reads exactly the
 *  receipt the analyst saw. Distinct from WorkbenchPin (a whole thread): a
 *  citation is a single source line. Citations live on the Investigation, never
 *  mixed into `pins`. */
export interface Citation {
  /** Stable id (see {@link citationId}) — url-derived when a url exists, else
   *  source+headline. Makes the pin idempotent and the button a toggle. */
  id: string
  headline: string
  source?: string
  url?: string
  /** @deprecated Council R2 N1: this field was historically populated from the
   *  story's SUBJECT country (country_code) and therefore must NEVER be
   *  rendered as an outlet origin ("LOCAL IR" / "COVERED FROM" lie class).
   *  Legacy records keep it (frozen pins are never destroyed); surfaces render
   *  {@link Citation.originCountry} only. */
  sourceCountry?: string
  /** ISO country code of the OUTLET's origin (signals_v2.source_origin_country)
   *  — the only legal basis for an origin/LOCAL assertion. Absent when the
   *  outlet's origin is unknown (absence over guess). */
  originCountry?: string
  /** ISO 639-1 base language of the receipt (source_lang). */
  sourceLang?: string
  gateStatus: CitationGateStatus
  /** ISO day (YYYY-MM-DD) the underlying signal was published, when known. */
  publishedDate?: string
  /** When the analyst pinned it (freeze time). */
  capturedAt: string
  investigationId: string
  note?: string
}

/** Everything the caller supplies; `capturedAt`/`investigationId` are stamped by
 *  {@link addCitation}, and `id` is derived when absent. */
export type CitationInput =
  Omit<Citation, 'capturedAt' | 'investigationId' | 'id'> & { id?: string }

/** Normalize any gate label a surface carries into the 4-value Citation tier.
 *  `assigned` (topic-assigned but below both tiers) collapses to `below_gate`;
 *  anything unrecognized (or absent) is `unknown`. */
export function toCitationGateStatus(raw: string | null | undefined): CitationGateStatus {
  switch (raw) {
    case 'verified': return 'verified'
    case 'extended': return 'extended'
    case 'below_gate':
    case 'assigned': return 'below_gate'
    default: return 'unknown'
  }
}

/** Deterministic, collision-resistant id for a receipt. Prefers the url (the
 *  true identity of a source line); falls back to source+headline so url-less
 *  receipts still toggle. Two renders of the same receipt yield the same id. */
export function citationId(c: { url?: string | null; headline: string; source?: string | null }): string {
  const url = (c.url ?? '').trim()
  if (url) return `cite:url:${url}`
  const src = (c.source ?? '').trim().toLowerCase()
  const head = (c.headline ?? '').trim()
  return `cite:txt:${src}::${head}`
}

export interface WorkbenchPin {
  anchorId: string
  anchorType: string
  label: string
  evidenceLabel?: string
  retrievalLane?: string
  matchBasis?: string
  investigativeScore?: number
  /** W3: R3 category lens (research-plan-v1 anchors carry it). */
  category?: string
  open?: { surface: string; params: Record<string, unknown> } | null
  note?: string
  /** #227: frozen evidence at pin time (Phase 3 reads this, not live data). */
  snapshot?: PinSnapshot
  pinnedAt: string
  planId?: string
  queryText?: string
}

export interface TrailStep {
  at: string
  action: 'search' | 'open' | 'pin' | 'unpin' | 'branch'
  detail: string
}

export interface Investigation {
  id: string
  title: string
  /** True once the analyst has explicitly renamed the investigation. The auto
   *  first-pin title is a fallback label; a custom title wins over the dossier
   *  synthesis headline. Presentation only — pin snapshots stay frozen. */
  titleCustom?: boolean
  /** The research-plan query this investigation was started from. Persisted so
   *  the plan panel can re-fetch on reopen — before this, the query lived only
   *  in App state and the plan was lost when the workbench closed. */
  query?: string
  createdAt: string
  updatedAt: string
  pins: WorkbenchPin[]
  /** Receipt-level pins (council wish 1) — SEPARATE from thread `pins`. Default
   *  [] for pre-citation records (migrated on read; never drops pins). */
  citations: Citation[]
  /** Analyst judgements over pairs of citations (Carolina's claim ledger).
   *  Default [] for pre-claim records (migrated on read; never drops pins). */
  claims: Claim[]
  trail: TrailStep[]
}

import { track, trackOnce } from './telemetry'
import { enqueueSnapshotFetch } from './articleEnrichment'
import { makeClaim, type Claim, type ClaimInput, type ClaimRelation } from './claimLedger'
export type { Claim, ClaimInput, ClaimRelation } from './claimLedger'

const STORE_KEY = 'atlas.workbench.v1'
const ACTIVE_KEY = 'atlas.workbench.active.v1'

interface StoreShape {
  investigations: Investigation[]
}

/** Safe forward-migration: a v1 record written before citations existed has no
 *  `citations` array. Default it to [] without touching `pins` (never lose a
 *  pin). Idempotent — a record that already has citations passes through. */
function normalizeInvestigation(inv: Investigation): Investigation {
  if (!Array.isArray(inv.citations)) inv.citations = []
  if (!Array.isArray(inv.claims)) inv.claims = []
  if (!Array.isArray(inv.pins)) inv.pins = []
  return inv
}

function readStore(): StoreShape {
  try {
    const raw = localStorage.getItem(STORE_KEY)
    if (!raw) return { investigations: [] }
    const parsed = JSON.parse(raw) as StoreShape
    if (!Array.isArray(parsed.investigations)) return { investigations: [] }
    parsed.investigations.forEach(normalizeInvestigation)
    return parsed
  } catch {
    return { investigations: [] }
  }
}

// ── accounts-v1 sync hook ────────────────────────────────────────────────
// Every mutation funnels through writeStore; subscribers (the sync engine)
// get the fresh investigation list after each write. Subscribers must never
// break the store — errors are swallowed (sync is best-effort by design).
type WorkbenchListener = (investigations: Investigation[]) => void
const changeListeners = new Set<WorkbenchListener>()

export function onWorkbenchChange(cb: WorkbenchListener): () => void {
  changeListeners.add(cb)
  return () => changeListeners.delete(cb)
}

function writeStore(store: StoreShape): void {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(store))
  } catch {
    // quota/eviction: investigation continues in memory for this session;
    // export is the durability mechanism.
  }
  for (const cb of changeListeners) {
    try { cb(store.investigations) } catch { /* sync must never break the store */ }
  }
}

export function listInvestigations(): Investigation[] {
  return readStore().investigations
    .slice()
    .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
}

export function getActiveInvestigationId(): string | null {
  try {
    return localStorage.getItem(ACTIVE_KEY)
  } catch {
    return null
  }
}

export function setActiveInvestigation(id: string | null): void {
  try {
    if (id) localStorage.setItem(ACTIVE_KEY, id)
    else localStorage.removeItem(ACTIVE_KEY)
  } catch { /* non-fatal */ }
}

export function getInvestigation(id: string): Investigation | null {
  return readStore().investigations.find(inv => inv.id === id) ?? null
}

/** The research-plan query for an investigation. Falls back to the most recent
 *  pin's queryText (pre-existing investigations lack the persisted query), then
 *  to the title — both were created from the original search query. */
export function investigationQuery(inv: Investigation): string {
  if (inv.query) return inv.query
  for (let i = inv.pins.length - 1; i >= 0; i--) {
    const q = inv.pins[i].queryText
    if (q) return q
  }
  return inv.title
}

/** Normalize a query for dedupe (trim + collapse whitespace + lowercase). */
function normQuery(q: string): string {
  return q.trim().replace(/\s+/g, ' ').toLowerCase()
}

export function createInvestigation(title: string, query?: string): Investigation {
  const now = new Date().toISOString()
  const q = (query ?? title).trim()
  // Dedupe (council P1-11, wish 4): a natural-query ramp that fires twice must
  // NOT leave two identical investigations. Reuse an existing same-query one
  // (make it active) instead of silently duplicating it.
  if (q) {
    const key = normQuery(q)
    const existing = readStore().investigations.find(
      i => i.query && normQuery(i.query) === key,
    )
    if (existing) {
      setActiveInvestigation(existing.id)
      return existing
    }
  }
  const inv: Investigation = {
    id: `inv-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    title: title.trim() || 'Untitled investigation',
    query: q || undefined,
    createdAt: now,
    updatedAt: now,
    pins: [],
    citations: [],
    claims: [],
    trail: [{ at: now, action: 'search', detail: title.trim() }],
  }
  const store = readStore()
  store.investigations.push(inv)
  writeStore(store)
  setActiveInvestigation(inv.id)
  // W0 (L3 review 2026-07-05): the anti-goal is ungovernable without these.
  track('investigation_created')
  return inv
}

function mutate(id: string, fn: (inv: Investigation) => void): Investigation | null {
  const store = readStore()
  const inv = store.investigations.find(i => i.id === id)
  if (!inv) return null
  fn(inv)
  inv.updatedAt = new Date().toISOString()
  writeStore(store)
  return inv
}

export function addPin(
  investigationId: string,
  pin: Omit<WorkbenchPin, 'pinnedAt'>,
): Investigation | null {
  let added = false
  const inv = mutate(investigationId, inv => {
    if (inv.pins.some(p => p.anchorId === pin.anchorId)) return // idempotent
    const stamped: WorkbenchPin = { ...pin, pinnedAt: new Date().toISOString() }
    inv.pins.push(stamped)
    inv.trail.push({ at: stamped.pinnedAt, action: 'pin', detail: pin.label })
    added = true
  })
  if (added) {
    track('pin', { anchor_type: pin.anchorType, lane: pin.retrievalLane })
    // Investigation value moment = created + ≥1 pin (decision D4, 2026-07-05).
    trackOnce('first_value_moment', { kind: 'investigation' })
    // Enrichment F1: fire-and-forget server-side fetch of the frozen evidence
    // URLs (spec 2026-07-20). Best-effort — the pin never waits or fails on it.
    enqueueSnapshotFetch(pin.snapshot)
  }
  return inv
}

/** W1: replace/enrich a pin's frozen snapshot (panel pins fetch their evidence
 *  asynchronously after the pin lands — the pin never waits on the network). */
export function updatePinSnapshot(
  investigationId: string, anchorId: string, snapshot: PinSnapshot,
): Investigation | null {
  const out = mutate(investigationId, inv => {
    const pin = inv.pins.find(p => p.anchorId === anchorId)
    if (!pin) return
    pin.snapshot = snapshot
  })
  // Enrichment F1: async-landed evidence (panel pins) also gets fetched.
  if (out) enqueueSnapshotFetch(snapshot)
  return out
}

/** #227: edit the analyst's per-pin note (the annotation the dossier carries). */
export function updatePinNote(
  investigationId: string, anchorId: string, note: string,
): Investigation | null {
  return mutate(investigationId, inv => {
    const pin = inv.pins.find(p => p.anchorId === anchorId)
    if (!pin) return
    pin.note = note
  })
}

// ── Receipt-level citations (council wish 1) ────────────────────────────────

/** Pin ONE receipt (evidence row) with frozen provenance. Idempotent by id.
 *  The id is derived from the receipt when the caller omits it. */
export function addCitation(
  investigationId: string, input: CitationInput,
): Investigation | null {
  const id = input.id ?? citationId(input)
  let added = false
  const inv = mutate(investigationId, inv => {
    if (inv.citations.some(c => c.id === id)) return // idempotent
    const cit: Citation = {
      ...input,
      id,
      capturedAt: new Date().toISOString(),
      investigationId,
    }
    inv.citations.push(cit)
    inv.trail.push({ at: cit.capturedAt, action: 'pin', detail: `receipt: ${cit.headline}` })
    added = true
  })
  if (added) {
    track('citation_pin', {
      gate_status: input.gateStatus,
      // N1: origin (outlet home) is the provenance dimension; the deprecated
      // subject-derived source_country is no longer emitted.
      origin_country: input.originCountry,
      source_lang: input.sourceLang,
    })
    // A pinned receipt is an investigation value moment (parity with addPin).
    trackOnce('first_value_moment', { kind: 'investigation' })
  }
  return inv
}

export function removeCitation(investigationId: string, id: string): Investigation | null {
  return mutate(investigationId, inv => {
    const idx = inv.citations.findIndex(c => c.id === id)
    if (idx === -1) return
    const [removed] = inv.citations.splice(idx, 1)
    inv.trail.push({ at: new Date().toISOString(), action: 'unpin', detail: `receipt: ${removed.headline}` })
  })
}

export function updateCitationNote(
  investigationId: string, id: string, note: string,
): Investigation | null {
  return mutate(investigationId, inv => {
    const cit = inv.citations.find(c => c.id === id)
    if (!cit) return
    cit.note = note
  })
}

export function listCitations(investigationId: string): Citation[] {
  return getInvestigation(investigationId)?.citations ?? []
}

/** True when this receipt is already pinned to the given investigation (drives
 *  the PinReceiptButton toggle state). */
export function isCitationPinned(investigationId: string | null, id: string): boolean {
  if (!investigationId) return false
  return (getInvestigation(investigationId)?.citations ?? []).some(c => c.id === id)
}

// ── Claim ledger (Carolina's spec) ──────────────────────────────────────────

/** Link two citations (or a citation + typed value) with a relation. Idempotent
 *  by the claim's pair id — a second call on the same pair relabels rather than
 *  duplicating (so selecting two receipts twice never stacks). */
export function addClaim(
  investigationId: string, input: Omit<ClaimInput, 'investigationId' | 'id' | 'createdAt'>,
): Investigation | null {
  const claim = makeClaim({ ...input, investigationId }, new Date().toISOString())
  let added = false
  const inv = mutate(investigationId, inv => {
    const existing = inv.claims.find(c => c.id === claim.id)
    if (existing) { // same pair re-marked: update the relation in place
      existing.relation = claim.relation
      existing.figure = claim.figure
      existing.typedValue = claim.typedValue
      return
    }
    inv.claims.push(claim)
    inv.trail.push({ at: claim.createdAt, action: 'branch', detail: `claim: ${claim.relation}` })
    added = true
  })
  if (added) track('claim_created', { relation: claim.relation })
  return inv
}

export function removeClaim(investigationId: string, id: string): Investigation | null {
  return mutate(investigationId, inv => {
    inv.claims = inv.claims.filter(c => c.id !== id)
  })
}

/** Change a claim's relation (CORROBORATES ↔ CONTRADICTS ↔ CONTEXT) in place. */
export function relabelClaim(
  investigationId: string, id: string, relation: ClaimRelation,
): Investigation | null {
  return mutate(investigationId, inv => {
    const claim = inv.claims.find(c => c.id === id)
    if (claim) claim.relation = relation
  })
}

export function listClaims(investigationId: string): Claim[] {
  return getInvestigation(investigationId)?.claims ?? []
}

/** Rename the investigation (presentation-only — pin snapshots stay frozen).
 *  Persisted so the title survives reopen; marks titleCustom so it wins over
 *  the dossier synthesis headline. Empty/blank title clears the override. */
export function renameInvestigation(id: string, title: string): Investigation | null {
  const trimmed = title.trim()
  return mutate(id, inv => {
    if (trimmed) {
      inv.title = trimmed
      inv.titleCustom = true
    } else {
      inv.titleCustom = false
    }
  })
}

export function removePin(investigationId: string, anchorId: string): Investigation | null {
  return mutate(investigationId, inv => {
    const idx = inv.pins.findIndex(p => p.anchorId === anchorId)
    if (idx === -1) return
    const [removed] = inv.pins.splice(idx, 1)
    inv.trail.push({ at: new Date().toISOString(), action: 'unpin', detail: removed.label })
  })
}

// ── Ergonomics: merge + move (council P1-11, wish 4) ────────────────────────

/** Merge investigation `sourceId` INTO `targetId`: union pins + citations +
 *  claims (deduped by id, target wins on conflict) and concatenate the trails
 *  in chronological order. The source is deleted; the survivor becomes active.
 *  No pin/citation/claim is ever dropped — a duplicate collapses, it never
 *  double-counts. Returns the merged survivor (null if either id is missing). */
export function mergeInvestigations(targetId: string, sourceId: string): Investigation | null {
  if (targetId === sourceId) return getInvestigation(targetId)
  const store = readStore()
  const target = store.investigations.find(i => i.id === targetId)
  const source = store.investigations.find(i => i.id === sourceId)
  if (!target || !source) return null

  const pinIds = new Set(target.pins.map(p => p.anchorId))
  for (const p of source.pins) if (!pinIds.has(p.anchorId)) target.pins.push(p)

  const citIds = new Set(target.citations.map(c => c.id))
  for (const c of source.citations) {
    if (!citIds.has(c.id)) target.citations.push({ ...c, investigationId: target.id })
  }

  const claimIds = new Set(target.claims.map(c => c.id))
  for (const c of source.claims) {
    if (!claimIds.has(c.id)) target.claims.push({ ...c, investigationId: target.id })
  }

  const now = new Date().toISOString()
  target.trail = [...target.trail, ...source.trail]
    .sort((a, b) => a.at.localeCompare(b.at))
  target.trail.push({ at: now, action: 'branch', detail: `merged “${source.title}” into this investigation` })
  target.updatedAt = now

  store.investigations = store.investigations.filter(i => i.id !== sourceId)
  writeStore(store)
  setActiveInvestigation(target.id)
  track('investigation_merged')
  return target
}

/** Move ONE pin from `fromId` to `toId`. No-op (false) when the pin is missing
 *  or the target already holds it (a conflict never loses the source's pin). */
export function movePin(anchorId: string, fromId: string, toId: string): boolean {
  if (fromId === toId) return false
  const store = readStore()
  const from = store.investigations.find(i => i.id === fromId)
  const to = store.investigations.find(i => i.id === toId)
  if (!from || !to) return false
  const idx = from.pins.findIndex(p => p.anchorId === anchorId)
  if (idx === -1) return false
  if (to.pins.some(p => p.anchorId === anchorId)) return false // conflict: keep source
  const now = new Date().toISOString()
  const [pin] = from.pins.splice(idx, 1)
  to.pins.push(pin)
  from.trail.push({ at: now, action: 'unpin', detail: `moved “${pin.label}” to ${to.title}` })
  to.trail.push({ at: now, action: 'pin', detail: `moved in “${pin.label}” from ${from.title}` })
  from.updatedAt = now
  to.updatedAt = now
  writeStore(store)
  track('pin_moved')
  return true
}

export function recordTrail(
  investigationId: string,
  action: TrailStep['action'],
  detail: string,
): void {
  mutate(investigationId, inv => {
    inv.trail.push({ at: new Date().toISOString(), action, detail })
  })
}

export function deleteInvestigation(id: string): void {
  const store = readStore()
  store.investigations = store.investigations.filter(i => i.id !== id)
  writeStore(store)
  if (getActiveInvestigationId() === id) setActiveInvestigation(null)
}

// JSON export is the v1 durability mechanism (spec amendment B3): the dossier
// (Phase 3) is generated from this same shape, so export early, export often.
export function exportInvestigationJSON(id: string): string | null {
  const inv = getInvestigation(id)
  if (!inv) return null
  return JSON.stringify(
    {
      format: 'atlas-investigation-v1',
      exportedAt: new Date().toISOString(),
      investigation: inv,
    },
    null,
    2,
  )
}
