// Task 2.2 (Exploration Flywheel): ambient exploration Trail — a lightweight
// record of where the analyst browsed, separate from deliberate pins.
// Own localStorage key, own ring buffer, NEVER synced (accounts-v1 sync only
// pushes workbench.ts investigations/pins) and never mixed with the
// per-investigation trail (`recordTrail` in workbench.ts). Best-effort: a
// storage failure never throws into the caller (recordTrailStep is called
// from every panel visit).
const KEY = 'atlas.frame.trail.v1'
export const TRAIL_CAP = 50

export interface TrailStep {
    surface: string
    kind: string
    value: string
    label: string
    at: string
}

export type TrailInput = Omit<TrailStep, 'at'> & { at?: string }

export function readTrail(): TrailStep[] {
    try {
        const raw = localStorage.getItem(KEY)
        return raw ? (JSON.parse(raw) as TrailStep[]) : []
    } catch {
        return []
    }
}

export function recordTrailStep(input: TrailInput): void {
    try {
        const prev = readTrail()
        if (prev[0] && prev[0].kind === input.kind && prev[0].value === input.value) return
        const step: TrailStep = { ...input, at: input.at ?? new Date().toISOString() }
        const next = [step, ...prev].slice(0, TRAIL_CAP)
        localStorage.setItem(KEY, JSON.stringify(next))
    } catch {
        /* best-effort */
    }
}
