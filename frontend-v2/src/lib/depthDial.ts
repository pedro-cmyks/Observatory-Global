// El dial de profundidad — Peldaño 1 (spec 2026-08-18-depth-dial-design §6).
// LEER · OBSERVAR · CONSTRUIR como conmutador sobre el keep-alive: la lib
// decide DESTINO y qué foco viaja (invariante 4: el foco sobrevive al
// deslizar — country cruza siempre; theme solo existe en el console y no se
// inventa un equivalente en /brief). El tiempo no se toca aquí: cada
// posición hereda su contrato temporal (invariante 6).
export const DIAL_KEY = 'atlas.reader.depth.v1'

export type DialPosition = 'leer' | 'observar' | 'construir'
const POSITIONS: DialPosition[] = ['leer', 'observar', 'construir']

export function loadDialPosition(): DialPosition {
    try {
        const raw = localStorage.getItem(DIAL_KEY)
        if (raw && (POSITIONS as string[]).includes(raw)) return raw as DialPosition
    } catch { /* storage unavailable → default */ }
    return 'leer'
}

export function saveDialPosition(p: DialPosition): void {
    try { localStorage.setItem(DIAL_KEY, p) } catch { /* best-effort */ }
}

/** ?depth= override — spec §7: un deep link que nombra posición, manda. */
export function dialFromUrl(search: string): DialPosition | null {
    const raw = new URLSearchParams(search).get('depth')
    return raw && (POSITIONS as string[]).includes(raw) ? (raw as DialPosition) : null
}

export interface DialTarget { path: string; search: string }

export function dialTarget(p: DialPosition, currentSearch: string): DialTarget {
    const cur = new URLSearchParams(currentSearch)
    const next = new URLSearchParams()
    const country = cur.get('country') || cur.get('country_code')
    if (country) next.set('country', country)
    if (p === 'leer') {
        const s = next.toString()
        return { path: '/brief', search: s ? `?${s}` : '' }
    }
    next.set('entry', 'dial')
    if (p === 'construir') next.set('workbench', '1')
    return { path: '/app', search: `?${next.toString()}` }
}
