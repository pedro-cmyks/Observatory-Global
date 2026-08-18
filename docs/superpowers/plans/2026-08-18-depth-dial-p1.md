# Depth Dial — Peldaño 1 (el conmutador) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** El dial LEER·OBSERVAR·CONSTRUIR como conmutador sobre el keep-alive existente — una puerta percibida, foco acarreado, cero cirugía de superficies.

**Architecture:** Una lib pura (`depthDial.ts`: posición, persistencia, destino con foco acarreado) + un componente (`DepthDial`) montado en el masthead del Brief y en la command bar del App. LEER=/brief · OBSERVAR=/app (display-toggle del shell keep-alive) · CONSTRUIR=/app con el Workbench abierto vía `?workbench=1`. El tiempo NO se toca: cada posición hereda su contrato temporal existente (invariante 6 del spec).

**Tech Stack:** React + vitest (frontend-v2 únicamente; cero backend). Spec: `docs/superpowers/specs/2026-08-18-depth-dial-design.md` §6-§7, §9.

**Regla del worktree compartido:** commits SOLO pathspec. ANTES de editar `App.tsx`/`main.tsx`: `git status --short` — si muestran cambios ajenos sin commitear (el chip del bundle corre en otra sesión y puede tocarlos), PARA y repórtalo.

**Forma del dial (provisional):** tres paradas NOMBRADAS (botones segmentados). La Ronda 3 del banco decidirá la forma final; el nombre-por-parada es la hipótesis más legible y es barata de re-vestir.

---

### Task 1: `lib/depthDial.ts` — la lib pura

**Files:**
- Create: `frontend-v2/src/lib/depthDial.ts`
- Test: `frontend-v2/src/lib/depthDial.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { DIAL_KEY, loadDialPosition, saveDialPosition, dialTarget, dialFromUrl } from './depthDial'

// vitest corre en node sin jsdom — el stub Map-backed es la convención del
// repo (workbench.test.ts:8-15, readerPlace.test.ts).
const store = new Map<string, string>()
vi.stubGlobal('localStorage', {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => { store.set(k, v) },
    removeItem: (k: string) => { store.delete(k) },
    clear: () => store.clear(),
})

describe('depthDial', () => {
    beforeEach(() => store.clear())

    it('primera visita: LEER (spec §7)', () => {
        expect(loadDialPosition()).toBe('leer')
    })

    it('persiste la elección; basura almacenada cae a leer', () => {
        saveDialPosition('observar')
        expect(loadDialPosition()).toBe('observar')
        store.set(DIAL_KEY, 'nonsense')
        expect(loadDialPosition()).toBe('leer')
    })

    it('dialFromUrl: ?depth= válido gana; ausente o inválido → null', () => {
        expect(dialFromUrl('?depth=observar')).toBe('observar')
        expect(dialFromUrl('?depth=zzz')).toBeNull()
        expect(dialFromUrl('?country=CO')).toBeNull()
    })

    describe('dialTarget — el destino con foco acarreado (invariante 4)', () => {
        it('leer desde /app: a /brief llevando SOLO country', () => {
            expect(dialTarget('leer', '?theme=dynamic-topic-9&country=CO&entry=x'))
                .toEqual({ path: '/brief', search: '?country=CO' })
            expect(dialTarget('leer', '?theme=dt-9'))
                .toEqual({ path: '/brief', search: '' })
        })

        it('observar desde /brief: a /app llevando country + entry=dial', () => {
            expect(dialTarget('observar', '?country=CO'))
                .toEqual({ path: '/app', search: '?country=CO&entry=dial' })
            expect(dialTarget('observar', ''))
                .toEqual({ path: '/app', search: '?entry=dial' })
        })

        it('construir: /app + workbench=1 + country', () => {
            expect(dialTarget('construir', '?country=VE'))
                .toEqual({ path: '/app', search: '?country=VE&entry=dial&workbench=1' })
        })
    })
})
```

- [ ] **Step 2: Run to fail**

Run: `cd frontend-v2 && export PATH="/opt/homebrew/opt/node@24/bin:$PATH" && npx vitest run src/lib/depthDial.test.ts`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement**

```ts
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
```

- [ ] **Step 4: Run to pass** — same command. Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/lib/depthDial.ts frontend-v2/src/lib/depthDial.test.ts
git commit -m "feat(dial): lib pura del dial — posicion, persistencia, destino con foco acarreado (P1)"
```

### Task 2: componente `DepthDial` + claves uiCopy

**Files:**
- Create: `frontend-v2/src/components/DepthDial.tsx`
- Create: `frontend-v2/src/components/DepthDial.css`
- Modify: `frontend-v2/src/lib/uiCopy.ts` (añadir claves; seguir la convención exacta del archivo)
- Test: `frontend-v2/src/components/DepthDial.test.tsx`

- [ ] **Step 1: claves uiCopy** (mismas reglas mecánicas del catálogo: placeholders/dígitos/no-copias):

```ts
'dial.leer':      { en: 'Read',    es: 'Leer' },
'dial.observar':  { en: 'Observe', es: 'Observar' },
'dial.construir': { en: 'Build',   es: 'Construir' },
'dial.tip':       { en: 'Depth: how much instrument you see. Your place, focus and warnings travel with you.',
                    es: 'Profundidad: cuánto instrumento ves. Tu lugar, tu foco y las advertencias viajan contigo.' },
```

- [ ] **Step 2: Write the failing test**

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, fireEvent } from '@testing-library/react'
import { DepthDial } from './DepthDial'

describe('DepthDial', () => {
    it('tres paradas, la activa marcada con aria-pressed', () => {
        const { getAllByRole } = render(<DepthDial active="observar" onSelect={() => {}} />)
        const btns = getAllByRole('button')
        expect(btns).toHaveLength(3)
        expect(btns[1].getAttribute('aria-pressed')).toBe('true')
        expect(btns[0].getAttribute('aria-pressed')).toBe('false')
    })

    it('click en parada inactiva dispara onSelect; en la activa, no', () => {
        const onSelect = vi.fn()
        const { getAllByRole } = render(<DepthDial active="leer" onSelect={onSelect} />)
        fireEvent.click(getAllByRole('button')[2])
        expect(onSelect).toHaveBeenCalledWith('construir')
        onSelect.mockClear()
        fireEvent.click(getAllByRole('button')[0])
        expect(onSelect).not.toHaveBeenCalled()
    })
})
```

(Si los tests del repo no usan @testing-library, mira cómo testean
componentes los suites existentes y adapta — las aserciones se mantienen.)

- [ ] **Step 3: Implement**

```tsx
import React from 'react'
import { useUiCopy } from '../lib/uiCopy'
import type { DialPosition } from '../lib/depthDial'
import './DepthDial.css'

// El conmutador de profundidad (P1). Forma provisional: tres paradas
// nombradas — la Ronda 3 del banco decide la forma final. Honestidad: el
// dial cambia VESTUARIO; el tip lo dice y nada más (G-SIN-OPINIÓN).
const ORDER: DialPosition[] = ['leer', 'observar', 'construir']

export function DepthDial({ active, onSelect }: {
    active: DialPosition
    onSelect: (p: DialPosition) => void
}) {
    const tr = useUiCopy()
    return (
        <div className="depth-dial" role="group" aria-label={tr('dial.tip')} data-tip={tr('dial.tip')}>
            {ORDER.map(p => (
                <button
                    key={p}
                    type="button"
                    className={`depth-dial-stop${p === active ? ' active' : ''}`}
                    aria-pressed={p === active}
                    onClick={() => { if (p !== active) onSelect(p) }}
                >
                    {tr(`dial.${p}`)}
                </button>
            ))}
        </div>
    )
}
```

CSS (`DepthDial.css`, tokens de la casa, cero paleta nueva; piso táctil 44px
en `(max-width:768px),(pointer:coarse)` como el ReaderLanguagePicker):

```css
.depth-dial { display: inline-flex; gap: 2px; border: 1px solid var(--border, rgba(128,128,128,.4)); border-radius: 4px; padding: 2px; }
.depth-dial-stop { font: inherit; font-size: 11px; letter-spacing: .08em; text-transform: uppercase; background: transparent; border: none; border-radius: 3px; padding: 4px 10px; cursor: pointer; opacity: .65; }
.depth-dial-stop.active { opacity: 1; background: var(--surface-2, rgba(128,128,128,.15)); font-weight: 600; }
@media (max-width: 768px), (pointer: coarse) {
    .depth-dial-stop { min-height: 44px; min-width: 44px; }
}
```

- [ ] **Step 4: Run** `npx vitest run src/components/DepthDial.test.tsx` + catálogo uiCopy. Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/components/DepthDial.tsx frontend-v2/src/components/DepthDial.css frontend-v2/src/lib/uiCopy.ts frontend-v2/src/components/DepthDial.test.tsx
git commit -m "feat(dial): componente DepthDial — 3 paradas nombradas, aria, es/en, piso tactil (P1)"
```

### Task 3: montar en el Brief (LEER)

**Files:**
- Modify: `frontend-v2/src/pages/BriefNewspaper.tsx` (masthead, junto al chip «Abrir consola» de `:1867`)

- [ ] **Step 1**: en el masthead, REEMPLAZAR el chip «Abrir consola» (`goToAtlas(...)` en `:1867`, clave `brief.action.console`) por `<DepthDial active="leer" onSelect={...} />`:

```tsx
<DepthDial
    active="leer"
    onSelect={(p) => {
        saveDialPosition(p)
        track('dial_change', { to: p, from: 'leer' })
        const t = dialTarget(p, countryFilter ? `?country=${countryFilter}` : '')
        navigate(`${t.path}${t.search}`)
    }}
/>
```

(imports: `DepthDial`, `dialTarget`, `saveDialPosition`; `track` ya existe en
el archivo — usa la firma real que uses ahí. `countryFilter` es el país
activo del Brief — verifica el nombre real de la variable en el masthead.)

- [ ] **Step 2**: soporte de deep-link `?depth=` en /brief: al montar, si `dialFromUrl(location.search)` devuelve `observar`/`construir` → navegar a `dialTarget(...)` (respeta spec §7). Un `useEffect` con guard de una sola ejecución.

- [ ] **Step 3**: vitest completo + `npm run build`. Expected: verdes; el catálogo uiCopy nota que `brief.action.console` puede quedar huérfana — elimínala SOLO si ningún otro sitio la usa (grep).

- [ ] **Step 4: Commit**

```bash
git add frontend-v2/src/pages/BriefNewspaper.tsx frontend-v2/src/lib/uiCopy.ts
git commit -m "feat(dial): el masthead del Brief cambia 'Abrir consola' por el dial — LEER activo, foco acarreado (P1)"
```

### Task 4: montar en el App (OBSERVAR·CONSTRUIR)

**Files:**
- Modify: `frontend-v2/src/App.tsx` (command bar; el botón «INICIO»/`navigate('/brief')` de `:1737`; `setWorkbenchOpen` de `:298`)

- [ ] **Step 1** (ANTES: `git status --short` — si App.tsx trae cambios ajenos, PARA y reporta): en la command bar, junto a donde vive el botón que navega a `/brief` (`:1737`), montar el dial. Posición activa DERIVADA: `workbenchOpen ? 'construir' : 'observar'`:

```tsx
<DepthDial
    active={workbenchOpen ? 'construir' : 'observar'}
    onSelect={(p) => {
        saveDialPosition(p)
        track('dial_change', { to: p, from: workbenchOpen ? 'construir' : 'observar' })
        if (p === 'construir') { setWorkbenchOpen(true); return }
        if (p === 'observar') { setWorkbenchOpen(false); return }
        const t = dialTarget('leer', location.search)
        navigate(`${t.path}${t.search}`)
    }}
/>
```

El botón INICIO existente queda SUBSUMIDO por la parada LEER — retíralo si
era solo navegación a /brief (grep sus usos primero); el botón WORKBENCH se
queda (herramienta de poder, ahora redundante con CONSTRUIR — no se toca).

- [ ] **Step 2**: manejar `?workbench=1`: `useEffect` sobre `location.search` — si el param está, `setWorkbenchOpen(true)` y STRIP del param (el patrón exacto de `entry=`/`lens=` que App ya usa — búscalo y copia su forma, incluida la limpieza de URL sin re-render loop).

- [ ] **Step 3**: móvil ≤768: el dial NO se monta en App (la tab shell existe; el spec §6 dice que las tabs lo absorben en P2). Guard con el mismo `isMobile` del archivo.

- [ ] **Step 4**: vitest completo + build. Expected: verdes.

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/App.tsx
git commit -m "feat(dial): la command bar deriva OBSERVAR/CONSTRUIR del workbench y viaja a LEER con el foco; ?workbench=1 abre el Workbench (P1)"
```

### Task 5: los gates (§9 del spec) + cierre

- [ ] **Step 1 — G-FOCO (browser, preview launch.json, pestaña propia)**: script de 10 travesías: en /brief fijar país CO (selector de lugar) → dial OBSERVAR → verificar URL `/app?country=CO&entry=dial` y que el foco país está activo (chip/heat) → dial LEER → de vuelta `/brief?country=CO` con «Cerca de ti · Colombia» → repetir ×5 (incluye una con VE). **10/10 o FAIL.**
- [ ] **Step 2 — G-HONESTIDAD (mecánica)**: con una historia grab-bag servida hoy, verificar el chip visible en /brief (tarjeta) Y en el console (fila del lens/rail) — la marca existe en ambas posiciones. Cero marcas perdidas al deslizar.
- [ ] **Step 3 — G-VELOCIDAD**: `/brief` sigue <1s contra prod (curl del API + carga del preview); el dial no añadió fetch alguno a LEER.
- [ ] **Step 4 — G-NAV-LOSS re-run**: los deep links existentes viven: `?lens=story&theme=` abre el lens · `?theme=` abre detalle · `?entry=brief` intacto · el walkthrough de país no se dispara en falso al llegar por dial (verificar 1 travesía con localStorage limpio).
- [ ] **Step 5**: suites completas (vitest + build; backend no se tocó — `git status` debe mostrarlo), commits pathspec, y reporte final: travesías 10/10, capturas de qué se vio, cualquier desviación.

**NO push, NO deploy** — el controlador cierra (push a ambos refs → Vercel).

---

## Self-review

- **Spec §6 P1** cubierto (T1-T4); **§7** persistencia+?depth= (T1/T3); **§9 P1** los 4 gates (T5); **invariante 4** foco = `dialTarget` testeado; **invariante 6** tiempo = intocado por construcción (cero cambios a selectores/scrubbers); **invariante 3** honestidad = G-HONESTIDAD.
- Tipos consistentes: `DialPosition`/`dialTarget`/`saveDialPosition` idénticos en T1-T4.
- Riesgo declarado: colisión con el chip del bundle en App.tsx/main.tsx → guard de Step 1 del T4.
- Fuera de alcance P1 (spec): redirect-por-preferencia al entrar desde Landing (P2), tabs móviles como dial (P2), forma final del dial (banco R3).
