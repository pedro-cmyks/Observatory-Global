import { useEffect, useState } from 'react'
import { BookOpen, HelpCircle, X } from 'lucide-react'
import './PanelHelpDrawer.css'

export type PanelHelpId =
    | 'globe'
    | 'signal-stream'
    | 'narrative-threads'
    | 'correlation-matrix'
    | 'anomaly-attention'
    | 'source-integrity'

interface PanelHelpContent {
    eyebrow: string
    title: string
    summary: string
    reads: string[]
    actions: string[]
    docsHash: string
}

const PANEL_HELP: Record<PanelHelpId, PanelHelpContent> = {
    globe: {
        eyebrow: 'Orientation layer',
        title: 'Globe',
        summary: 'The map shows where narratives are unusually active relative to each country baseline. Raw volume adds evidence density, but it is not a direct importance score.',
        reads: [
            'Glow: baseline-normalized country attention.',
            'Flow: countries sharing the same narrative frame.',
            'Ships and planes: live strategic context layers, not narrative ranking inputs.',
        ],
        actions: [
            'Click a country to open Country Intelligence.',
            'Use the reset control to fly toward the hottest normalized region.',
        ],
        docsHash: 'globe-panel',
    },
    'signal-stream': {
        eyebrow: 'Investigation entry',
        title: 'Signal Stream',
        summary: 'The stream is not meant to be read linearly. It is a pivot engine for turning a country, theme, person, source, or headline into a focused investigation.',
        reads: [
            'Rows are recent open signals selected for investigative usefulness.',
            'Country, theme, person, and source labels are clickable pivots.',
            'The center panel changes shape based on the active focus.',
        ],
        actions: [
            'Click a theme to open Narrative Detail.',
            'Pin useful items into Workspace before moving deeper.',
        ],
        docsHash: 'signal-stream-panel',
    },
    'narrative-threads': {
        eyebrow: 'Narrative engine',
        title: 'Narrative Threads',
        summary: 'Threads show how topics spread across countries and time. This is the core Atlas lens: not just what happened, but how public narratives are moving.',
        reads: [
            'Volume shows observed media signal count.',
            'Country tags show where the narrative is present.',
            'Trend lines show acceleration or fading over the selected window.',
        ],
        actions: [
            'Open a thread to inspect evolution, drift, people, related investigations, and coverage.',
            'Use related investigations carefully: they are pivots into adjacent frames.',
        ],
        docsHash: 'narrative-threads',
    },
    'correlation-matrix': {
        eyebrow: 'Shared framing',
        title: 'Correlation Matrix',
        summary: 'The matrix compares countries or themes by shared coverage patterns. It helps find who is talking about the same thing, not who is identical politically.',
        reads: [
            'Brighter cells mean stronger co-coverage.',
            'Country x Country compares shared narrative presence.',
            'Theme x Theme compares topics that travel together.',
        ],
        actions: [
            'Use it after a thread opens to find adjacent countries or themes.',
            'Treat high correlation as a lead, then validate in the stream and thread detail.',
        ],
        docsHash: 'correlation-panel',
    },
    'anomaly-attention': {
        eyebrow: 'Second lens',
        title: 'Anomaly Alert + Public Attention',
        summary: 'This panel contrasts media movement with public attention. Anomalies flag unusual media spikes; public attention shows what people are reading or searching.',
        reads: [
            'Geo alerts compare current country activity against recent baselines.',
            'Public attention comes from Wikipedia/Google-style attention signals where available.',
            'A public-attention item should become a narrative pivot, not a dead end.',
        ],
        actions: [
            'Click a public-attention item to open its investigation panel.',
            'Use related pills to continue into narrative threads or country context.',
        ],
        docsHash: 'public-attention-panel',
    },
    'source-integrity': {
        eyebrow: 'Coverage quality',
        title: 'Source Integrity',
        summary: 'Source Integrity estimates whether coverage is broad or dominated by a few outlets. It is a bias/coverage-health layer, not a truth score.',
        reads: [
            'Source Diversity counts how many outlets are active.',
            'Top Source Share highlights concentration risk.',
            'Source Quality compares known/allowlisted sources with unknown sources.',
        ],
        actions: [
            'Check this panel before trusting a high-volume country or theme.',
            'Use concentration leaders to inspect which publishers are shaping the view.',
        ],
        docsHash: 'source-integrity-panel',
    },
}

interface PanelHelpButtonProps {
    panel: PanelHelpId
}

export function PanelHelpButton({ panel }: PanelHelpButtonProps) {
    const [open, setOpen] = useState(false)
    const content = PANEL_HELP[panel]

    useEffect(() => {
        if (!open) return
        const onKey = (event: KeyboardEvent) => {
            if (event.key === 'Escape') setOpen(false)
        }
        window.addEventListener('keydown', onKey)
        return () => window.removeEventListener('keydown', onKey)
    }, [open])

    return (
        <>
            <button
                type="button"
                className="panel-help-trigger"
                onClick={(event) => {
                    event.stopPropagation()
                    setOpen(true)
                }}
                data-tip="Open panel guide"
                aria-label={`Open ${content.title} guide`}
            >
                <HelpCircle size={12} />
            </button>
            {open && (
                <div className="panel-help-layer" role="dialog" aria-modal="true" aria-labelledby={`panel-help-${panel}`}>
                    <button className="panel-help-scrim" aria-label="Close panel guide" onClick={() => setOpen(false)} />
                    <aside className="panel-help-drawer">
                        <header className="panel-help-header">
                            <div>
                                <span className="panel-help-eyebrow">{content.eyebrow}</span>
                                <h2 id={`panel-help-${panel}`}>{content.title}</h2>
                            </div>
                            <button className="panel-help-close" onClick={() => setOpen(false)} data-tip="Close guide" aria-label="Close guide">
                                <X size={16} />
                            </button>
                        </header>
                        <p className="panel-help-summary">{content.summary}</p>
                        <section className="panel-help-section">
                            <h3>What to read</h3>
                            <ul>
                                {content.reads.map(item => <li key={item}>{item}</li>)}
                            </ul>
                        </section>
                        <section className="panel-help-section">
                            <h3>What to do</h3>
                            <ul>
                                {content.actions.map(item => <li key={item}>{item}</li>)}
                            </ul>
                        </section>
                        <a className="panel-help-docs-link" href={`/docs#${content.docsHash}`}>
                            <BookOpen size={14} />
                            Read the full panel guide
                        </a>
                    </aside>
                </div>
            )}
        </>
    )
}
