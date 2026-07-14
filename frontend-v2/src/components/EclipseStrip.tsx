// L1 "MEANWHILE, OFF THE FRONT PAGE" strip.
//
// Renders only when the day's coverage is ECLIPSED — one event dominating — AND
// consequential stories are running quiet underneath it. On a diffuse day (or a
// 404/failure) it renders nothing. Presentational: the page fetches the payload
// and owns routing; this component only reads the pure helpers.
import {
  type EclipseData,
  shouldShowEclipse,
  eclipseDominantLine,
  formatEclipseItem,
} from '../lib/attentionEclipse'
import './EclipseStrip.css'

interface Props {
  data: EclipseData | null
  onOpenTopic: (topicId: string, label: string) => void
}

export function EclipseStrip({ data, onOpenTopic }: Props) {
  if (!shouldShowEclipse(data)) return null
  const d = data as EclipseData
  return (
    <>
      <section className="brief-eclipse-strip">
        <h3
          className="brief-bottom-heading"
          data-tip="One event is dominating today's coverage. These stories are consequential (covered across many languages and countries) but hold a tiny share of coverage — running quiet in its shadow. Ranked candidates, not certified; 'coverage share' is media volume, not audience attention."
        >
          Meanwhile, off the front page
        </h3>
        <p className="brief-eclipse-lede">{eclipseDominantLine(d)}</p>
        <div className="brief-eclipse-list">
          {d.selected.map(item => {
            const f = formatEclipseItem(item)
            return (
              <button
                key={item.topic_id}
                className="brief-eclipse-row"
                onClick={() => onOpenTopic(item.topic_id, item.label)}
              >
                <span className="brief-eclipse-main">
                  <span className="brief-eclipse-label">{item.label}</span>
                  {f.rising && (
                    <span className="brief-eclipse-rising" data-tip="Coverage is rising despite the eclipse — a fresh under-the-radar story.">
                      ▲ rising
                    </span>
                  )}
                </span>
                <span className="brief-eclipse-meta">
                  <span className="brief-eclipse-breadth">{f.breadthLabel}</span>
                  <span className="brief-eclipse-share" data-tip="Share of the window's total coverage volume — how drowned out this story is.">
                    {f.sharePct} of coverage
                  </span>
                </span>
              </button>
            )
          })}
        </div>
      </section>
      <div className="brief-rule thin" />
    </>
  )
}
