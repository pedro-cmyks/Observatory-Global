import { useEffect, useRef, useState } from 'react'
import { Download, Loader2, X } from 'lucide-react'
import type { PinnedItem } from '../contexts/WorkspaceContext'
import { fetchItemSignals, buildDossierMarkdown, type DossierSection, type DossierSignal } from '../lib/exportFormatters'
import { getThemeLabel } from '../lib/themeLabels'
import { resolveCountryName } from '../lib/countryNames'
import './ReadingMode.css'

interface ReadingModeProps {
    items: PinnedItem[]
    onClose: () => void
}

function sentimentColor(s: number): string {
    if (s > 0.1) return 'var(--color-sentiment-positive)'
    if (s < -0.1) return 'var(--color-sentiment-negative)'
    return 'var(--color-sentiment-neutral)'
}

function SignalCard({ sig }: { sig: DossierSignal }) {
    return (
        <article className="rm-signal-card">
            <div className="rm-signal-meta">
                <span className="rm-signal-source">{sig.source || 'unknown'}</span>
                <span className="rm-signal-country">{resolveCountryName(sig.country)}</span>
                <span className="rm-signal-date">{new Date(sig.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                <span className="rm-signal-sentiment" style={{ color: sentimentColor(sig.sentiment) }}>
                    {sig.sentiment > 0.1 ? '▲' : sig.sentiment < -0.1 ? '▼' : '—'}
                </span>
            </div>
            <p className="rm-signal-headline">{sig.headline || '(no headline)'}</p>
            {sig.persons?.length > 0 && (
                <p className="rm-signal-persons">{sig.persons.slice(0, 4).join(' · ')}</p>
            )}
            {sig.url && (
                <a className="rm-signal-url" href={sig.url} target="_blank" rel="noopener noreferrer">
                    {sig.url.length > 72 ? sig.url.slice(0, 72) + '…' : sig.url}
                </a>
            )}
        </article>
    )
}

function SectionBlock({ section }: { section: DossierSection }) {
    const { item, signals } = section
    const label = item.type === 'theme'
        ? getThemeLabel(new URLSearchParams(item.urlParams.replace(/^\?/, '')).get('theme') || item.id)
        : item.title

    return (
        <section className="rm-section">
            <header className="rm-section-header">
                <span className="rm-section-type">{item.type}</span>
                <h2 className="rm-section-title">{label}</h2>
                {item.notes.trim() && <p className="rm-section-notes">{item.notes}</p>}
                <span className="rm-section-count">{signals.length} signals</span>
            </header>
            {signals.length === 0 ? (
                <p className="rm-empty">No signals in this window.</p>
            ) : (
                <div className="rm-signals-grid">
                    {signals.map(sig => <SignalCard key={sig.id} sig={sig} />)}
                </div>
            )}
        </section>
    )
}

export function ReadingMode({ items, onClose }: ReadingModeProps) {
    const [sections, setSections] = useState<DossierSection[]>([])
    const [loading, setLoading] = useState(true)
    const [exporting, setExporting] = useState(false)
    const ref = useRef<HTMLDivElement>(null)

    useEffect(() => {
        const controller = new AbortController()
        const dossierItems = items.filter(i => ['theme', 'country', 'person'].includes(i.type))

        void (async () => {
            setLoading(true)
            const result = await Promise.all(
                dossierItems.map(async item => ({ item, signals: await fetchItemSignals(item) }))
            )
            if (!controller.signal.aborted) {
                setSections(result)
                setLoading(false)
            }
        })()

        return () => controller.abort()
    }, [items])

    useEffect(() => {
        const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
        window.addEventListener('keydown', onKey)
        return () => window.removeEventListener('keydown', onKey)
    }, [onClose])

    const handleExport = async () => {
        setExporting(true)
        try {
            const md = buildDossierMarkdown(sections)
            const blob = new Blob([md], { type: 'text/markdown' })
            const url = URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `atlas-dossier-${new Date().toISOString().split('T')[0]}.md`
            document.body.appendChild(a)
            a.click()
            document.body.removeChild(a)
            URL.revokeObjectURL(url)
        } finally {
            setExporting(false)
        }
    }

    const totalSignals = sections.reduce((n, s) => n + s.signals.length, 0)

    return (
        <div className="rm-layer" role="dialog" aria-modal="true" aria-label="Reading Mode">
            <button className="rm-scrim" aria-label="Close Reading Mode" onClick={onClose} />
            <div className="rm-panel" ref={ref}>
                <header className="rm-header">
                    <div className="rm-header-left">
                        <span className="rm-eyebrow">Atlas Investigation</span>
                        <h1 className="rm-title">Signal Dossier</h1>
                        <span className="rm-subtitle">
                            {loading ? 'Loading…' : `${sections.length} items · ${totalSignals} signals · last 7 days`}
                        </span>
                    </div>
                    <div className="rm-header-actions">
                        <button
                            type="button"
                            className="rm-action-btn"
                            onClick={handleExport}
                            disabled={loading || exporting}
                            data-tip="Export as Markdown"
                            aria-label="Export as Markdown"
                        >
                            {exporting ? <Loader2 size={14} className="spin" /> : <Download size={14} />}
                            Export .md
                        </button>
                        <button type="button" className="rm-close-btn" onClick={onClose} aria-label="Close">
                            <X size={18} />
                        </button>
                    </div>
                </header>

                <div className="rm-body">
                    {loading ? (
                        <div className="rm-loading">
                            <Loader2 size={24} className="spin" />
                            <span>Fetching signals for {items.filter(i => ['theme', 'country', 'person'].includes(i.type)).length} pinned items…</span>
                        </div>
                    ) : sections.length === 0 ? (
                        <p className="rm-empty">Pin themes, countries, or people to generate a dossier.</p>
                    ) : (
                        sections.map(section => <SectionBlock key={section.item.id} section={section} />)
                    )}
                </div>

                <footer className="rm-footer">
                    Sources: GDELT 2.0 · Atlas Signal Stream · {new Date().toUTCString()}
                </footer>
            </div>
        </div>
    )
}
