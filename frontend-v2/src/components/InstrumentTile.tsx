// The Instrument Skin component family (`.atlas-instrument`) — the presentation
// QUARANTINE for MEASURED market data (design §7). A market number renders only
// through these primitives so it can never fuse into a narrative claim, arrow, or
// headline. Descriptive only: level + trend, NEVER a correlation / lead-lag /
// "news moved this" / trade signal.
import { type KeyboardEvent } from 'react'
import {
  type MarketInstrument,
  type MarketDirection,
  changeDirection,
  formatChangePct,
  formatLevel,
  directionGlyph,
  unitTag,
  RELATION_PENDING_TEXT,
  NOT_ADVICE_TEXT,
} from '../lib/markets'
import './InstrumentSkin.css'

// TODO dedup with NarrativeThreads/Brief sparkline — those two are timeline-count
// sparks (max-normalized, zero baseline). This one is a PRICE spark: self-normalized
// to the instrument's own [min,max] with a non-zero padded baseline so a nearly-flat
// series reads as flat, not as a floor-hugging collapse. A future shared <Sparkline>
// should take a `mode: 'count' | 'price'` prop; not unified here to keep the build safe.
export function InstrumentSpark({
  series,
  direction,
  width = 88,
  height = 26,
}: {
  series: number[] | null | undefined
  direction: MarketDirection
  width?: number
  height?: number
}) {
  const clean = (series ?? []).filter(v => typeof v === 'number' && isFinite(v))
  if (clean.length < 2) {
    return <span className="atlas-instrument-spark atlas-instrument-spark--empty" aria-hidden="true" />
  }
  const min = Math.min(...clean)
  const max = Math.max(...clean)
  const range = max - min || Math.abs(max) || 1
  // Non-zero baseline: pad the value range so the line sits inside the box and a
  // flat series does not collapse onto the floor.
  const pad = range * 0.14
  const lo = min - pad
  const hi = max + pad
  const span = hi - lo || 1
  const step = width / (clean.length - 1)
  const points = clean
    .map((v, i) => `${(i * step).toFixed(1)},${(height - ((v - lo) / span) * height).toFixed(1)}`)
    .join(' ')
  // svg stretches to the tile width (width="100%"); the viewBox keeps the coordinate
  // space so the polyline never spills outside the tile (the old fixed 88px svg
  // overflowed narrow tiles).
  return (
    <span
      className={`atlas-instrument-spark atlas-instrument-spark--${direction}`}
      data-tip="30-day close shape only — self-scaled to this instrument's own range; compare by the printed last-close, not amplitude."
    >
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} preserveAspectRatio="none">
        <polyline points={points} fill="none" stroke="currentColor" strokeWidth="1.4" />
      </svg>
    </span>
  )
}

// The boxed instrument tile: identity + as-of-implied level + trend, inside the
// quarantine container. Inert by default (the Brief passes no onClick). In the
// console dock an optional `onClick` drills to a bigger IN-PANEL chart — it never
// jumps to a narrative panel, so the quarantine holds.
export function InstrumentTile({ inst, onClick }: { inst: MarketInstrument; onClick?: () => void }) {
  const dir = changeDirection(inst.change_pct)
  const pct = formatChangePct(inst.change_pct)
  const clickable = !!onClick
  return (
    <div
      className={`atlas-instrument atlas-instrument-tile atlas-instrument--${dir}${clickable ? ' atlas-instrument-tile--clickable' : ''}`}
      data-symbol={inst.symbol}
      {...(clickable
        ? {
            role: 'button',
            tabIndex: 0,
            onClick,
            onKeyDown: (e: KeyboardEvent) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                onClick()
              }
            },
            'data-tip': 'Open a bigger chart for this instrument (in-panel — stays in markets).',
          }
        : {})}
    >
      <div className="atlas-instrument-head">
        <span className="atlas-instrument-label" title={inst.symbol}>{inst.label || inst.symbol}</span>
        <span className="atlas-instrument-class">{unitTag(inst)}</span>
      </div>
      {inst.price_pending ? (
        <div className="atlas-instrument-pending" data-tip="No close ingested yet — the descriptive skeleton never fabricates a tick.">
          price pending
        </div>
      ) : (
        <>
          <div className="atlas-instrument-level">{formatLevel(inst.last_close)}</div>
          <div className="atlas-instrument-foot">
            {pct ? (
              <span className={`atlas-instrument-change atlas-instrument-change--${dir}`}>
                {directionGlyph(dir)} {pct}
              </span>
            ) : (
              <span className="atlas-instrument-change atlas-instrument-change--flat">·</span>
            )}
          </div>
          <InstrumentSpark series={inst.spark_30d} direction={dir} />
        </>
      )}
    </div>
  )
}

// The in-panel drill chart — a bigger view of ONE instrument (console dock only).
// Still the quarantine: descriptive level + 30-day close shape + a back control;
// NEVER a relation, a forecast, or a jump out to a narrative panel.
export function InstrumentChart({ inst, onBack }: { inst: MarketInstrument; onBack: () => void }) {
  const dir = changeDirection(inst.change_pct)
  const pct = formatChangePct(inst.change_pct)
  const series = (inst.spark_30d ?? []).filter(v => typeof v === 'number' && isFinite(v))
  const hasChart = series.length >= 2
  let path = ''
  let lo = 0
  let hi = 0
  if (hasChart) {
    const min = Math.min(...series)
    const max = Math.max(...series)
    const range = max - min || Math.abs(max) || 1
    const pad = range * 0.1
    lo = min - pad
    hi = max + pad
    const span = hi - lo || 1
    const W = 300
    const H = 90
    const step = W / (series.length - 1)
    path = series
      .map((v, i) => `${(i * step).toFixed(1)},${(H - ((v - lo) / span) * H).toFixed(1)}`)
      .join(' ')
  }
  return (
    <div className="atlas-instrument markets-chart">
      <button className="markets-chart-back" onClick={onBack}>← Back to markets</button>
      <div className="markets-chart-head">
        <span className="markets-chart-label" title={inst.symbol}>{inst.label || inst.symbol}</span>
        <span className="atlas-instrument-class">{unitTag(inst)}</span>
        <span className="markets-chart-symbol">{inst.symbol}</span>
      </div>
      {inst.price_pending ? (
        <div className="atlas-instrument-pending">price pending — the cron fills this on the next run.</div>
      ) : (
        <>
          <div className="markets-chart-levelrow">
            <span className="markets-chart-level">{formatLevel(inst.last_close)}</span>
            {pct && (
              <span className={`atlas-instrument-change atlas-instrument-change--${dir}`}>
                {directionGlyph(dir)} {pct} · 30d
              </span>
            )}
          </div>
          {hasChart ? (
            <div className={`markets-chart-plot atlas-instrument-spark--${dir}`}>
              <svg viewBox="0 0 300 90" width="100%" height="120" preserveAspectRatio="none">
                <polyline points={path} fill="none" stroke="currentColor" strokeWidth="1.6" />
              </svg>
              <div className="markets-chart-scale">
                <span>{formatLevel(hi)}</span>
                <span>{formatLevel(lo)}</span>
              </div>
            </div>
          ) : (
            <p className="markets-note">Not enough history yet — fills over the next cron runs.</p>
          )}
          <p className="markets-chart-foot">30-day close series · self-scaled shape · descriptive, not a trade signal.</p>
        </>
      )}
    </div>
  )
}

// The two-state honesty chip. `descriptive` = the lit, active state (ships now).
// `relation` = the reserved-but-DARK slot (gated on #226, never a number).
export function InstrumentHonestyChip({ state }: { state: 'descriptive' | 'relation' }) {
  if (state === 'relation') {
    return (
      <span
        className="atlas-instrument atlas-instrument-chip atlas-instrument-chip--relation-dark"
        data-tip="Whether news co-moves with an instrument is gated on the #226 event study — re-run ~Oct 2026. Never retrofitted onto a price."
      >
        RELATION · pending #226
      </span>
    )
  }
  return (
    <span
      className="atlas-instrument atlas-instrument-chip atlas-instrument-chip--descriptive"
      data-tip="Level and trend from the last market close — descriptive only; NOT a claim that news moved this."
    >
      DESCRIPTIVE · LAST CLOSE
    </span>
  )
}

// The greyed full-line relation-analysis slot — the honest absence of the gated
// tier. Never a number, never "news moved this".
export function RelationPendingSlot() {
  return (
    <div className="atlas-instrument atlas-instrument-relation-slot" data-tip="#226 event study re-runs at ~150 trading days (~Oct 2026).">
      {RELATION_PENDING_TEXT}
    </div>
  )
}

// The persistent no-trade-signal microcopy.
export function NotAdviceLine() {
  return <div className="atlas-instrument atlas-instrument-advice">{NOT_ADVICE_TEXT}</div>
}
