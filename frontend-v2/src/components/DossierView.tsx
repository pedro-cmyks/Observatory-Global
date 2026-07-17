import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { buildDossier, dossierToMarkdown, fmtDay } from '../lib/dossier'
import { fetchDossierEnrichment, resolveThreadTopicId, type DossierEnrichment } from '../lib/dossierEnrichment'
import {
    connectionsSummaryLines, coverageLensNote, buildFrozenCrossRefs,
    nodeStoryWindow, investigationStoryWindow,
    type ClusterResult, type ConnectionsData, type ConnectionNode,
} from '../lib/dossierConnections'
import { synthesizeDossier, synthesisMarkdown, isArticle, splitCitations, type DossierSynthesis } from '../lib/dossierSynthesis'
import {
    buildCorroborationRequest, fetchCorroboration, loadCachedCorroboration,
    saveCorroboration, corroborationMarkdown, statusChip, type CorroborationData,
} from '../lib/dossierCorroboration'
import { DossierConnections } from './DossierConnections'
import { track, trackOnce } from '../lib/telemetry'
import { humanizeReadinessValue } from '../lib/humanizeInternals'
import { renameInvestigation, type Investigation } from '../lib/workbench'
import {
    buildInvestigationPublication,
    buildPublicationReadinessMarkdown,
    buildRelationsMarkdown,
    summarizeInvestigationEdges,
    readableReasonCode,
    type InvestigationPublicationResult,
} from '../lib/investigationPublication'
import './DossierView.css'

/** P0.6a: article text with inline [n] receipt markers → clickable superscript
 *  anchors into the numbered receipts list below the article. */
function renderWithCitations(text: string) {
    return splitCitations(text).map((part, i) =>
        part.kind === 'text'
            ? <span key={i}>{part.text}</span>
            : (
                <sup key={i} className="dossier-cite-ref">
                    <a
                        href={`#dossier-cite-${part.n}`}
                        onClick={e => {
                            e.preventDefault()
                            // 'auto' not 'smooth': smooth scrollIntoView silently no-ops on the
                            // overlay scroller in Chrome (verified live) — instant jump always works.
                            document.getElementById(`dossier-cite-${part.n}`)?.scrollIntoView({ behavior: 'auto', block: 'center' })
                        }}
                    >[{part.n}]</a>
                </sup>
            ),
    )
}

/** Phase 3 report view — a structured dossier generated from the FROZEN
 *  Workbench pins (#227 snapshots), with a Markdown export. Dossier v2 (W3)
 *  adds who-says-what + voice sections MEASURED at generation time. */
export function DossierView({ investigation, onClose, autoCorroborate }: {
    investigation: Investigation; onClose: () => void; autoCorroborate?: boolean
}) {
    const now = useMemo(() => new Date().toISOString(), [])
    const [enrichment, setEnrichment] = useState<DossierEnrichment | undefined>(undefined)
    const dossier = useMemo(
        () => buildDossier(investigation, now, enrichment),
        [investigation, now, enrichment],
    )
    const [copied, setCopied] = useState(false)
    // Export feedback (council wish 12): downloads must confirm themselves too.
    const [downloaded, setDownloaded] = useState(false)
    // Title is a presentation/label concern (the frozen pins never change). The
    // H1 leads with the analyst's explicit rename if any, else the synthesis
    // headline (a real thesis, not the worst-conflated first-pin), else the
    // auto first-pin title. Rename persists on the investigation (survives reopen).
    const [customTitle, setCustomTitle] = useState<string | null>(
        investigation.titleCustom ? investigation.title : null,
    )
    const [editingTitle, setEditingTitle] = useState(false)
    const [titleDraft, setTitleDraft] = useState('')
    // Connection analysis is fetched inside DossierConnections; it hands the
    // measured data up here so the synthesis + Markdown export carry the findings.
    const [conn, setConn] = useState<{ data: ConnectionsData; cluster: ClusterResult } | null>(null)
    const onConnections = useCallback((data: ConnectionsData, cluster: ClusterResult) => {
        setConn({ data, cluster })
    }, [])

    // P0.3 story windows: header = whole-investigation span; per-pin windows
    // render on the pin cards once the connection measurement lands.
    const storyWindow = useMemo(
        () => (conn ? investigationStoryWindow(conn.data.nodes) : null),
        [conn],
    )
    const nodeForPin = useCallback((pinTopicId: string | null): ConnectionNode | null => {
        if (!pinTopicId || !conn) return null
        return conn.data.nodes.find(n => n.id === pinTopicId || n.collapsed_from?.includes(pinTopicId)) ?? null
    }, [conn])

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
    // StrictMode's simulated unmount sets this false — reset on (re)mount or
    // the synthesis result is silently swallowed in dev.
    useEffect(() => { mounted.current = true; return () => { mounted.current = false } }, [])
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

    // P0.6b web corroboration — pins checked against live web coverage with
    // source-independence weighting. Cached per investigation (re-run on
    // demand); DOC 2.0 permits one query per five seconds, so duration grows
    // with evidence-bearing pins. It is button-triggered, never automatic —
    // except via the Workbench CORROBORATE ramp.
    const [corrob, setCorrob] = useState<CorroborationData | null>(
        () => loadCachedCorroboration(investigation.id),
    )
    const [corrobRunning, setCorrobRunning] = useState(false)
    const [corrobFailed, setCorrobFailed] = useState(false)
    const corrobAutoFired = useRef(false)
    const runCorroboration = useCallback(async (force: boolean) => {
        if (dossierRef.current.pinCount === 0) return
        setCorrobRunning(true)
        setCorrobFailed(false)
        track('dossier_corroborate', { pins: dossierRef.current.pinCount, force })
        const body = buildCorroborationRequest(
            dossierRef.current.pins, connRef.current?.data.nodes ?? null)
        const data = await fetchCorroboration(body, force)
        if (!mounted.current) return
        if (data) {
            saveCorroboration(investigation.id, data)
            setCorrob(data)
        } else {
            setCorrobFailed(true)   // keep any cached result on screen
        }
        setCorrobRunning(false)
    }, [investigation.id])
    useEffect(() => {
        if (!autoCorroborate || corrobAutoFired.current) return
        corrobAutoFired.current = true
        if (!corrob) void runCorroboration(false)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [autoCorroborate])

    // W3: measured sections load after the frozen core renders; a fetch
    // failure leaves the report intact (sections simply absent).
    useEffect(() => {
        let alive = true
        fetchDossierEnrichment(investigation)
            .then(e => { if (alive) setEnrichment(e) })
            .catch(() => { /* frozen core stands alone */ })
        return () => { alive = false }
    }, [investigation])

    // Shared L1/L3 publication contract. This normalizes EVERY heterogeneous
    // Workbench pin into the typed graph, then measures 5W+H readiness without
    // asking the LLM to decide what matters or whether two things are related.
    // A missing endpoint degrades to an absent panel; the frozen dossier stays.
    const [publication, setPublication] = useState<InvestigationPublicationResult | null | undefined>(undefined)
    useEffect(() => {
        let alive = true
        if (investigation.pins.length === 0) {
            setPublication(null)
            return () => { alive = false }
        }
        setPublication(undefined)
        buildInvestigationPublication(investigation)
            .then(result => { if (alive) setPublication(result) })
        return () => { alive = false }
    }, [investigation])

    // T5.1: generating a report is the deepest value moment in the analyst loop.
    useEffect(() => {
        track('dossier_generated', { pins: dossier.pinCount })
        trackOnce('first_value_moment', { kind: 'dossier' })
    }, [dossier.pinCount])

    // Effective title: explicit rename > synthesis headline > auto first-pin title.
    const effectiveTitle = customTitle ?? (synth?.headline || null) ?? investigation.title

    const startRename = () => { setTitleDraft(effectiveTitle); setEditingTitle(true) }
    const commitRename = () => {
        const next = titleDraft.trim()
        renameInvestigation(investigation.id, next)
        // Blank clears the override → fall back to synthesis/auto title again.
        setCustomTitle(next || null)
        setEditingTitle(false)
        track('dossier_renamed')
    }

    const markdown = () => {
        // Export/filename use the same chosen title the report leads with.
        let base = dossierToMarkdown({ ...dossier, title: effectiveTitle })
        // Synthesis leads the report (above the templated summary) so the export
        // opens with the finding, not a pin count.
        if (synth && (synth.headline || synth.synthesis || isArticle(synth))) {
            const sblock = synthesisMarkdown(synth).join('\n')
            const sMarker = '## Executive summary'
            const sAt = base.indexOf(sMarker)
            base = sAt === -1 ? `${sblock}\n${base}` : `${base.slice(0, sAt)}${sblock}\n${base.slice(sAt)}`
        }
        // P0.6b: the web-corroboration section travels with the export.
        if (corrob) {
            const cblock = corroborationMarkdown(corrob).join('\n') + '\n'
            const cMarker = '\n## Timeline'
            const cAt = base.indexOf(cMarker)
            base = cAt === -1 ? `${base}\n${cblock}` : `${base.slice(0, cAt)}\n${cblock}${base.slice(cAt)}`
        }
        if (publication?.package) {
            const relBlock = buildRelationsMarkdown(publication.graph)
            const pblock = buildPublicationReadinessMarkdown(publication.package)
                + (relBlock ? `\n${relBlock}` : '') + '\n'
            const pMarker = '\n## Timeline'
            const pAt = base.indexOf(pMarker)
            base = pAt === -1 ? `${base}\n${pblock}` : `${base.slice(0, pAt)}\n${pblock}${base.slice(pAt)}`
        }
        if (!conn || conn.data.nodes.length < 2) return base
        const block = connectionsSummaryLines(conn.data, conn.cluster, {
            lensNote: coverageLensNote(conn.data.distributions?.languages ?? []),
            crossRefs: buildFrozenCrossRefs(investigation.pins, conn.data),
        }).join('\n') + '\n'
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
        a.download = `atlas-report-${effectiveTitle.replace(/[^a-z0-9]+/gi, '-').toLowerCase().slice(0, 40)}.md`
        a.click()
        URL.revokeObjectURL(url)
        setDownloaded(true)
        setTimeout(() => setDownloaded(false), 1600)
    }

    return (
        <div className="dossier-overlay" onClick={onClose}>
            <div className="dossier" onClick={e => e.stopPropagation()}>
                <div className="dossier-head">
                    <div>
                        <div className="dossier-kicker">INVESTIGATION REPORT</div>
                        {editingTitle ? (
                            <input
                                className="dossier-title-input"
                                autoFocus
                                value={titleDraft}
                                placeholder={synth?.headline || investigation.title}
                                onChange={e => setTitleDraft(e.target.value)}
                                onKeyDown={e => {
                                    if (e.key === 'Enter') commitRename()
                                    else if (e.key === 'Escape') setEditingTitle(false)
                                }}
                                onBlur={commitRename}
                            />
                        ) : (
                            <h1
                                className="dossier-title"
                                onClick={startRename}
                                title="Click to rename this report"
                            >
                                {effectiveTitle}
                                <span className="dossier-title-edit" aria-hidden> ✎</span>
                            </h1>
                        )}
                    </div>
                    <div className="dossier-actions">
                        <button
                            className="dossier-btn dossier-btn--corroborate"
                            onClick={() => void runCorroboration(!!corrob)}
                            disabled={corrobRunning || dossier.pinCount === 0}
                            data-tip="Check every evidence-bearing pin against live web coverage — independent sources weighted. Metadata-only context is marked not applicable. DOC 2.0 permits one query every five seconds, so duration grows with the route."
                        >{corrobRunning ? 'Corroborating every evidence pin…' : corrob ? 'Re-corroborate' : 'Corroborate'}</button>
                        <button className="dossier-btn" onClick={copy}>{copied ? 'Copied ✓' : 'Copy MD'}</button>
                        <button className="dossier-btn" onClick={download}>{downloaded ? 'Downloaded ✓' : 'Download'}</button>
                        <button className="dossier-close" onClick={onClose} aria-label="Close">×</button>
                    </div>
                </div>

                <div className="dossier-meta">
                    Generated {new Date(dossier.generatedAt).toLocaleString()} · {dossier.pinCount} pin{dossier.pinCount === 1 ? '' : 's'} · frozen at pin time
                    {storyWindow && <> · story window {fmtDay(storyWindow.first)} → {fmtDay(storyWindow.last)}</>}
                    {dossier.queries.length > 0 && <> · queries: {dossier.queries.join(' · ')}</>}
                </div>

                {(synth || (synth === undefined && dossier.pinCount > 0)) && (
                    <section className="dossier-section dossier-synthesis">
                        <h2>Synthesis</h2>
                        {synth === undefined ? (
                            <p className="dossier-meta">Writing the standalone brief…</p>
                        ) : synth && (synth.headline || synth.synthesis || isArticle(synth)) ? (
                            <>
                                {synth.headline && <p className="dossier-synth-headline">{synth.headline}</p>}
                                {isArticle(synth) ? (
                                    <>
                                        {synth.lede && <p className="dossier-synth-lede">{renderWithCitations(synth.lede)}</p>}
                                        {(synth.body ?? []).map((para, i) => (
                                            <p key={i}>{renderWithCitations(para)}</p>
                                        ))}
                                        {synth.unknowns && synth.unknowns.length > 0 && (
                                            <div className="dossier-synth-unknowns">
                                                <div className="dossier-synth-unknowns-title">What we don't know</div>
                                                <ul>
                                                    {synth.unknowns.map((u, i) => <li key={i}>{u}</li>)}
                                                </ul>
                                            </div>
                                        )}
                                        {synth.citations && synth.citations.length > 0 && (
                                            <ol className="dossier-synth-citations">
                                                {synth.citations.map(c => (
                                                    <li key={c.n} id={`dossier-cite-${c.n}`} value={c.n}>
                                                        {c.url
                                                            ? <a href={c.url} target="_blank" rel="noopener noreferrer">{c.headline}</a>
                                                            : c.headline}
                                                        {(c.source || c.date) && (
                                                            <span className="dossier-src"> — {[c.source, c.date ? fmtDay(c.date) : null].filter(Boolean).join(', ')}</span>
                                                        )}
                                                        <span className="dossier-cite-pin"> ({c.pin})</span>
                                                    </li>
                                                ))}
                                            </ol>
                                        )}
                                    </>
                                ) : (
                                    <>
                                        {synth.synthesis && <p>{synth.synthesis}</p>}
                                        {synth.gap && <p className="dossier-synth-gap">Key gap: {synth.gap}</p>}
                                    </>
                                )}
                                <p className="dossier-meta" data-tip="One grounded LLM pass over the frozen pins + the measured connection verdict. Every claim carries a numbered receipt from the frozen evidence. Measured now, not frozen; degrades to absence.">
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

                {dossier.pinCount > 0 && (
                    <section className="dossier-section dossier-readiness">
                        <h2>Editorial readiness — 5W+H</h2>
                        {publication === undefined ? (
                            <p className="dossier-meta">Measuring the pinned investigation against the shared L1/L3 publication contract…</p>
                        ) : publication ? (
                            <>
                                <div className="dossier-readiness-grid">
                                    {(['who', 'what', 'when', 'where', 'how', 'why'] as const).map(key => {
                                        const item = publication.package.readiness[key]
                                        return (
                                            <div key={key} className={`dossier-ready-card dossier-ready-card--${item.status}`}>
                                                <div className="dossier-ready-head">
                                                    <span>{key}</span>
                                                    <span>{item.status}</span>
                                                </div>
                                                {item.values.length > 0 && (
                                                    <div className="dossier-ready-values">
                                                        {/* Jargon purge (wish 7): internals like `changed_10h=-38` or
                                                            node hashes leak into these cells — render the human
                                                            paraphrase, keep the verbatim internal in the hover. */}
                                                        {item.values.map((v, i) => {
                                                            const h = humanizeReadinessValue(v)
                                                            return (
                                                                <span key={i}>
                                                                    {i > 0 && ' · '}
                                                                    {h.internal
                                                                        ? <span className="dossier-ready-internal" data-tip={`measured internal: ${h.raw}`}>{h.text}</span>
                                                                        : h.text}
                                                                </span>
                                                            )
                                                        })}
                                                    </div>
                                                )}
                                                {item.reason_codes.length > 0 && (
                                                    <div className="dossier-ready-reasons">
                                                        {item.reason_codes.map(readableReasonCode).join(' · ')}
                                                    </div>
                                                )}
                                            </div>
                                        )
                                    })}
                                </div>
                                <p className="dossier-meta">
                                    {publication.graph.nodes.length} typed node{publication.graph.nodes.length === 1 ? '' : 's'} · {publication.graph.edges.length} measured/inferred/contextual relation{publication.graph.edges.length === 1 ? '' : 's'} · {publication.package.receipts.length} receipt{publication.package.receipts.length === 1 ? '' : 's'}
                                    {publication.graph.completion.resolved_nodes < publication.graph.completion.requested_nodes
                                        ? ` · ${publication.graph.completion.requested_nodes - publication.graph.completion.resolved_nodes} metadata-only`
                                        : ''}
                                </p>
                                {publication.package.gaps.length > 0 && (
                                    <ul className="dossier-ready-gap-list">
                                        {publication.package.gaps.map(gap => (
                                            <li key={gap}>{readableReasonCode(gap)}</li>
                                        ))}
                                    </ul>
                                )}
                                {(() => {
                                    const edges = summarizeInvestigationEdges(publication.graph)
                                    if (edges.length === 0) return null
                                    return (
                                        <div className="dossier-relations">
                                            <h3 className="dossier-relations-title">Typed relations</h3>
                                            <ul className="dossier-relations-list">
                                                {edges.map((e, i) => (
                                                    <li key={`${e.relation}-${e.source}-${e.target}-${i}`} className={`dossier-relation dossier-relation--${e.tier}`}>
                                                        <span className="dossier-relation-tier">{e.tier}</span>
                                                        <span className="dossier-relation-body">
                                                            <strong>{e.relation}</strong> · {e.source} ↔ {e.target} · {e.receiptCount} receipt{e.receiptCount === 1 ? '' : 's'}
                                                            {e.caveats.length > 0 && (
                                                                <span className="dossier-relation-caveat"> · {e.caveats.map(readableReasonCode).join(' · ')}</span>
                                                            )}
                                                        </span>
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )
                                })()}
                            </>
                        ) : (
                            <p className="dossier-meta">Publication readiness unavailable — frozen evidence and the rest of the report remain intact.</p>
                        )}
                    </section>
                )}

                <section className="dossier-section">
                    <h2>Evidence ({dossier.pinCount})</h2>
                    {dossier.pins.length === 0 ? (
                        <p className="dossier-empty">No pins yet — pin anchors or truncated threads to build the report.</p>
                    ) : (
                        dossier.pins.map(p => {
                            const hasEvidence = (p.snapshot?.evidence ?? []).length > 0
                            const pinNode = nodeForPin(resolveThreadTopicId(p))
                            const win = pinNode ? nodeStoryWindow(pinNode) : null
                            return (
                            <div key={p.anchorId} className="dossier-pin">
                                <div className="dossier-pin-head">
                                    <span className="dossier-pin-label">{p.label}</span>
                                    <span className="dossier-pin-type">{p.anchorType}</span>
                                    {!hasEvidence && (
                                        <span className="dossier-pin-noev" data-tip="This pin froze metadata only — no evidence headlines were captured at pin time. Re-open the source to inspect it live.">
                                            metadata only — no frozen evidence
                                        </span>
                                    )}
                                </div>
                                {win && (
                                    <div className="dossier-pin-window">story window {fmtDay(win.first)} → {fmtDay(win.last)}</div>
                                )}
                                {p.snapshot?.summary && <div className="dossier-pin-summary">{p.snapshot.summary}</div>}
                                {hasEvidence && (
                                    <ul className="dossier-evidence">
                                        {p.snapshot!.evidence!.map((e, i) => (
                                            <li key={i}>
                                                {e.url ? <a href={e.url} target="_blank" rel="noopener noreferrer">{e.headline}</a> : e.headline}
                                                {(e.source || e.date) ? (
                                                    <span className="dossier-src"> — {e.source ?? ''}{e.source && e.date ? ', ' : ''}{e.date ? fmtDay(e.date) : ''}</span>
                                                ) : null}
                                            </li>
                                        ))}
                                    </ul>
                                )}
                                {p.note && <div className="dossier-note">Note: {p.note}</div>}
                            </div>
                            )
                        })
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

                {(corrob || corrobRunning || corrobFailed) && (
                    <section className="dossier-section dossier-corroboration">
                        <h2>Web corroboration</h2>
                        {corrobRunning ? (
                            <p className="dossier-meta">Checking every evidence-bearing pin against live web coverage… DOC 2.0 permits one query every five seconds, so duration grows with the route.</p>
                        ) : corrob ? (
                            <>
                                {corrob.search_available ? (
                                    <p className="dossier-meta" data-tip={corrob.meta?.independence_rule ?? ''}>
                                        measured {new Date(corrob.measured_at).toLocaleString()} · independent sources weighted · {corrob.search_source} · window {corrob.window_days}d
                                    </p>
                                ) : (
                                    <p className="dossier-meta">{corrob.meta?.search_note ?? 'Web-search lane unavailable — corroboration not measured.'}</p>
                                )}
                                {corrob.pins.map(p => (
                                    <div key={p.id} className="dossier-pin">
                                        <div className="dossier-pin-head">
                                            <span className={`dossier-corrob-chip dossier-corrob-chip--${p.status}`}>{statusChip(p.status)}</span>
                                            <span className="dossier-pin-label">{p.label}</span>
                                        </div>
                                        <div className="dossier-pin-summary">{p.note}</div>
                                        {p.citations.length > 0 && (
                                            <ul className="dossier-evidence">
                                                {p.citations.map((c, i) => (
                                                    <li key={i}>
                                                        {c.url ? <a href={c.url} target="_blank" rel="noopener noreferrer">{c.title}</a> : c.title}
                                                        <span className="dossier-src"> — {c.outlet}{c.lane === 'client-supplied' ? ' (supplied)' : ''}</span>
                                                    </li>
                                                ))}
                                            </ul>
                                        )}
                                    </div>
                                ))}
                                {corrob.coverage_asymmetry?.note && (
                                    <div className="dossier-pin">
                                        <div className="dossier-pin-head">
                                            <span className="dossier-pin-label">Coverage asymmetry</span>
                                            <span className="dossier-pin-type">what the web emphasizes vs the pinned evidence</span>
                                        </div>
                                        <div className="dossier-pin-summary">{corrob.coverage_asymmetry.note}</div>
                                        <p className="dossier-meta">phrased from the gathered titles only{corrob.coverage_asymmetry.provider ? ` · ${corrob.coverage_asymmetry.provider}` : ''}</p>
                                    </div>
                                )}
                            </>
                        ) : (
                            <p className="dossier-meta">Corroboration failed — the search lane did not answer. Re-run from the button above.</p>
                        )}
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
