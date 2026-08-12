// Loading-delight feed — the rotation LoadingMoment consumes during load
// states. Two sources, merged: (1) MEASURED facts fetched from
// /api/v2/delight and cached in localStorage so the NEXT load reads them
// synchronously, offline, with zero network on the delight path; (2) bundled
// EVERGREEN facts about how Atlas works — the first-load / offline fallback.
// Honesty travels with each fact: measured facts carry measured_at + window,
// evergreen facts are labeled "about Atlas". Everything here is non-fatal by
// construction — a broken cache or failed fetch degrades to evergreen.

export interface DelightFact {
    id: string
    kind: 'measured' | 'evergreen'
    text: string
    window_hours?: number
    measured_at?: string
}

const STORE_KEY = 'atlas_delight_v1'
// Measured facts older than this are dropped, not shown stale.
const MAX_MEASURED_AGE_MS = 48 * 60 * 60 * 1000

export const EVERGREEN_FACTS: DelightFact[] = [
    { id: 'ev-silence', kind: 'evergreen', text: 'Atlas measures who says what — and who says nothing. Silence is data.' },
    { id: 'ev-gate', kind: 'evergreen', text: 'Every count you see is verified by the quality gate or labeled unverified. No middle ground.' },
    { id: 'ev-volume', kind: 'evergreen', text: 'Volume is not importance. Atlas heat blends velocity, surprise and voice diversity — not just noise.' },
    { id: 'ev-selfvoice', kind: 'evergreen', text: 'A story told only by outsiders reads differently. Atlas tracks how much a country covers itself.' },
    { id: 'ev-universe', kind: 'evergreen', text: 'On the universe map, positions are approximate; relations are exact. Atlas labels which is which.' },
    { id: 'ev-threads', kind: 'evergreen', text: 'Stories are grown from the data, not picked from a fixed list. New stories find their own name.' },
    { id: 'ev-empty', kind: 'evergreen', text: 'When a country shows zero stories, that is an honest empty. Atlas never pads with filler.' },
    { id: 'ev-languages', kind: 'evergreen', text: 'Atlas reads press in 30+ languages — and shows you when a story is only told in one.' },
    { id: 'ev-archive', kind: 'evergreen', text: 'The archive remembers: every story keeps its history, even after it leaves the front page.' },
    { id: 'ev-decay', kind: 'evergreen', text: 'Heat decays. What mattered yesterday must prove itself again today.' },
]

interface StoredFeed {
    facts: DelightFact[]
    fetchedAt: number
}

function isFact(f: unknown): f is DelightFact {
    if (!f || typeof f !== 'object') return false
    const o = f as Record<string, unknown>
    return typeof o.id === 'string'
        && (o.kind === 'measured' || o.kind === 'evergreen')
        && typeof o.text === 'string' && o.text.length > 0 && o.text.length < 400
}

// Pure: validate an arbitrary parsed payload into a clean fact list.
export function parseFacts(raw: unknown): DelightFact[] {
    if (!raw || typeof raw !== 'object') return []
    const facts = (raw as Record<string, unknown>).facts
    if (!Array.isArray(facts)) return []
    return facts.filter(isFact).slice(0, 12)
}

// Pure: deterministic shuffle keyed by day — same rotation order all day,
// different tomorrow. Measured facts lead (they are the fresh material),
// evergreen follows interleaved.
export function buildRotation(
    measured: DelightFact[],
    evergreen: DelightFact[],
    seed: number,
): DelightFact[] {
    const shuffled = (list: DelightFact[], s: number) => {
        const out = [...list]
        let x = (s || 1) >>> 0
        for (let i = out.length - 1; i > 0; i--) {
            // xorshift32 — deterministic, no Math.random
            x ^= x << 13; x >>>= 0
            x ^= x >> 17
            x ^= x << 5; x >>>= 0
            const j = x % (i + 1)
            ;[out[i], out[j]] = [out[j], out[i]]
        }
        return out
    }
    const m = shuffled(measured, seed)
    const e = shuffled(evergreen, seed + 7)
    // Interleave 2 measured : 1 evergreen while measured lasts.
    const rotation: DelightFact[] = []
    let mi = 0, ei = 0
    while (mi < m.length || ei < e.length) {
        if (mi < m.length) rotation.push(m[mi++])
        if (mi < m.length) rotation.push(m[mi++])
        if (ei < e.length) rotation.push(e[ei++])
    }
    return rotation
}

// Pure: honesty label for a fact.
export function factLabel(fact: DelightFact, now = Date.now()): string {
    if (fact.kind === 'evergreen') return 'about Atlas'
    const win = fact.window_hours ?? 24
    if (fact.measured_at) {
        const age = now - Date.parse(fact.measured_at)
        if (Number.isFinite(age) && age > 24 * 60 * 60 * 1000) {
            return `measured yesterday · ${win} h window`
        }
    }
    return `measured · last ${win} h`
}

function readStored(now: number): DelightFact[] {
    try {
        if (typeof localStorage === 'undefined') return []
        const raw = localStorage.getItem(STORE_KEY)
        if (!raw) return []
        const stored: StoredFeed = JSON.parse(raw)
        if (!stored || !Array.isArray(stored.facts)) return []
        if (now - stored.fetchedAt > MAX_MEASURED_AGE_MS) return []
        return stored.facts.filter(isFact)
    } catch {
        return []
    }
}

// Synchronous read for LoadingMoment — never awaits anything.
export function readDelightRotation(now = Date.now()): DelightFact[] {
    const daySeed = Math.floor(now / (24 * 60 * 60 * 1000))
    return buildRotation(readStored(now), EVERGREEN_FACTS, daySeed)
}

let refreshed = false

// Fire-and-forget background refresh; call once after the app is up.
// Failures are silent — the delight path never depends on this succeeding.
export function refreshDelightFeed(): void {
    if (refreshed) return
    refreshed = true
    try {
        fetch('/api/v2/delight')
            .then(r => (r.ok ? r.json() : null))
            .then(payload => {
                const facts = parseFacts(payload)
                if (facts.length === 0) return
                const stored: StoredFeed = { facts, fetchedAt: Date.now() }
                try {
                    localStorage.setItem(STORE_KEY, JSON.stringify(stored))
                } catch { /* storage full/blocked — evergreen carries it */ }
            })
            .catch(() => { /* best-effort */ })
    } catch { /* no fetch (very old env) — evergreen carries it */ }
}
