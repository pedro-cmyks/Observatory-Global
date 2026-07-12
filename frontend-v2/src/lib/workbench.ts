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
  evidence?: Array<{ headline: string; source?: string; url?: string }>
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
  trail: TrailStep[]
}

import { track, trackOnce } from './telemetry'

const STORE_KEY = 'atlas.workbench.v1'
const ACTIVE_KEY = 'atlas.workbench.active.v1'

interface StoreShape {
  investigations: Investigation[]
}

function readStore(): StoreShape {
  try {
    const raw = localStorage.getItem(STORE_KEY)
    if (!raw) return { investigations: [] }
    const parsed = JSON.parse(raw) as StoreShape
    if (!Array.isArray(parsed.investigations)) return { investigations: [] }
    return parsed
  } catch {
    return { investigations: [] }
  }
}

function writeStore(store: StoreShape): void {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(store))
  } catch {
    // quota/eviction: investigation continues in memory for this session;
    // export is the durability mechanism.
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

export function createInvestigation(title: string, query?: string): Investigation {
  const now = new Date().toISOString()
  const q = (query ?? title).trim()
  const inv: Investigation = {
    id: `inv-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    title: title.trim() || 'Untitled investigation',
    query: q || undefined,
    createdAt: now,
    updatedAt: now,
    pins: [],
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
  }
  return inv
}

/** W1: replace/enrich a pin's frozen snapshot (panel pins fetch their evidence
 *  asynchronously after the pin lands — the pin never waits on the network). */
export function updatePinSnapshot(
  investigationId: string, anchorId: string, snapshot: PinSnapshot,
): Investigation | null {
  return mutate(investigationId, inv => {
    const pin = inv.pins.find(p => p.anchorId === anchorId)
    if (!pin) return
    pin.snapshot = snapshot
  })
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
