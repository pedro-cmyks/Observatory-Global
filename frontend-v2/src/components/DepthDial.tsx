import { useUiCopy } from '../lib/uiCopy'
import type { UiCopyKey } from '../lib/uiCopy'
import type { DialPosition } from '../lib/depthDial'
import './DepthDial.css'

// El conmutador de profundidad (P1 — spec 2026-08-18-depth-dial-design §6).
// Forma provisional: tres paradas nombradas — la Ronda 3 del banco decide la
// forma final. Honestidad: el dial cambia VESTUARIO; el tip lo dice y nada
// más (invariante 5, sin opinión).
const ORDER: DialPosition[] = ['leer', 'observar', 'construir']

export interface DialStop {
    position: DialPosition
    ariaPressed: boolean
    copyKey: UiCopyKey
}

/** Modelo puro del render (testeable en node sin jsdom). */
export function buildDialStops(active: DialPosition): DialStop[] {
    return ORDER.map(p => ({
        position: p,
        ariaPressed: p === active,
        copyKey: `dial.${p}` as UiCopyKey,
    }))
}

/** Guard puro del click: la parada activa no re-dispara. */
export function handleDialSelect(
    active: DialPosition,
    clicked: DialPosition,
    onSelect: (p: DialPosition) => void,
): void {
    if (clicked !== active) onSelect(clicked)
}

export function DepthDial({ active, onSelect }: {
    active: DialPosition
    onSelect: (p: DialPosition) => void
}) {
    const { t: tr } = useUiCopy()
    return (
        <div className="depth-dial" role="group" aria-label={tr('dial.tip')} data-tip={tr('dial.tip')}>
            {buildDialStops(active).map(s => (
                <button
                    key={s.position}
                    type="button"
                    className={`depth-dial-stop${s.ariaPressed ? ' active' : ''}`}
                    aria-pressed={s.ariaPressed}
                    onClick={() => handleDialSelect(active, s.position, onSelect)}
                >
                    {tr(s.copyKey)}
                </button>
            ))}
        </div>
    )
}
