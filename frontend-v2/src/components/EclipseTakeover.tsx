import { createPortal } from 'react-dom'
import { useEclipseMode } from '../contexts/EclipseModeContext'
import { decodeEntities, eclipseDominantLabel } from '../lib/attentionEclipse'
import './EclipseTakeover.css'

export function EclipseTakeover() {
  const { data, mode, act } = useEclipseMode()
  if (mode !== 'takeover' || !data) return null
  // N28: resolved, never the raw `dominant.label` — the dominant can be a
  // category bucket whose label is its own slug.
  const label = decodeEntities(eclipseDominantLabel(data))
  const share = Math.round((data.dominant?.share ?? data.window?.top1_share ?? 0) * 100)
  const cd = data.axes?.country_dominance
  const nCountries = cd != null ? Math.round(cd * 100) : null

  return createPortal(
    <div className="eclipse-takeover" role="dialog" aria-label="Attention eclipse" aria-modal="true">
      <div className="eclipse-takeover-disc-wrap"><div className="eclipse-takeover-disc" /></div>
      <div className="eclipse-takeover-content">
        <div className="eclipse-takeover-eyebrow">Total eclipse of attention</div>
        <h1 className="eclipse-takeover-headline">{`“${label}”`}</h1>
        <div className="eclipse-takeover-stats">
          {`${share}% of the world's coverage`}
          {nCountries != null && ` · leading in ${nCountries}% of countries`}
        </div>
        <div className="eclipse-takeover-honesty">
          Coverage-volume concentration — a proxy for attention, not audience eyeballs. Ranked, not certified.
        </div>
        <div className="eclipse-takeover-actions">
          <button className="eclipse-btn eclipse-btn-primary" onClick={() => act('enter')}>Enter the eclipse ▸</button>
          <button className="eclipse-btn eclipse-btn-ghost" onClick={() => act('enter')}>The stories in its shadow →</button>
        </div>
      </div>
    </div>,
    document.body,
  )
}
