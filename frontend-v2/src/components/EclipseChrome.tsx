import { createPortal } from 'react-dom'
import { useEclipseMode } from '../contexts/EclipseModeContext'
import { decodeEntities } from '../lib/attentionEclipse'

/** Portaled eclipse chrome (ambient ribbon + muted sigil), rendered to
 * document.body so it sits ABOVE the absolutely-positioned command bar and
 * OUTSIDE #root's grayscale filter (keeps the eclipse-red). */
export function EclipseChrome() {
  const { data, mode, act } = useEclipseMode()
  if (mode === 'ambient' && data) {
    const label = decodeEntities(data.dominant?.label ?? 'one story')
    return createPortal(
      <div className="eclipse-ribbon">
        ◑ Eclipsed · <b>{`“${label}”`}</b> is eclipsing the world
        <button className="eclipse-ribbon-x" onClick={() => act('mute')} data-tip="Exit the eclipse view">✕ exit eclipse</button>
      </div>,
      document.body,
    )
  }
  if (mode === 'muted') {
    return createPortal(
      <button className="eclipse-map-sigil" onClick={() => act('restore')}
              data-tip="An eclipse is active — re-enter the eclipse view" aria-label="Re-enter eclipse view" />,
      document.body,
    )
  }
  return null
}
