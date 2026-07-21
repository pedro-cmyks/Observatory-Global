export type Lane = 'who' | 'where' | 'what'
export interface LaneSnapshotHint { countryCode?: string }

const WHO = new Set(['person', 'source'])
const WHERE = new Set(['country'])
const GEO_IF_COUNTRY = new Set(['event', 'anomaly', 'signal'])

export function pinLane(anchorType: string, snapshot?: LaneSnapshotHint): Lane {
  if (WHO.has(anchorType)) return 'who'
  if (WHERE.has(anchorType)) return 'where'
  if (GEO_IF_COUNTRY.has(anchorType) && snapshot?.countryCode) return 'where'
  return 'what'
}

export interface LanePin { anchorType: string; snapshot?: { countryCode?: string } }
export function groupPinsByLane<T extends LanePin>(pins: T[]): { who: T[]; where: T[]; what: T[] } {
  const g = { who: [] as T[], where: [] as T[], what: [] as T[] }
  for (const p of pins) g[pinLane(p.anchorType, p.snapshot)].push(p)
  return g
}
