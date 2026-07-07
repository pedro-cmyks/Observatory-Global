import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { buildDossier, dossierToMarkdown } from '../lib/dossier'
import { fetchDossierEnrichment, type DossierEnrichment } from '../lib/dossierEnrichment'
import {
    connectionsSummaryLines,
    type ClusterResult, type ConnectionsData,
} from '../lib/dossierConnections'
import { synthesizeDossier, synthesisMarkdown, type DossierSynthesis } from '../lib/dossierSynthesis'
import { DossierConnections } from './DossierConnections'
import { track, trackOnce } from '../lib/telemetry'
import type { Investigation } from '../lib/workbench'
import './DossierView.css'

/** Phase 3 report view — a structured dossier generated from the FROZEN
 *  Workbench pins (#227 snapshots), with a Markdown export. Dossier v2 (W3)
 *  adds who-says-what + voice sections MEASURED at generation time. */
export function DossierView({ investigation, onClose }: { investigation: Investigation; onClose: () => void }) {
    const now = useMemo(() => new Date().toISOString(), [])
    const [enrichment, setEnrichment] = useState<DossierEnrichment | undefined>(undefined)
    const dossier = useMemo(
        () => buildDossier(investigation, now, enrichment),
        [investigation, now, enrichment],
    )
    const [copied, setCopied] = useState(false)
    // Connection analysis is fetched inside DossierConnections; it hands the
    // measured data up here so the synthesis + Markdown export carry the findings.
    const [conn, setConn] = useState<{ data: ConnectionsData; cluster: ClusterResult } | null>(null)
    const onConnections = useCallback((data: ConnectionsData, cluster: ClusterResult) => {
        setConn({ data, cluster })
    }, [])

    // #2 synthesis — the standalone brief. One grounded LLM pass over the frozen
    // pins + the measured connection verdict. Fires once the connection is
    // measured (so the verdict feeds it), or from pins alone as a fallback.
    const [synth, setSynth] = useState<DossierSynthesis | null | undefined>(undefined)
    // Refs so the single synthesis call always reads the freshest dossier + conn,
    // and its result lands as long as the component is mounted — independent of
    // which effect instance fired it (the fallback-timer closure would otherwise
    // be cancelled the moment `conn` arrives, swallowing the brief).
    const dossierRef = useRef(dossier)
    dossierRef.current = dossier
    const connRef = useRef(conn)
    connRef.current = conn
    const mounted = useRef(true)
    useEffect(() => () => { mounted.current = false }, [])
    const synthStarted = useRef(false)
    useEffect(() => {
        if (dossier.pinCount === 0) { setSynth(null); return }
        if (synthStarted.current) return
        const run = () => {
            if (synthStarted.current) return
            synthStarted.current = true
            synthesizeDossier(dossierRef.current, connRef.current)
                .then(s => { if (mounted.current) setSynth(s) })
        }
        // 1 pin → no connection to wait for; 2+ → fire as soon as the verdict is
        // measured, else fall back after 9s so a failed measurement never blocks
        // the brief. run() always reads the latest conn via connRef.
        if (dossier.pinCount < 2 || conn) { run(); return }
        const t = setTimeout(run, 9000)
        return () => clearTimeout(t)
    }, [investigation.id, conn, dossier.pinCount])

    // W3: measured sections load after the frozen core renders; a fetch
    // failure leaves the report intact (sections simply absent).
    useEffect(() => {
        let alive = true
        fetchDossierEnrichment(investigation)
            .then(e => { if (alive) setEnrichment(e) })
            .catch(() => { /* frozen core stands alone */ })
        return () => { alive = false }
    }, [investigation])

    // T5.1: generating a report is the deepest value moment in the analyst loop.
    useEffect(() => {
        track('dossier_generated', { pins: dossier.pinCount })
        trackOnce('first_value_moment', { kind: 'dossier' })
    }, [dossier.pinCount])

    const markdown = () => {
        let base = dossierToMarkdown(dossier)
        // Synthesis leads the report (above the templated summary) so the export
        // opens with the finding, not a pin count.
        if (synth && (synth.headline || synth.synthesis)) {
            const sblock = synthesisMarkdown(synth).join('\n')
            const sMarker = '## Executive summary'
            const sAt = base.indexOf(sMarker)
            base = sAt === -1 ? `${sblock}\n${base}` : `${base.slice(0, sAt)}${sblock}\n${base.slice(sAt)}`
        }
        if (!conn || conn.data.nodes.length < 2) return base
        const block = connectionsSummaryLines(conn.data, conn.cluster).join('\n') + '\n'
        // Insert the connection findings before the Timeline section.
        const marker = '\n## Timeline'
        const at = base.indexOf(marker)
        return at === -1 ? `${base}\n${block}` : `${base.slice(0, at)}\n${block}${base.slice(at)}`
    }

    const copy = async () => {
        try { await navigator.clipboard.writeText(markdown()); setCopied(true); setTimeout(() => setCopied(false), 1500) } catch { /* ignore */ }
    }
    const download = () => {
        const blob = new Blob([markdown()], { type: 'text/markdown' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `atlas-report-${investigation.title.replace(/[^a-z0-9]+/gi, '-').toLowerCase().slice(0, 40)}.md`
        a.click()
        URL.revokeObjectURL(url)
    }

    return (
        <div className="dossier-overlay" onClick={onClose}>
            <div className="dossier" onClick={e => e.stopPropagation()}>
                <div className="dossier-head">
                    <div>
                        <div className="dossier-kicker">INVESTIGATION REPORT</div>
                        <h1 className="dossier-title">{dossier.title}</h1>
                    </div>
                    <div className="dossier-actions">
                        <button className="dossier-btn" onClick={copy}>{copied ? 'Copied' : 'Copy MD'}</button>
                        <button className="dossier-btn" onClick={download}>Download</button>
                        <button className="dossier-close" onClick={onClose} aria-label="Close">×</button>
                    </div>
                </div>

                <div className="dossier-meta">
                    Generated {new Date(dossier.generatedAt).toLocaleString()} · {dossier.pinCount} pin{dossier.pinCount === 1 ? '' : 's'} · frozen at pin time
                    {dossier.queries.length > 0 && <> · queries: {dossier.queries.join(' · ')}</>}
                </div>

                {(synth || (synth === undefined && dossier.pinCount > 0)) && (
                    <section className="dossier-section dossier-synthesis">
                        <h2>Synthesis</h2>
                        {synth === undefined ? (
                            <p className="dossier-meta">Writing the standalone brief…</p>
                        ) : synth && (synth.headline || synth.synthesis) ? (
                            <>
                                {synth.headline && <p className="dossier-synth-headline">{synth.headline}</p>}
                                {synth.synthesis && <p>{synth.synthesis}</p>}
                                {synth.gap && <p className="dossier-synth-gap">Key gap: {synth.gap}</p>}
                                <p className="dossier-meta" data-tip="One grounded LLM pass over the frozen pins + the measured connection verdict. Measured now, not frozen; degrades to absence.">
                                    measured at generation time{synth.provider ? ` · ${synth.provider}` : ''} — grounded in pinned evidence + measured connections
                                </p>
                            </>
                        ) : (
                            <p className="dossier-meta">Synthesis unavailable — the templated summary below stands in.</p>
                        )}
                    </section>
                )}

                <section className="dossier-section">
                    <h2>Executive summary</h2>
                    <p>{dossier.summary}</p>
                </section>

                <section className="dossier-section">
                    <h2>Evidence ({dossier.pinCount})</h2>
                    {dossier.pins.length === 0 ? (
                        <p className="dossier-empty">No pins yet — pin anchors or truncated threads to build the report.</p>
                    ) : (
                        dossier.pins.map(p => (
                            <div key={p.anchorId} className="dossier-pin">
                                <div className="dossier-pin-head">
                                    <span className="dossier-pin-label">{p.label}</span>
                                    <span className="dossier-pin-type">{p.anchorType}</span>
                                </div>
                                {p.snapshot?.summary && <div className="dossier-pin-summary">{p.snapshot.summary}</div>}
                                {(p.snapshot?.evidence ?? []).length > 0 && (
                                    <ul className="dossier-evidence">
                                        {p.snapshot!.evidence!.map((e, i) => (
                                            <li key={i}>
                                                {e.url ? <a href={e.url} target="_blank" rel="noopener noreferrer">{e.headline}</a> : e.headline}
                                                {e.source ? <span className="dossier-src"> — {e.source}</span> : null}
                                            </li>
                                        ))}
                                    </ul>
                                )}
                                {p.note && <div className="dossier-note">Note: {p.note}</div>}
                            </div>
                        ))
                    )}
                </section>

                {dossier.pinCount >= 2 && (
                    <section className="dossier-section">
                        <h2>Connection analysis</h2>
                        <p className="dossier-meta" data-tip="Do these pinned stories form one narrative, and which sub-clusters connect? Semantic proximity + shared entities, measured now.">
                            do these stories connect — and which sub-narratives hold?
                        </p>
                        <DossierConnections inv={investigation} onData={onConnections} />
                    </section>
                )}

                {dossier.enrichment && Object.keys(dossier.enrichment.whoSaysWhat).length > 0 && (
                    <section className="dossier-section">
                        <h2>Who says what — press vs public</h2>
                        <p className="dossier-meta" data-tip="Typed member roles: press = verified evidence, public = forum/social discussion (never verified). Measured now, not frozen at pin time.">
                            measured at generation time · typed member roles
                        </p>
                        {dossier.pins.map(p => {
                            const e = dossier.enrichment!.whoSaysWhat[p.anchorId]
                            if (!e) return null
                            return (
                                <div key={p.anchorId} className="dossier-pin">
                                    <div className="dossier-pin-head">
                                        <span className="dossier-pin-label">{p.label}</span>
                                        <span className="dossier-pin-type">{e.relationship}</span>
                                    </div>
                                    <div className="dossier-pin-summary">
                                        press {e.evidenceCount} · public {e.discussionCount}
                                        {e.moodCount > 0 ? ` · mood ${e.moodCount}` : ''} — {e.rationale}
                                    </div>
                                    {e.sourceTiers && (
                                        <div className="dossier-pin-tiers" data-tip="Credibility tiers of the sources backing this thread (#217) — labels with provenance, measured now.">
                                            receipts by tier: {Object.entries(e.sourceTiers)
                                                .sort((a, b) => b[1] - a[1])
                                                .map(([t, n]) => `${t} ${n}`).join(' · ')}
                                        </div>
                                    )}
                                </div>
                            )
                        })}
                    </section>
                )}

                {dossier.enrichment && Object.keys(dossier.enrichment.voice).length > 0 && (
                    <section className="dossier-section">
                        <h2>Voice — who covers, not just who is covered</h2>
                        <p className="dossier-meta">self-voice = outlet ownership, not language · 168h window</p>
                        {Object.entries(dossier.enrichment.voice).map(([cc, v]) => (
                            <div key={cc} className="dossier-pin">
                                <div className="dossier-pin-head">
                                    <span className="dossier-pin-label">{cc}</span>
                                </div>
                                <div className="dossier-pin-summary">
                                    {v.selfVoiceRatio !== null && <>self-voice {(v.selfVoiceRatio * 100).toFixed(0)}% · </>}
                                    {v.dominantOutsider && <>dominant outsider {v.dominantOutsider} · </>}
                                    {v.stateMediaPct !== null && <>state media {v.stateMediaPct.toFixed(0)}% · </>}
                                    {v.topForeignOrigins.length > 0 && <>top foreign: {v.topForeignOrigins.join(', ')}</>}
                                </div>
                            </div>
                        ))}
                    </section>
                )}

                {dossier.categoryGroups.some(g => g.category !== null) && (
                    <section className="dossier-section">
                        <h2>Categories covered</h2>
                        <ul className="dossier-timeline">
                            {dossier.categoryGroups.map((g, i) => (
                                <li key={i}>
                                    <span className="dossier-tl-action">{g.category ?? 'uncategorized'}</span>
                                    <span className="dossier-tl-detail">
                                        {g.anchorIds.map(id => dossier.pins.find(p => p.anchorId === id)?.label).filter(Boolean).join('; ')}
                                    </span>
                                </li>
                            ))}
                        </ul>
                    </section>
                )}

                <section className="dossier-section">
                    <h2>Timeline</h2>
                    <ul className="dossier-timeline">
                        {dossier.timeline.map((s, i) => (
                            <li key={i}>
                                <span className="dossier-tl-action">{s.action}</span>
                                <span className="dossier-tl-detail">{s.detail}</span>
                            </li>
                        ))}
                    </ul>
                </section>

                {dossier.enrichment && dossier.enrichment.coverageGaps.length > 0 && (
                    <section className="dossier-section">
                        <h2>What is missing — attention without verified coverage</h2>
                        <p className="dossier-meta" data-tip="Categories with attention (raw signals) but zero gate-verified coverage in the last 24h. The wedge's 'what is missing', measured at generation.">
                            measured at generation time · global, last 24h
                        </p>
                        <ul className="dossier-timeline">
                            {dossier.enrichment.coverageGaps.map((g, i) => (
                                <li key={i}>
                                    <span className="dossier-tl-action">{g.label}</span>
                                    <span className="dossier-tl-detail">
                                        {g.rawSignals} raw signals · {g.status === 'gate_pending' ? 'awaiting gate' : 'none verified'}
                                    </span>
                                </li>
                            ))}
                        </ul>
                    </section>
                )}

                <section className="dossier-section dossier-gaps">
                    <h2>Gaps &amp; uncertainty</h2>
                    <ul>
                        {dossier.gaps.map((g, i) => <li key={i}>{g}</li>)}
                    </ul>
                </section>
            </div>
        </div>
    )
}
