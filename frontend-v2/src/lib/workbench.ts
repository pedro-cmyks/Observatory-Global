// Workbench investigation store (Phase 2, spec §Workbench / #213).
//
// v1 storage is localStorage — per-browser and evictable, NOT a durable
// archive (spec amendment B3). Durability comes from JSON export and the
// server-side pin-event log (#218). Multiple investigations live side by
// side; pins from different investigations never silently mix.

export interface WorkbenchPin {
  anchorId: string
  anchorType: string
  label: string
  evidenceLabel?: string
  retrievalLane?: string
  matchBasis?: string
  investigativeScore?: number
  open?: { surface: string; params: Record<string, unknown> } | null
  note?: string
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
  createdAt: string
  updatedAt: string
  pins: WorkbenchPin[]
  trail: TrailStep[]
}

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

export function createInvestigation(title: string): Investigation {
  const now = new Date().toISOString()
  const inv: Investigation = {
    id: `inv-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    title: title.trim() || 'Untitled investigation',
    createdAt: now,
    updatedAt: now,
    pins: [],
    trail: [{ at: now, action: 'search', detail: title.trim() }],
  }
  const store = readStore()
  store.investigations.push(inv)
  writeStore(store)
  setActiveInvestigation(inv.id)
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
  return mutate(investigationId, inv => {
    if (inv.pins.some(p => p.anchorId === pin.anchorId)) return // idempotent
    const stamped: WorkbenchPin = { ...pin, pinnedAt: new Date().toISOString() }
    inv.pins.push(stamped)
    inv.trail.push({ at: stamped.pinnedAt, action: 'pin', detail: pin.label })
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
