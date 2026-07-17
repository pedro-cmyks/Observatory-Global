// The L3 wedge, made visual: a dossier is a CONNECTED investigation. This
// component measures how the pinned stories relate and renders it three ways —
// an investigative universe (scoped semantic field + relation edges), an Equal
// Earth map of the countries the stories touch, and distributions (coverage by
// country/language, press vs public, sentiment, combined timeline). All
// MEASURED at generation time; the frozen pin core never depends on it.
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import {
  fetchConnections, deriveClusters, layoutInvestigativeUniverse, edgeReason, deOverlapLabels,
  edgeStrength, clusterStrength, sharedBasisNames, coverageLensNote, buildFrozenCrossRefs,
  umbrellaChildDivergence, UMBRELLA_DIVERGENCE_MAX,
  type ConnectionsData, type ConnectionEdge, type ClusterResult,
  type ConnectionNeighbor, type LabelItem, type TextCrossRef,
} from '../lib/dossierConnections'
import { categoryColor, universeRadius } from '../lib/universeLayout'
import { createEqualEarth } from '../lib/equalEarthProjection'
// Item-1 fix round: assigned ISO codes (CH/CG/CF/KN…) are NEVER remapped —
// the old CH→CN entry painted China for a Switzerland row. Legacy-only table.
import { LEGACY_GDELT_TO_ISO } from '../lib/countryCodeBoundary'
import { track } from '../lib/telemetry'
import type { Investigation } from '../lib/workbench'
import './DossierConnections.css'

// Edge visual truth: green = distinctive shared actor; amber = evidence-text
// mention; blue dotted = same COVERAGE country (context only); slate dashed =
// semantic proximity. Country overlap is never subject identity or causality.
const STRONG_EDGE = '#1D9E75'
const TEXT_EDGE = '#f59e0b'   // evidence-text mention — verify, not confirmed
const CONTEXT_EDGE = '#38bdf8' // coverage geography — visible, explicitly non-confirming
const WEAK_EDGE = '#64748b'

const UNIVERSE_W = 640
// Taller (not wider) — width scales the whole viewBox to the container, so a
// wider box shrinks the text; extra HEIGHT gives labels room without shrinking.
const UNIVERSE_H = 460

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v))
// The always-visible "why" on a pin↔pin edge — the strongest measured basis, so
// a reader of the report alone sees WHY two stories connect, not just that they do.
function edgeTag(e: ConnectionEdge): string {
  // Strongest basis first — a distinctive shared actor must show its NAME, not a
  // cosine number that would make the confirmed link look fuzzy.
  if (e.shared_persons.length) return e.shared_persons[0].split(' ')[0]
  if (e.shared_countries.length) return e.shared_countries[0]
  if (e.text_mentions?.length) return `“${e.text_mentions[0]}”`
  if (e.basis.includes('semantic') && e.semantic_sim != null) return `≈${e.semantic_sim.toFixed(2)}`
  return ''
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

  // Frank v2: frozen-evidence cross-refs (the killer blocker — an isolation
  // claim contradicted by a headline the report itself shows) + the coverage
  // lens note. Both pure math over data already in hand.
  const crossRefs = buildFrozenCrossRefs(inv.pins, data)
  const lensNote = coverageLensNote(data.distributions?.languages ?? [])

  return (
    <div className="dcx">
      <p className="dossier-meta" data-tip="Semantic centroid proximity, coverage-country context, rarity-weighted shared actors, and evidence-text mentions — measured now, not frozen at pin time. A shared coverage country is not subject identity or causality.">
        measured at generation time · {data.nodes.length} stories · {data.edges.length} links
      </p>
      {/* W4 (dataviz audit): count-lineage reconciliation — the pin cards, the
          distributions and who-says-what each total differently; one line says
          why, mirroring the research plan's downranking-ledger discipline. */}
      {(() => {
        const memberTotal = data.nodes.reduce((s, n) => s + (n.n || 0), 0)
        const roleTotal = data.nodes.reduce(
          (s, n) => s + (n.roleCounts?.evidence || 0) + (n.roleCounts?.discussion || 0) + (n.roleCounts?.mood || 0), 0)
        return memberTotal > 0 ? (
          <p className="dossier-meta dcx-count-lineage" data-tip="Typed members = signals bound to the pinned topics in the measurement window (30d). Role-attributed = the subset carrying a press/public role. Pin-card counts were frozen at pin time under a different window, so they will not match these.">
            {memberTotal.toLocaleString()} typed member signals · {roleTotal.toLocaleString()} role-attributed · pin-card counts are frozen at pin time
          </p>
        ) : null
      })()}

      <ClusterVerdict data={data} cluster={cluster} crossRefs={crossRefs} />
      {lensNote && (
        <p className="dcx-lens" data-tip="Automatic note when one language dominates the pinned evidence — the report acknowledges its vantage. Share over language-known evidence signals.">
          {lensNote}
        </p>
      )}
      <AssembledStories data={data} />
      <InvestigativeUniverse data={data} cluster={cluster} />
      <DossierMap data={data} />
      <DossierDistributions data={data} />
    </div>
  )
}

// ── Sub-narrative verdict ─────────────────────────────────────────────────────
// The claim-truth half of the fix: a cluster held together only by semantic
// proximity or coverage-country overlap is NOT "one connected narrative".
// Confirmed = at least one distinctive shared-actor edge.
function ClusterVerdict({ data, cluster, crossRefs }: {
  data: ConnectionsData; cluster: ClusterResult; crossRefs?: TextCrossRef[]
}) {
  // Frank v2 blocker 1: the isolation warning — entity extraction found no
  // overlap, but a FROZEN headline the report displays mentions the other pin.
  const crossRefWarnings = (crossRefs ?? []).map((x, i) => (
    <p key={i} className="dcx-note dcx-crossref">
      ⚠ Verify before calling “{x.pinLabel}” unrelated: entity extraction found no overlap
      with “{x.otherLabel}”, but its frozen evidence text mentions <strong>“{x.term}”</strong>
      {' '}(“{x.headline}”).
    </p>
  ))

  if (cluster.clusters.length === 0) {
    return (
      <div className="dcx-verdict" data-state="neutral">
        <p>No sub-narrative connects these pins — every story is isolated by entity overlap. They may not form one narrative.</p>
        {crossRefWarnings}
        {data.unresolved.length > 0 && (
          <p className="dcx-note">Not in the relation graph (no story centroid): {data.unresolved.join(', ')}.</p>
        )}
      </div>
    )
  }

  const strengths = cluster.clusters.map(g => clusterStrength(g, data.edges))
  const single = cluster.clusters.length === 1
  // Whole-box state: single cluster → its strength; multiple → 'split' (per-cluster
  // pills carry the nuance, never roll conflicting clusters into one claim).
  const boxState = single ? (strengths[0] === 'confirmed' ? 'confirmed' : 'caution') : 'split'

  let headline: ReactNode
  if (single && strengths[0] === 'confirmed') {
    const via = sharedBasisNames(cluster.clusters[0], data.edges)
    headline = (
      <p>
        <b className="dcx-verdict-glyph" style={{ color: STRONG_EDGE }}>✓</b>{' '}
        These pins are connected by a distinctive shared actor, not just similar coverage.
        {via.length > 0 && <> Linked via <strong>{via.join(', ')}</strong>.</>}
      </p>
    )
  } else if (single && strengths[0] === 'text') {
    headline = (
      <>
        <p>
          <b className="dcx-verdict-glyph" style={{ color: TEXT_EDGE }}>✎</b>{' '}
          These pins share no extracted actors or places, but one story's <strong>evidence text
          mentions the other</strong> — the headline states a link the entity lens missed.
        </p>
        <p className="dcx-note">
          Text-linked is weaker than a confirmed shared actor and stronger than semantic proximity —
          verify the mention before treating these as one narrative.
        </p>
      </>
    )
  } else if (single && strengths[0] === 'context') {
    headline = (
      <>
        <p>
          <b className="dcx-verdict-glyph" style={{ color: CONTEXT_EDGE }}>◇</b>{' '}
          These pins touch the same <strong>coverage geography</strong>, but Atlas has not
          verified that the country is the subject linking both stories.
        </p>
        <p className="dcx-note">
          Treat this as navigation context — not story identity, coordination, or causality.
        </p>
      </>
    )
  } else if (single) {
    headline = (
      <>
        <p>
          <b className="dcx-verdict-glyph" style={{ color: '#f59e0b' }}>⚠</b>{' '}
          These pins are only <strong>similar in topic</strong> — no shared actors or places connect them.
        </p>
        <p className="dcx-note">
          All links are semantic proximity only. This may reflect shared language or subject matter,
          not a real coordinated narrative — treat it as a hypothesis to investigate, not a finding.
        </p>
      </>
    )
  } else {
    headline = (
      <p>
        These pins split into {cluster.clusters.length} sub-narratives.
        {cluster.isolated.length > 0
          && ` ${cluster.isolated.length} pin${cluster.isolated.length === 1 ? '' : 's'} connect to nothing (flagged).`}
      </p>
    )
  }

  return (
    <div className="dcx-verdict" data-state={boxState}>
      {headline}
      <ul className="dcx-clusters">
        {cluster.clusters.map((g, i) => {
          const s = strengths[i]
          const badgeCls = s === 'confirmed' ? 'dcx-cluster-badge--confirmed'
            : s === 'text' ? 'dcx-cluster-badge--text' : 'dcx-cluster-badge--caution'
          return (
            <li key={i}>
              <span className={`dcx-cluster-badge ${badgeCls}`}>
                {s === 'confirmed' ? 'CONFIRMED'
                  : s === 'text' ? 'TEXT-LINKED'
                    : s === 'context' ? 'COVERAGE CONTEXT' : 'SIMILAR ONLY'}
              </span>
              <span className="dcx-cluster-dot" style={{ background: clusterColor(i) }} />
              <span><strong>Sub-narrative {i + 1}</strong> ({g.length}): {g.map(n => n.label).join('; ')}</span>
            </li>
          )
        })}
        {cluster.isolated.length > 0 && (
          <li className="dcx-isolated-row">
            <span className="dcx-cluster-dot dcx-iso-dot" />
            <strong>Isolated</strong> (by entity overlap): {cluster.isolated.map(n => n.label).join('; ')}
          </li>
        )}
      </ul>
      {crossRefWarnings}
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
  // Frank v2 blocker 5: only claim "fragments of ONE event" when the child
  // labels actually share the parent's key tokens. A diverging fold (Khamenei
  // Funeral under Trump-Putin Talks) renders as engine-grouped RELATED topics.
  const coherent = (u: (typeof umbrellas)[number]) =>
    (umbrellaChildDivergence(u) ?? 0) <= UMBRELLA_DIVERGENCE_MAX
  const allCoherent = umbrellas.every(coherent)
  return (
    <div className="dcx-panel dcx-assembled">
      <div className="dcx-panel-title">Assembled stories</div>
      <p className="dcx-panel-sub">
        {allCoherent
          ? <>Near-duplicate fragments of one event, folded into a single story by facet — the
              constellation, not the {umbrellas.reduce((s, u) => s + (u.child_count ?? 0), 0)} raw rows.</>
          : <>Topics the engine grouped under a parent story. Where child labels diverge from the
              parent, the group is <strong>related topics, NOT one event</strong> — flagged per story.</>}
      </p>
      {umbrellas.map(u => (
        <div key={u.base_id} className="dcx-umbrella">
          <div className="dcx-umbrella-head">
            <strong>{u.label}</strong>
            <span className="dcx-umbrella-meta">
              {coherent(u)
                ? <>{u.child_count ?? 0} fragments · {u.facets!.length} facets</>
                : <>{u.child_count ?? 0} engine-grouped topics · {u.facets!.length} facets</>}
            </span>
          </div>
          {!coherent(u) && (
            <p className="dcx-note dcx-umbrella-warn">
              ⚠ Child stories diverge from this label ({Math.round((umbrellaChildDivergence(u) ?? 0) * 100)}%
              share no key token with it) — related topics grouped by the engine, NOT near-duplicate
              fragments of one event.
            </p>
          )}
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
// Approx monospace glyph widths for the two on-canvas label sizes (fontPx*0.6).
const PIN_CHAR_W = 5.4      // 9px labels
const NB_CHAR_W = 4.2       // 7px labels
const truncate = (s: string, max: number) => (s.length > max ? s.slice(0, max - 1) + '…' : s)

interface PlacedNeighbor {
  base_id: string
  label: string
  category: string | null
  px: number
  py: number
  bridge: boolean
  links: Array<{ pin: string; sim: number }>
}

// Exported: the workbench mini-constellation reuses this field at compact
// height so the analyst sees the universe build as they pin (report untouched).
export function InvestigativeUniverse({ data, cluster, compact = false }: {
  data: ConnectionsData; cluster: ClusterResult; compact?: boolean
}) {
  // hover = a pin id OR `nb:<base_id>` for a neighbor star.
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
  // Per-cluster strength → a similarity-only cluster gets an amber dashed ring on
  // its nodes (same "dashed = provisional" grammar as the isolated ring).
  const clusterStrengths = useMemo(
    () => cluster.clusters.map(g => clusterStrength(g, data.edges)),
    [cluster, data.edges],
  )

  // Group unpinned neighbors: BRIDGES (near >1 pin — the meaningful cross-pin
  // connectors) vs SINGLE (near one pin — the crowd). Bridges are always
  // labelled; singles fan out as dots and only reveal a label on hover.
  const nbGroups = useMemo(() => {
    const bridges: ConnectionNeighbor[] = []
    const byPin = new Map<string, ConnectionNeighbor[]>()
    for (const nb of (data.neighbors ?? [])) {
      const links = nb.links.filter(l => byId.has(l.pin))
      if (links.length === 0) continue
      if (links.length > 1) bridges.push(nb)
      else byPin.set(links[0].pin, [...(byPin.get(links[0].pin) ?? []), nb])
    }
    return { bridges, byPin }
  }, [data, byId])

  // Position neighbors: bridges at the barycenter of their pins; single-pin
  // neighbors fanned evenly across an arc that points AWAY from the field center
  // (so they splay outward instead of piling on the pin).
  const neighborPlaced = useMemo<PlacedNeighbor[]>(() => {
    const cx = UNIVERSE_W / 2, cy = UNIVERSE_H / 2
    const out: PlacedNeighbor[] = []
    const mk = (nb: ConnectionNeighbor, px: number, py: number, bridge: boolean): PlacedNeighbor => ({
      base_id: nb.base_id, label: nb.label, category: nb.category, links: nb.links, bridge,
      px: clamp(px, 16, UNIVERSE_W - 16), py: clamp(py, 20, UNIVERSE_H - 14),
    })
    for (const nb of nbGroups.bridges) {
      const pts = nb.links.map(l => byId.get(l.pin)).filter(Boolean) as Array<{ px: number; py: number }>
      const mx = pts.reduce((s, p) => s + p.px, 0) / pts.length
      const my = pts.reduce((s, p) => s + p.py, 0) / pts.length
      out.push(mk(nb, mx, my, true))
    }
    for (const [pin, list] of nbGroups.byPin) {
      const p = byId.get(pin)!
      const base = Math.atan2(p.py - cy, p.px - cx) // outward direction from center
      const R = 48 + Math.min(list.length, 8) * 4
      const span = Math.min(Math.PI * 1.3, Math.max(0.001, list.length - 1) * 0.42)
      list.forEach((nb, i) => {
        const frac = list.length === 1 ? 0 : i / (list.length - 1) - 0.5
        const ang = base + frac * span
        out.push(mk(nb, p.px + Math.cos(ang) * R, p.py + Math.sin(ang) * R, false))
      })
    }
    return out
  }, [nbGroups, byId])

  // De-overlap the ALWAYS-ON labels (pins + bridges) into vertical lanes.
  const labelY = useMemo(() => {
    const items: LabelItem[] = []
    for (const n of placed) {
      const t = truncate(n.label, 26)
      items.push({ id: n.id, cx: n.px, halfW: (t.length * PIN_CHAR_W) / 2, y: n.py - universeRadius(n.n) - 5 })
    }
    for (const nb of neighborPlaced) {
      if (!nb.bridge) continue
      const t = truncate(nb.label, 22)
      items.push({ id: `nb:${nb.base_id}`, cx: nb.px, halfW: (t.length * NB_CHAR_W) / 2, y: nb.py - 6 })
    }
    return deOverlapLabels(items, 11)
  }, [placed, neighborPlaced])

  const hovered = hover && !hover.startsWith('nb:') ? byId.get(hover) : null
  const hoverEdges = hovered ? data.edges.filter(e => e.a === hovered.id || e.b === hovered.id) : []
  // A single neighbor's label shows when the neighbor itself is hovered, or when
  // the pin it sits near is hovered (reveal a pin's whole crowd at once).
  const nbLabelShown = (nb: PlacedNeighbor): boolean =>
    hover === `nb:${nb.base_id}` || (!!hover && !hover.startsWith('nb:') && nb.links.some(l => l.pin === hover))

  const shortPin = (id: string) => truncate(byId.get(id)?.label ?? id, 18)

  return (
    <div className={compact ? 'dcx-universe-compact' : 'dcx-panel'}>
      {!compact && (
        <>
          <div className="dcx-panel-title">Investigative universe</div>
          <p className="dcx-sub">How the pinned stories relate — and the unpinned stories sitting near them. Hover any node to trace its links.</p>
          <div className="dcx-howto">
            <span><b className="dcx-k-pin">●</b> your pins (always labelled)</span>
            <span><b className="dcx-k-nb">◦</b> nearby unpinned story</span>
            <span><b className="dcx-k-bridge">◎</b> bridge — near several pins</span>
            <span>position ≈ semantic field · closer = more alike</span>
          </div>
          <div className="dcx-howto dcx-edge-legend">
            <span><i className="dcx-k-strong-edge" /> solid green = confirmed distinctive actor</span>
            <span><i className="dcx-k-text-edge" /> solid amber = evidence-text mention (verify)</span>
            <span style={{ color: CONTEXT_EDGE }}>◇ blue dotted = coverage-country context</span>
            <span><i className="dcx-k-weak-edge" /> dashed = similarity only, not a confirmed link</span>
            <span>line label = the reason (shared actor, coverage country, “mention”, or ≈cosine)</span>
          </div>
        </>
      )}
      <svg viewBox={`0 0 ${UNIVERSE_W} ${UNIVERSE_H}`} className={`dcx-universe${compact ? ' dcx-universe--compact' : ''}`} role="img" aria-label="Investigative universe">
        {/* neighbor links — faint, behind everything */}
        {neighborPlaced.map(nb => nb.links.map((l, j) => {
          const p = byId.get(l.pin)
          if (!p) return null
          const lit = nbLabelShown(nb)
          return <line key={`${nb.base_id}-${j}`} x1={p.px} y1={p.py} x2={nb.px} y2={nb.py}
            stroke={lit ? '#94a3b8' : '#475569'} strokeWidth={lit ? 0.8 : 0.5} strokeDasharray="2 3"
            strokeOpacity={hover ? (lit ? 0.55 : 0.1) : 0.28} />
        }))}
        {/* Edges encode truth tier; only distinctive actors receive confirmation
            weight. Coverage-country and semantic links never scale into proof. */}
        {data.edges.map((e, i) => {
          const a = byId.get(e.a), b = byId.get(e.b)
          if (!a || !b) return null
          const dim = hover && e.a !== hover && e.b !== hover
          const tier = edgeStrength(e)
          const strong = tier === 'strong'
          const color = strong ? STRONG_EDGE
            : tier === 'text' ? TEXT_EDGE : tier === 'context' ? CONTEXT_EDGE : WEAK_EDGE
          const width = strong ? 1.4 + e.weight * 1.8 : tier === 'text' ? 1.0 : 0.75
          const opacity = dim ? (strong ? 0.10 : 0.06)
            : (strong ? 0.55 + e.weight * 0.35 : tier === 'text' ? 0.45 : tier === 'context' ? 0.42 : 0.30)
          const tag = edgeTag(e)
          return (
            <g key={i}>
              <line x1={a.px} y1={a.py} x2={b.px} y2={b.py} stroke={color}
                strokeWidth={width} strokeOpacity={opacity}
                strokeDasharray={tier === 'context' ? '1 3' : tier === 'weak' ? '3 3' : undefined} />
              {!dim && tag && (
                <text x={(a.px + b.px) / 2} y={(a.py + b.py) / 2 - 2} textAnchor="middle"
                  className="dcx-edge-tag" fill={color}>{tag}</text>
              )}
            </g>
          )
        })}
        {/* neighbor stars — dots always; single labels on hover, bridges labelled */}
        {neighborPlaced.map(nb => {
          const showLabel = nb.bridge || nbLabelShown(nb)
          // bridges use the de-overlapped lane; single (hover) labels sit just above.
          const rel = nb.bridge ? (labelY.get(`nb:${nb.base_id}`) ?? (nb.py - 6)) - nb.py : -6
          const dim = hover ? !nbLabelShown(nb) && hover !== `nb:${nb.base_id}` : false
          return (
            <g key={nb.base_id} transform={`translate(${nb.px},${nb.py})`}
               onMouseEnter={() => setHover(`nb:${nb.base_id}`)} onMouseLeave={() => setHover(null)}
               style={{ cursor: 'pointer' }} opacity={dim ? 0.35 : 1}>
              {showLabel && nb.bridge && rel < -8 && (
                <line x1={0} y1={-4} x2={0} y2={rel + 2} stroke="#475569" strokeWidth={0.4} />
              )}
              {/* family palette returns a var() expression — SVG attrs don't substitute var(), so style */}
              <circle r={nb.bridge ? 3.5 : 3} style={{ fill: nb.category ? categoryColor(nb.category) : '#64748b' }}
                fillOpacity={nb.bridge ? 0.6 : 0.5}
                stroke={nb.bridge ? '#e2e8f0' : '#475569'} strokeWidth={nb.bridge ? 1.2 : 0.5} />
              {showLabel && (
                <text y={rel} textAnchor="middle"
                  className={`dcx-neighbor-label${nb.bridge ? ' bridge' : ''}`}>
                  {truncate(nb.label, 22)}
                </text>
              )}
            </g>
          )
        })}
        {/* nodes (pins) */}
        {placed.map(n => {
          const isolated = cluster.isolated.some(x => x.id === n.id)
          const ci = cluster.clusterOf.get(n.id) ?? -1
          const weakCluster = ci >= 0 && clusterStrengths[ci] === 'caution'
          const r = universeRadius(n.n)
          const active = hover === n.id
          const nearHover = hover && !hover.startsWith('nb:') && (n.id === hover || neighborsOf.get(hover)?.has(n.id))
          const dim = hover && !hover.startsWith('nb:') && !nearHover
          const ly = labelY.get(n.id) ?? (n.py - r - 5)
          const rel = ly - n.py // absolute → relative to node translate
          return (
            <g key={n.id}
               transform={`translate(${n.px},${n.py})`}
               onMouseEnter={() => setHover(n.id)} onMouseLeave={() => setHover(null)}
               style={{ cursor: 'pointer', opacity: dim ? 0.3 : 1 }}>
              {isolated && (
                <circle r={r + 4} fill="none" stroke="#64748b" strokeWidth={1}
                        strokeDasharray="3 3" />
              )}
              {weakCluster && !isolated && (
                <circle r={r + 4} fill="none" stroke="#f59e0b" strokeWidth={1.5}
                        strokeDasharray="4 2" strokeOpacity={0.7} />
              )}
              {/* leader line when the label got pushed up out of the way */}
              {rel < -r - 8 && (
                <line x1={0} y1={-r - 2} x2={0} y2={rel + 2} stroke={clusterColor(ci)} strokeWidth={0.5} strokeOpacity={0.5} />
              )}
              <circle r={r} style={{ fill: n.category ? categoryColor(n.category) : '#7dd3fc' }}
                      stroke={isolated ? '#64748b' : clusterColor(ci)}
                      strokeWidth={active ? 2.5 : 1.5} />
              <text y={rel} textAnchor="middle" className="dcx-node-label">
                {truncate(n.label, 26)}
              </text>
            </g>
          )
        })}
      </svg>
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
      {/* Static "nearby" list — the report-only reader gets the names without hover */}
      {!compact && (nbGroups.bridges.length > 0 || nbGroups.byPin.size > 0) && (
        <div className="dcx-nearby">
          <div className="dcx-nearby-title">Nearby unpinned stories</div>
          {nbGroups.bridges.length > 0 && (
            <div className="dcx-nearby-row">
              <span className="dcx-nearby-tag bridge">bridges</span>
              <span className="dcx-nearby-list">
                {nbGroups.bridges.map(nb => (
                  <span key={nb.base_id} className="dcx-nearby-item">
                    {nb.label}
                    <em> ({nb.links.map(l => shortPin(l.pin)).join(' + ')})</em>
                  </span>
                ))}
              </span>
            </div>
          )}
          {[...nbGroups.byPin.entries()].map(([pin, list]) => (
            <div key={pin} className="dcx-nearby-row">
              <span className="dcx-nearby-tag">near {shortPin(pin)}</span>
              <span className="dcx-nearby-list">
                {list.map(nb => <span key={nb.base_id} className="dcx-nearby-item">{nb.label}</span>)}
              </span>
            </div>
          ))}
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
      const iso = LEGACY_GDELT_TO_ISO[c.cc] ?? c.cc
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
          // W2 (dataviz audit): floor 0.35 compressed the volume range on a dark
          // surface (RU 33 vs MD 4 read nearly alike) — widen to 0.2..0.95.
          const t = n > 0 ? 0.2 + 0.75 * (n / maxN) : 0
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
  // Tone arrives on the raw GDELT scale (nominally −10…+10; extremes can
  // exceed it) — the SAME user-facing unit as ThemeDetail (B3: one tone scale
  // everywhere). Bars draw RELATIVE to the most-charged story so the pins
  // differentiate; the caption below states both the relative scaling and the
  // absolute unit.
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
              <div key={s.id} className="dcx-sent-row" data-tip={`avg GDELT tone ${s.sentiment.toFixed(2)} (−10 critical … +10 supportive; scores rarely exceed ±3)`}>
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
          {/* W3/B3 (dataviz audit): the bars are per-report relative — without
              this caption the same bar length means −2.5 in one dossier and −9
              in another. Tone unit = raw GDELT ±10, same as ThemeDetail. */}
          {d.sentimentByNode.length > 0 && (
            <div className="dcx-note" data-tip="Bar length is relative to this report's most-charged pin so the pins differentiate; the number is the absolute GDELT tone (−10…+10).">
              bars scaled to the most-charged pin ({(d.sentimentByNode.find(s => Math.abs(s.sentiment) === sentMax)?.sentiment ?? sentMax).toFixed(2)} tone) · GDELT scale −10…+10
            </div>
          )}
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
