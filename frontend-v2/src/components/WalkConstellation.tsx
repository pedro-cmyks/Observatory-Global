// The walked constellation — multi-hop transitive kinship, RADIAL (spec
// docs/superpowers/specs/2026-07-21-multi-hop-transitive-chains.md §4).
//
// From the analyst's pins, the backend walks the whitened topic graph outward and
// returns KIN by honest distance. This surface draws them RADIALLY (pin at center,
// kin outward by degree — never a left-to-right chain, which would import the
// causation the walk exists to kill) and lets the analyst walk it one degree at a
// time ("¿ver primos?"). Every walked node is CLICKABLE + PINNABLE — the fix for the
// inert bridge stars (journey-map §1): opening/pinning a primo grows the
// investigation. v1 is UNDIRECTED — no causal arrow anywhere. Vanilla CSS + SVG.
import { useEffect, useMemo, useRef, useState } from 'react'
import {
  WALK_COLORS,
  degreeLabel,
  fetchWalk,
  hopColorRole,
  hopDash,
  hopWidth,
  layoutWalkRadial,
  nextDegree,
  nodeOpacity,
  nodeRadius,
  receiptLine,
  visibleKin,
  type WalkData,
  type WalkKin,
} from '../lib/constellationWalk'
import { connectionTopicIds } from '../lib/dossierConnections'
import type { Investigation } from '../lib/workbench'
import './WalkConstellation.css'

const W = 320
const H = 264

const truncate = (s: string, max: number) => (s.length > max ? s.slice(0, max - 1) + '…' : s)

export default function WalkConstellation({ inv, onOpen, onPin }: {
  inv: Investigation
  onOpen?: (topicId: string, label: string) => void
  /** Pin a walked node — grows the investigation (the flywheel ring). Returns
   *  whether the pin was newly added (for a light toast). */
  onPin?: (kin: WalkKin) => void
}) {
  const topicKey = useMemo(
    () => connectionTopicIds(inv).slice().sort().join('|'),
    [inv],
  )
  const topicCount = topicKey ? topicKey.split('|').length : 0

  const [relFloor, setRelFloor] = useState(0.35)
  const [maxDegree, setMaxDegree] = useState(1)
  const [data, setData] = useState<WalkData | null | undefined>(undefined)
  const [hover, setHover] = useState<string | null>(null)
  const invRef = useRef(inv)
  invRef.current = inv

  useEffect(() => {
    if (topicCount < 1) { setData(null); return }
    let alive = true
    setData(undefined)
    setMaxDegree(1) // re-reveal from hermanos when the pins or reach change
    fetchWalk(invRef.current, relFloor)
      .then(d => { if (alive) setData(d) })
      .catch(() => { if (alive) setData(null) })
    return () => { alive = false }
  }, [inv.id, topicKey, topicCount, relFloor])

  const placed = useMemo(() => {
    if (!data || data.kin.length === 0) return null
    return layoutWalkRadial(data.seeds, visibleKin(data.kin, maxDegree), W, H)
  }, [data, maxDegree])
  const byId = useMemo(() => new Map((placed ?? []).map(p => [p.id, p])), [placed])

  if (topicCount < 1) return null // from-pins: nothing to walk yet

  const kin = data?.kin ?? []
  const next = data ? nextDegree(kin, maxDegree) : null
  const hovered = hover ? kin.find(k => k.id === hover) : null

  return (
    <div className="walk">
      <div className="walk-head">
        <span
          className="walk-title"
          data-tip="Measured multi-hop kinship from your pins over the whitened topic graph. A HERMANO has a direct measured edge; a PRIMO Nº is reached only by walking N hops — no direct line, only this trail. Undirected: association, never cause. Every hop carries a receipt."
        >
          WALKED KIN
        </span>
        {data === undefined && <span className="walk-status">walking…</span>}
        {data && data.kin.length > 0 && (
          <span className="walk-status">
            {data.meta.hermanos ?? 0} hermano{(data.meta.hermanos ?? 0) === 1 ? '' : 's'}
            {' · '}{data.meta.primos ?? 0} primo{(data.meta.primos ?? 0) === 1 ? '' : 's'}
          </span>
        )}
      </div>

      {/* ¿hasta dónde caminar? — the relative-floor slider (spec §2.3). */}
      {data && data.kin.length > 0 && (
        <label className="walk-floor" data-tip="How far to walk: lower = reach further-out cousins along strong trails. The hard 3-hop cap is fixed.">
          <span>reach</span>
          <input
            type="range" min={0.15} max={0.6} step={0.05} value={relFloor}
            onChange={e => setRelFloor(Number(e.target.value))}
          />
        </label>
      )}

      {placed && (
        <svg viewBox={`0 0 ${W} ${H}`} className="walk-svg" role="img" aria-label="Walked constellation">
          {/* hop lines: parent → kin, honesty grammar (solid hermano / dashed primo,
              thickness = accumulated weight, color = why). Behind the nodes. */}
          {placed.map(p => {
            if (!p.kin) return null
            const parentId = p.kin.via.parent_id
            // parent is a placed seed or kin; a folded (non-represented) parent
            // falls back to the field center so the trail still reads outward.
            const parent = parentId ? byId.get(parentId) : null
            const fx = parent?.px ?? W / 2, fy = parent?.py ?? H / 2
            const role = hopColorRole(p.kin)
            const dim = hover && hover !== p.id && p.kin.via.parent_id !== hover
            return (
              <line
                key={`e-${p.id}`} x1={fx} y1={fy} x2={p.px} y2={p.py}
                stroke={WALK_COLORS[role]} strokeWidth={hopWidth(p.kin)}
                strokeDasharray={hopDash(p.kin)}
                strokeOpacity={dim ? 0.12 : 0.55}
              />
            )
          })}

          {/* nodes: seeds (pins) at center, kin outward. Size + opacity recede with
              degree. Click opens; the ◆ glyph pins (grows the investigation). */}
          {placed.map(p => {
            const isSeed = p.kinship === 'seed'
            const k = p.kin
            const r = isSeed ? 8 : nodeRadius(p.degree)
            const op = isSeed ? 1 : nodeOpacity(p.degree)
            const active = hover === p.id
            const dim = hover && !active && p.kin?.via.parent_id !== hover
            const role = k ? hopColorRole(k) : 'hermano'
            const label = truncate(p.label, 22)
            return (
              <g
                key={p.id} transform={`translate(${p.px},${p.py})`}
                className={`walk-node${isSeed ? ' seed' : ''}`}
                style={{ opacity: dim ? 0.3 : op, cursor: isSeed ? 'default' : 'pointer' }}
                onMouseEnter={() => !isSeed && setHover(p.id)}
                onMouseLeave={() => setHover(null)}
                onClick={() => { if (!isSeed && onOpen) onOpen(p.id, p.label) }}
              >
                <circle
                  r={r}
                  style={{ fill: isSeed ? '#e2e8f0' : WALK_COLORS[role] }}
                  fillOpacity={isSeed ? 1 : 0.75}
                  stroke={isSeed ? '#94a3b8' : WALK_COLORS[role]}
                  strokeWidth={active ? 2.2 : 1}
                />
                {(isSeed || active || p.degree <= 1) && (
                  <text y={-r - 3} textAnchor="middle" className="walk-node-label">{label}</text>
                )}
                {k && (
                  <text
                    className="walk-node-pin" x={r + 2} y={3} data-tip="Pin this story — grows the investigation (the galaxy grows a ring)."
                    onClick={ev => { ev.stopPropagation(); onPin?.(k) }}
                  >◆</text>
                )}
                {k && (active || p.degree <= 1) && (
                  <text y={r + 9} textAnchor="middle" className={`walk-degree ${k.kinship}`}>{degreeLabel(k)}</text>
                )}
              </g>
            )
          })}
        </svg>
      )}

      {/* honest orphan (spec §8): a semantic-orphan pin has no measured kin. */}
      {data && data.kin.length === 0 && (
        <div className="walk-orphan">
          no measured kin — {data.seeds.length > 1 ? 'these stories stand' : 'this story stands'} alone
        </div>
      )}
      {data === null && (
        <div className="walk-status walk-status--muted">walk unavailable — pins are unaffected</div>
      )}

      {/* the analyst walks it — one degree at a time (spec §4). */}
      {next !== null && (
        <button className="walk-more" onClick={() => setMaxDegree(next)}>
          ¿ver primos {next}º? →
        </button>
      )}

      {placed && (
        <div className="walk-legend">
          <span><i className="walk-k-solid" /> hermano (direct)</span>
          <span><i className="walk-k-dash" /> primo (walked)</span>
          <span>thickness = trail strength · ◆ pin</span>
        </div>
      )}

      {hovered && (
        <div className="walk-receipt">
          <strong>{hovered.label}</strong>
          <span className={`walk-degree-chip ${hovered.kinship}`}>{degreeLabel(hovered)}</span>
          {hovered.category && <span className="walk-cat">{hovered.category}</span>}
          <div className="walk-receipt-line">{receiptLine(hovered)}</div>
          <div className="walk-receipt-note">Association, not cause — you walk the trail; the app only measures each hop.</div>
        </div>
      )}
    </div>
  )
}
