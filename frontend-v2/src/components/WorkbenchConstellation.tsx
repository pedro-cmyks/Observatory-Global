// Incremental constellation seed (workbench): re-measures the connection graph
// as the pin set changes and renders the compact investigative universe LIVE —
// the analyst sees countries light up and edges appear while pinning, without
// generating the report. Cheap by construction: refetches only when the set of
// resolvable topic pins changes (POST /dossier/connections is server-cached
// 120s); anything short of 2 thread pins degrades to absence.
import { useEffect, useMemo, useRef, useState } from 'react'
import {
  connectionTopicIds, deriveClusters, fetchConnections,
  type ConnectionsData,
} from '../lib/dossierConnections'
import { InvestigativeUniverse } from './DossierConnections'
import WalkConstellation from './WalkConstellation'
import { addPin, type Investigation } from '../lib/workbench'
import type { WalkKin } from '../lib/constellationWalk'
import './WorkbenchConstellation.css'

export default function WorkbenchConstellation({ inv, onOpenThread, onRerender }: {
  inv: Investigation
  /** Open a thread (a walked/bridge node clicked). */
  onOpenThread?: (threadId: string, label: string) => void
  /** Notify the parent a pin was added so it re-reads localStorage. */
  onRerender?: () => void
}) {
  // Capture a story surfaced by the constellation — the flywheel ring
  // (journey-map §1/§3.1). Metadata-only pin (no snapshot); opening it later
  // backfills evidence like any thread pin.
  const pinStory = (n: { id: string; label: string; category?: string | null }) => {
    addPin(inv.id, {
      anchorId: n.id,
      anchorType: 'thread',
      label: n.label,
      category: n.category ?? undefined,
      retrievalLane: 'constellation-walk',
      open: { surface: 'thread_detail', params: { thread_id: n.id } },
    })
    onRerender?.()
  }
  const pinKin = (k: WalkKin) => pinStory({ id: k.id, label: k.label, category: k.category })
  // The refetch key: the SET of connectable topic ids — note edits, trail
  // steps and non-thread pins never trigger a re-measure.
  const topicKey = useMemo(
    () => connectionTopicIds(inv).slice().sort().join('|'),
    [inv],
  )
  const topicCount = topicKey ? topicKey.split('|').length : 0

  const [data, setData] = useState<ConnectionsData | null | undefined>(undefined)
  // inv is re-read from localStorage every parent render (new object identity);
  // keep the latest in a ref so the effect can key on id+topicKey only.
  const invRef = useRef(inv)
  invRef.current = inv

  useEffect(() => {
    if (topicCount < 2) { setData(null); return }
    let alive = true
    setData(undefined)
    fetchConnections(invRef.current)
      .then(d => { if (alive) setData(d) })
      .catch(() => { if (alive) setData(null) })
    return () => { alive = false }
  }, [inv.id, topicKey, topicCount])

  // The connections view needs ≥2 pins (nothing to connect with one); the WALK
  // needs only ≥1 (it reaches outward from a single seed), so mount at ≥1.
  if (topicCount < 1) return null

  const cluster = data && data.nodes.length >= 2 ? deriveClusters(data.nodes, data.edges) : null
  const countries = data?.distributions?.countries ?? []

  return (
    <div className="wbc">
      <div className="wbc-head">
        <span
          className="wbc-title"
          data-tip="Measured live from your current pins (semantic proximity + coverage countries + shared actors). Coverage country is context, not a confirmed story link. Re-measures as you pin; the report freezes its own copy."
        >
          CONSTELLATION · LIVE
        </span>
        {data === undefined && <span className="wbc-status">measuring…</span>}
        {data && cluster && (
          <span className="wbc-status">
            {data.nodes.length} stories · {data.edges.length} links
          </span>
        )}
      </div>
      {data && cluster && (
        <>
          <InvestigativeUniverse
            data={data} cluster={cluster} compact
            onNodeClick={onOpenThread}
            onNodePin={pinStory}
          />
          {countries.length > 0 && (
            <div className="wbc-countries">
              <span className="wbc-countries-label" data-tip="Countries the pinned coverage touches, by signal volume. This is coverage geography, not subject identity.">touches</span>
              {countries.slice(0, 10).map(c => (
                <span key={c.cc} className="wbc-cc">{c.cc} {c.n}</span>
              ))}
            </div>
          )}
        </>
      )}
      {data === null && topicCount >= 2 && (
        <div className="wbc-status wbc-status--muted">
          connection measure unavailable — pins are unaffected
        </div>
      )}
      {/* The walked constellation — transitive kin from the pins, clickable +
          pinnable (the flywheel). Manages its own fetch/degree/empty state. */}
      <WalkConstellation inv={inv} onOpen={onOpenThread} onPin={pinKin} />
    </div>
  )
}
