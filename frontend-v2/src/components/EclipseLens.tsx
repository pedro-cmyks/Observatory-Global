// L2 Console "Under the Radar" eclipse lens — the QUIET counterpart to
// AnomalyPanel's loud volume-spike alerts. Same pool of data as the L1 Brief strip
// (GET /api/v2/attention/eclipse + lib/attentionEclipse helpers), different channel:
// here each eclipsed story has two actions off the same row — OPEN the thread in the
// console (L2), or ◇ INVESTIGATE it (L3: seeds an investigation + pin + Workbench).
//
// The eclipse is window-global (today's coverage concentration), so unlike the
// country-scoped AnomalyPanel this fetches once at a fixed 24h and ignores focus.
import { useEffect, useState } from 'react'
import {
  type EclipseData,
  type EclipseItem,
  shouldShowEclipse,
  eclipseDominantLine,
  formatEclipseItem,
  decodeEntities,
} from '../lib/attentionEclipse'
import './EclipseLens.css'

interface Props {
  onOpenTopic: (topicId: string, label: string) => void
  onInvestigate: (item: EclipseItem) => void
}

export function EclipseLens({ onOpenTopic, onInvestigate }: Props) {
  const [data, setData] = useState<EclipseData | null>(null)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), 12000)
    fetch('/api/v2/attention/eclipse?hours=24', { signal: ctrl.signal })
      .then(r => (r.ok ? r.json() : null))
      .then(payload => { if (payload) setData(payload as EclipseData) })
      .catch(() => { /* diffuse day / unavailable — honest empty state */ })
      .finally(() => { clearTimeout(timer); setLoaded(true) })
    return () => { clearTimeout(timer); ctrl.abort() }
  }, [])

  if (!shouldShowEclipse(data)) {
    return (
      <div className="eclipse-lens eclipse-lens-empty">
        <p>
          {loaded
            ? 'No attention eclipse right now. Coverage is spread across many stories — nothing is being drowned out by a single dominant event.'
            : 'Checking whether one event is eclipsing the rest…'}
        </p>
      </div>
    )
  }

  const d = data as EclipseData
  return (
    <div className="eclipse-lens">
      <p className="eclipse-lens-banner">{decodeEntities(eclipseDominantLine(d))}</p>
      <div className="eclipse-lens-list">
        {d.selected.map(item => {
          const f = formatEclipseItem(item)
          return (
            <div key={item.topic_id} className="eclipse-lens-row">
              <button
                className="eclipse-lens-open"
                onClick={() => onOpenTopic(item.topic_id, item.label)}
                data-tip="Open this thread in the console"
              >
                <span className="eclipse-lens-label">
                  {decodeEntities(item.label)}
                  {f.rising && <span className="eclipse-lens-rising" data-tip="Rising despite the eclipse">▲</span>}
                </span>
                <span className="eclipse-lens-meta">{f.breadthLabel} · {f.sharePct} of coverage</span>
              </button>
              <button
                className="eclipse-lens-investigate"
                onClick={() => onInvestigate(item)}
                data-tip="Start an investigation from this eclipsed story"
                aria-label={`Investigate ${decodeEntities(item.label)}`}
              >
                ◇
              </button>
            </div>
          )
        })}
      </div>
      <p className="eclipse-lens-foot">
        Coverage-volume share — a proxy for attention, not audience eyeballs. Ranked candidates, not certified.
      </p>
    </div>
  )
}
