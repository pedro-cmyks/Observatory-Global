// The L3 wedge, made visual: a dossier is a CONNECTED investigation. This
// component measures how the pinned stories relate and renders it three ways —
// an investigative universe (scoped semantic field + relation edges), an Equal
// Earth map of the countries the stories touch, and distributions (coverage by
// country/language, press vs public, sentiment, combined timeline). All
// MEASURED at generation time; the frozen pin core never depends on it.
import { useEffect, useMemo, useRef, useState } from 'react'
import {
  fetchConnections, deriveClusters, layoutInvestigativeUniverse, edgeReason,
  type ConnectionsData, type ConnectionEdge, type ClusterResult,
} from '../lib/dossierConnections'
import { categoryColor, universeRadius } from '../lib/universeLayout'
import { createEqualEarth } from '../lib/equalEarthProjection'
import { track } from '../lib/telemetry'
import type { Investigation } from '../lib/workbench'
import './DossierConnections.css'

const BASIS_COLOR: Record<string, string> = {
  semantic: '#38bdf8',        // cyan — semantic proximity
  shared_country: '#f59e0b',  // amber — shared country
  shared_person: '#a78bfa',   // violet — shared actor
}

const UNIVERSE_W = 640
const UNIVERSE_H = 380

// GDELT/FIPS → ISO_A2 (Natural Earth), to match the geojson used by the map.
const GDELT_TO_ISO: Record<string, string> = {
  CH: 'CN', RI: 'ID', RB: 'RS', KV: 'XK', CG: 'CD', CF: 'CG',
  KS: 'KR', KN: 'KP', GZ: 'PS',
}

export function DossierConnections(
  { inv, onData }: {
    inv: Investigation
    /** Hands the measured data + clusters up so the parent can fold a
     *  connection summary into the Markdown export. */
    onData?: (data: ConnectionsData, cluster: ClusterResult) => void
  },
) {
  const [data, setData] = useState<ConnectionsData | null | undefined>(undefined)

  useEffect(() => {
    let alive = true
    fetchConnections(inv).then(d => { if (alive) setData(d) }).catch(() => { if (alive) setData(null) })
    return () => { alive = false }
  }, [inv])

  const cluster = useMemo<ClusterResult | null>(
    () => (data ? deriveClusters(data.nodes, data.edges) : null),
    [data],
  )

  const onDataRef = useRef(onData)
  onDataRef.current = onData
  useEffect(() => {
    if (data && cluster) {
      track('dossier_connections_measured', {
        nodes: data.nodes.length, edges: data.edges.length,
        clusters: cluster.clusters.length, isolated: cluster.isolated.length,
      })
      onDataRef.current?.(data, cluster)
    }
  }, [data, cluster])

  if (data === undefined) {
    return <div className="dcx-loading">Measuring connections across pins…</div>
  }
  if (!data || data.nodes.length < 2 || !cluster) {
    return (
      <div className="dcx-empty">
        Pin at least two story/thread anchors to measure how they connect.
      </div>
    )
  }

  return (
    <div className="dcx">
      <p className="dossier-meta" data-tip="Semantic centroid proximity, shared country, and rarity-weighted shared actors — measured now, not frozen at pin time.">
        measured at generation time · {data.nodes.length} stories · {data.edges.length} links
      </p>

      <ClusterVerdict data={data} cluster={cluster} />
      <AssembledStories data={data} />
      <InvestigativeUniverse data={data} cluster={cluster} />
      <DossierMap data={data} />
      <DossierDistributions data={data} />
    </div>
  )
}

// ── Sub-narrative verdict ─────────────────────────────────────────────────────
function ClusterVerdict({ data, cluster }: { data: ConnectionsData; cluster: ClusterResult }) {
  return (
    <div className="dcx-verdict">
      {cluster.clusters.length === 0 ? (
        <p>No sub-narrative connects these pins — every story is isolated. They may not form one narrative.</p>
      ) : (
        <>
          <p>
            {cluster.clusters.length === 1
              ? 'These pins form one connected narrative.'
              : `These pins split into ${cluster.clusters.length} sub-narratives.`}
            {cluster.isolated.length > 0
              && ` ${cluster.isolated.length} pin${cluster.isolated.length === 1 ? '' : 's'} connect to nothing (flagged).`}
          </p>
          <ul className="dcx-clusters">
            {cluster.clusters.map((g, i) => (
              <li key={i}>
                <span className="dcx-cluster-dot" style={{ background: clusterColor(i) }} />
                <strong>Sub-narrative {i + 1}</strong> ({g.length}): {g.map(n => n.label).join('; ')}
              </li>
            ))}
            {cluster.isolated.length > 0 && (
              <li className="dcx-isolated-row">
                <span className="dcx-cluster-dot dcx-iso-dot" />
                <strong>Isolated</strong>: {cluster.isolated.map(n => n.label).join('; ')}
              </li>
            )}
          </ul>
        </>
      )}
      {data.unresolved.length > 0 && (
        <p className="dcx-note">Not in the relation graph (no story centroid): {data.unresolved.join(', ')}.</p>
      )}
    </div>
  )
}

// ── Assembled stories (constellation by facet) ───────────────────────────────
// An umbrella node folds ~N near-duplicate fragments of ONE big event into a
// single story with typed sub-facets. Lists each assembled story by facet so
// the analyst navigates "Venezuela Earthquakes → death-toll / aid / foreign-
// victims / rescues / aftermath" instead of ~30 duplicate rows.
const FACET_LABEL: Record<string, string> = {
  'death-toll': 'Death toll',
  'foreign-victims': 'Foreign victims',
  'international-aid': 'International aid',
  'government-response': 'Government response',
  rescues: 'Rescues',
  aftermath: 'Aftermath',
  core: 'Main thread',
}
const facetLabel = (f: string): string => FACET_LABEL[f] || f.replace(/-/g, ' ')

function AssembledStories({ data }: { data: ConnectionsData }) {
  const umbrellas = data.nodes.filter(n => n.is_umbrella && (n.facets?.length ?? 0) > 0)
  if (umbrellas.length === 0) return null
  return (
    <div className="dcx-panel dcx-assembled">
      <div className="dcx-panel-title">Assembled stories</div>
      <p className="dcx-panel-sub">
        Near-duplicate fragments of one event, folded into a single story by facet — the
        constellation, not the {umbrellas.reduce((s, u) => s + (u.child_count ?? 0), 0)} raw rows.
      </p>
      {umbrellas.map(u => (
        <div key={u.base_id} className="dcx-umbrella">
          <div className="dcx-umbrella-head">
            <strong>{u.label}</strong>
            <span className="dcx-umbrella-meta">
              {u.child_count ?? 0} fragments · {u.facets!.length} facets
            </span>
          </div>
          <div className="dcx-facets">
            {u.facets!.map(f => (
              <div key={f.facet} className="dcx-facet">
                <div className="dcx-facet-head">
                  <span className="dcx-facet-name">{facetLabel(f.facet)}</span>
                  <span className="dcx-facet-count">
                    {f.topic_count} {f.topic_count === 1 ? 'story' : 'stories'}
                    {f.evidence_n > 0 ? ` · ${f.evidence_n} signals` : ''}
                    {f.countries.length > 0 ? ` · ${f.countries.slice(0, 3).map(c => c.cc).join(' ')}` : ''}
                  </span>
                </div>
                {f.topics.length > 0 && (
                  <div className="dcx-facet-topics">{f.topics.slice(0, 5).map(t => t.label).join(' · ')}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function clusterColor(i: number): string {
  const hues = [190, 40, 280, 140, 0, 320, 90]
  return `hsl(${hues[i % hues.length]}, 70%, 58%)`
}

// ── Investigative universe (scoped semantic field) ────────────────────────────
function InvestigativeUniverse({ data, cluster }: { data: ConnectionsData; cluster: ClusterResult }) {
  const [hover, setHover] = useState<string | null>(null)
  const placed = useMemo(
    () => layoutInvestigativeUniverse(data.nodes, data.edges, UNIVERSE_W, UNIVERSE_H),
    [data],
  )
  const byId = useMemo(() => new Map(placed.map(n => [n.id, n])), [placed])
  const neighborsOf = useMemo(() => {
    const m = new Map<string, Set<string>>()
    for (const e of data.edges) {
      m.set(e.a, (m.get(e.a) ?? new Set()).add(e.b))
      m.set(e.b, (m.get(e.b) ?? new Set()).add(e.a))
    }
    return m
  }, [data])

  const hovered = hover ? byId.get(hover) : null
  const hoverEdges = hover
    ? data.edges.filter(e => e.a === hover || e.b === hover)
    : []

  return (
    <div className="dcx-panel">
      <div className="dcx-panel-title">Investigative universe</div>
      <p className="dcx-sub">Each body a pinned story · edges = measured relations · dashed ring = isolated · position ≈ semantic field</p>
      <svg viewBox={`0 0 ${UNIVERSE_W} ${UNIVERSE_H}`} className="dcx-universe" role="img" aria-label="Investigative universe">
        {/* edges */}
        {data.edges.map((e, i) => {
          const a = byId.get(e.a), b = byId.get(e.b)
          if (!a || !b) return null
          const dim = hover && e.a !== hover && e.b !== hover
          const color = BASIS_COLOR[e.basis[0]] ?? '#94a3b8'
          return (
            <line
              key={i} x1={a.px} y1={a.py} x2={b.px} y2={b.py}
              stroke={color}
              strokeWidth={0.6 + e.weight * 2.2}
              strokeOpacity={dim ? 0.06 : 0.18 + e.weight * 0.5}
            />
          )
        })}
        {/* nodes */}
        {placed.map(n => {
          const isolated = cluster.isolated.some(x => x.id === n.id)
          const ci = cluster.clusterOf.get(n.id) ?? -1
          const r = universeRadius(n.n)
          const active = hover === n.id
          const nearHover = hover && (n.id === hover || neighborsOf.get(hover)?.has(n.id))
          const dim = hover && !nearHover
          return (
            <g key={n.id}
               transform={`translate(${n.px},${n.py})`}
               onMouseEnter={() => setHover(n.id)} onMouseLeave={() => setHover(null)}
               style={{ cursor: 'pointer', opacity: dim ? 0.3 : 1 }}>
              {isolated && (
                <circle r={r + 4} fill="none" stroke="#64748b" strokeWidth={1}
                        strokeDasharray="3 3" />
              )}
              <circle r={r} fill={n.category ? categoryColor(n.category) : '#7dd3fc'}
                      stroke={isolated ? '#64748b' : clusterColor(ci)}
                      strokeWidth={active ? 2.5 : 1.5} />
              <text y={-r - 4} textAnchor="middle" className="dcx-node-label">
                {n.label.length > 26 ? n.label.slice(0, 25) + '…' : n.label}
              </text>
            </g>
          )
        })}
      </svg>
      <div className="dcx-legend">
        <span><i style={{ background: BASIS_COLOR.semantic }} /> semantic</span>
        <span><i style={{ background: BASIS_COLOR.shared_country }} /> shared country</span>
        <span><i style={{ background: BASIS_COLOR.shared_person }} /> shared actor</span>
      </div>
      {hovered && (
        <div className="dcx-hovercard">
          <strong>{hovered.label}</strong>
          {hovered.category && <span className="dcx-chip">{hovered.category}</span>}
          <div className="dcx-hover-rel">
            {hoverEdges.length === 0
              ? 'isolated — no measured connection to other pins'
              : hoverEdges.map((e: ConnectionEdge, i) => {
                  const otherId = e.a === hovered.id ? e.b : e.a
                  const other = byId.get(otherId)
                  return <div key={i}>↔ {other?.label ?? otherId} — {edgeReason(e)}</div>
                })}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Equal Earth map of touched countries ──────────────────────────────────────
interface Feat { properties: Record<string, unknown>; geometry: unknown }

function DossierMap({ data }: { data: ConnectionsData }) {
  const [features, setFeatures] = useState<Feat[] | null>(null)
  const failed = useRef(false)

  useEffect(() => {
    let alive = true
    fetch('/data/countries.geojson')
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(fc => { if (alive) setFeatures((fc.features ?? []) as Feat[]) })
      .catch(() => { failed.current = true; if (alive) setFeatures([]) })
    return () => { alive = false }
  }, [])

  const W = 640, H = 300
  const ee = useMemo(() => createEqualEarth(W, H), [])
  const touched = useMemo(() => {
    const m = new Map<string, number>()
    for (const c of data.distributions?.countries ?? []) {
      const iso = GDELT_TO_ISO[c.cc] ?? c.cc
      m.set(iso, c.n)
    }
    return m
  }, [data])
  const maxN = Math.max(1, ...[...touched.values()])

  if (!features) return <div className="dcx-panel"><div className="dcx-panel-title">Where these stories land</div><div className="dcx-loading">Loading map…</div></div>
  if (features.length === 0) return null // no geojson — degrade silently

  return (
    <div className="dcx-panel">
      <div className="dcx-panel-title">Where these stories land</div>
      <p className="dcx-sub">Countries the pinned coverage touches, shaded by volume</p>
      <svg viewBox={`0 0 ${W} ${H}`} className="dcx-map" role="img" aria-label="Countries touched by the investigation">
        <rect x={0} y={0} width={W} height={H} fill="#0f1620" />
        {features.map((f, i) => {
          const iso = String(f.properties.ISO_A2 ?? f.properties.ISO_A2_EH ?? '')
          const d = ee.pathString(f)
          if (!d) return null
          const n = touched.get(iso) ?? 0
          const t = n > 0 ? 0.35 + 0.6 * (n / maxN) : 0
          const fill = n > 0 ? `rgba(56,189,248,${t.toFixed(2)})` : '#243244'
          return <path key={i} d={d} fill={fill} stroke="#0f1620" strokeWidth={0.4} />
        })}
      </svg>
      <div className="dcx-map-legend">
        {(data.distributions?.countries ?? []).slice(0, 8).map(c => (
          <span key={c.cc} className="dcx-chip">{c.cc} {c.n}</span>
        ))}
      </div>
    </div>
  )
}

// ── Distributions ─────────────────────────────────────────────────────────────
function DossierDistributions({ data }: { data: ConnectionsData }) {
  const d = data.distributions
  if (!d) return null
  const roleTotal = Math.max(1, d.roles.press + d.roles.public)
  const langMax = Math.max(1, ...d.languages.map(l => l.n))
  const tlMax = Math.max(1, ...d.timeline.map(t => t.n))
  // Tone arrives on the raw signal scale (nlp/GDELT, ~±20). Show the diverging
  // bar RELATIVE to the most-charged story so the pins differentiate.
  const sentMax = Math.max(0.001, ...d.sentimentByNode.map(s => Math.abs(s.sentiment)))

  return (
    <div className="dcx-panel">
      <div className="dcx-panel-title">Distributions</div>

      <div className="dcx-dist-grid">
        <div className="dcx-dist">
          <div className="dcx-dist-title">Press vs public</div>
          <div className="dcx-role-bar" data-tip="press = verified evidence signals · public = forum/social discussion+mood, never verified">
            <div className="dcx-role-press" style={{ width: `${(d.roles.press / roleTotal) * 100}%` }} />
            <div className="dcx-role-public" style={{ width: `${(d.roles.public / roleTotal) * 100}%` }} />
          </div>
          <div className="dcx-role-legend">
            <span><i className="dcx-sw-press" /> press {d.roles.press}</span>
            <span><i className="dcx-sw-public" /> public {d.roles.public}</span>
          </div>
        </div>

        <div className="dcx-dist">
          <div className="dcx-dist-title">Coverage languages</div>
          {d.languages.length === 0 ? <div className="dcx-note">no language data</div> : d.languages.slice(0, 6).map(l => (
            <div key={l.lang} className="dcx-hbar-row">
              <span className="dcx-hbar-label">{l.lang}</span>
              <span className="dcx-hbar-track"><span className="dcx-hbar-fill" style={{ width: `${(l.n / langMax) * 100}%` }} /></span>
              <span className="dcx-hbar-n">{l.n}</span>
            </div>
          ))}
        </div>

        <div className="dcx-dist">
          <div className="dcx-dist-title">Sentiment by story</div>
          {d.sentimentByNode.length === 0 ? <div className="dcx-note">no sentiment data</div> : d.sentimentByNode.map(s => {
            const rel = s.sentiment / sentMax // [-1,1] relative to the most-charged story
            const w = Math.min(50, Math.abs(rel) * 50)
            return (
              <div key={s.id} className="dcx-sent-row" data-tip={`avg tone ${s.sentiment.toFixed(2)}`}>
                <span className="dcx-sent-label">{s.label.length > 22 ? s.label.slice(0, 21) + '…' : s.label}</span>
                <span className="dcx-sent-track">
                  <span className="dcx-sent-mid" />
                  <span
                    className={`dcx-sent-fill ${s.sentiment >= 0 ? 'pos' : 'neg'}`}
                    style={{ left: s.sentiment >= 0 ? '50%' : `${50 - w}%`, width: `${w}%` }}
                  />
                </span>
              </div>
            )
          })}
        </div>

        <div className="dcx-dist dcx-dist-wide">
          <div className="dcx-dist-title">Coverage timeline (combined)</div>
          {d.timeline.length === 0 ? <div className="dcx-note">no timeline data</div> : (
            <div className="dcx-timeline">
              {d.timeline.map(t => (
                <span key={t.day} className="dcx-tl-bar" data-tip={`${t.day}: ${t.n}`}
                      style={{ height: `${Math.max(4, (t.n / tlMax) * 100)}%` }} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
