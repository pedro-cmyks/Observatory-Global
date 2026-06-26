import { useMemo, useState } from 'react'
import { buildDossier, dossierToMarkdown } from '../lib/dossier'
import type { Investigation } from '../lib/workbench'
import './DossierView.css'

/** Phase 3 report view — a structured dossier generated from the FROZEN
 *  Workbench pins (#227 snapshots), with a Markdown export. */
export function DossierView({ investigation, onClose }: { investigation: Investigation; onClose: () => void }) {
    const now = useMemo(() => new Date().toISOString(), [])
    const dossier = useMemo(() => buildDossier(investigation, now), [investigation, now])
    const [copied, setCopied] = useState(false)

    const markdown = () => dossierToMarkdown(dossier)

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
