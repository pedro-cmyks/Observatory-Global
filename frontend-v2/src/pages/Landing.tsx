import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { prefetchBriefing } from '../lib/briefingPrefetch'
import { HeroThread } from '../components/HeroThread'
import './Landing.css'

const FILL_0 = { fontVariationSettings: "'FILL' 0" }

function useReveal() {
    const ref = useRef<HTMLElement>(null)
    useEffect(() => {
        const el = ref.current
        if (!el) return
        const obs = new IntersectionObserver(
            ([entry]) => { if (entry.isIntersecting) { el.classList.add('lp-visible'); obs.disconnect() } },
            { threshold: 0.1 }
        )
        obs.observe(el)
        return () => obs.disconnect()
    }, [])
    return ref
}

function RevealSection({ children, className = '', id }: { children: React.ReactNode; className?: string; id?: string }) {
    const ref = useReveal()
    return (
        <section ref={ref} id={id} className={`lp-reveal ${className}`}>
            {children}
        </section>
    )
}

function formatSignalCount(n: number): string {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
    if (n >= 1_000) return `${Math.floor(n / 1_000)}k`
    return String(n)
}

interface Mover { id: string; label: string; trend: string; countries: number }

const TREND_LABEL: Record<string, string> = {
    accelerating: 'accelerating',
    fading: 'fading',
    stable: 'steady',
}

export function Landing() {
    const navigate = useNavigate()
    const [liveSignals, setLiveSignals] = useState<string | null>(null)
    const [liveStatus, setLiveStatus] = useState<'live' | 'degraded' | null>(null)
    const [movers, setMovers] = useState<Mover[] | null>(null)

    useEffect(() => { prefetchBriefing(24) }, [])

    useEffect(() => {
        fetch('/health')
            .then(r => r.ok ? r.json() : null)
            .then(d => {
                if (d?.total_signals) setLiveSignals(formatSignalCount(d.total_signals))
                if (d?.status) setLiveStatus(d.status === 'healthy' ? 'live' : 'degraded')
            })
            .catch(() => {})
    }, [])

    useEffect(() => {
        fetch('/api/v2/threads?hours=24&limit=4')
            .then(r => r.ok ? r.json() : null)
            .then(d => {
                const list: unknown[] = d?.threads ?? d ?? []
                const out: Mover[] = (Array.isArray(list) ? list : []).map((item) => {
                    const t = item as Record<string, unknown>
                    return {
                        id: (t.thread_id ?? t.id) as string,
                        label: (t.label ?? t.title) as string,
                        trend: (t.trend as string) ?? 'stable',
                        countries: (t.country_count as number) ?? (Array.isArray(t.top_countries) ? (t.top_countries as unknown[]).length : 0),
                    }
                }).filter(m => Boolean(m.id && m.label))
                if (out.length) setMovers(out)
                else setMovers([])
            })
            .catch(() => setMovers([]))
    }, [])

    const lead = movers && movers.length ? movers[0] : null
    const rest = movers && movers.length > 1 ? movers.slice(1, 4) : []

    return (
        <div className="lp-root dark min-h-screen text-on-surface antialiased selection:bg-primary selection:text-on-primary">

            {/* ── Nav ── */}
            <nav className="fixed top-0 w-full z-50 bg-slate-950/80 backdrop-blur-xl border-b border-emerald-500/15">
                <div className="flex justify-between items-center px-8 md:px-12 h-20 max-w-7xl mx-auto w-full">
                    <div className="flex items-center gap-10">
                        <a href="/" className="text-2xl font-black tracking-tight text-emerald-400 font-display-xl">Atlas</a>
                        <div className="hidden md:flex items-center gap-7">
                            <a href="#moving" className="text-slate-400 hover:text-emerald-300 transition-colors font-technical-label text-technical-label uppercase tracking-wider">Moving now</a>
                            <a href="#how" className="text-slate-400 hover:text-emerald-300 transition-colors font-technical-label text-technical-label uppercase tracking-wider">How it works</a>
                            <button onClick={() => navigate('/docs')} className="lp-nav-text-btn text-slate-400 hover:text-emerald-300 transition-colors font-technical-label text-technical-label uppercase tracking-wider">Docs</button>
                            <a href="#support" className="text-slate-400 hover:text-emerald-300 transition-colors font-technical-label text-technical-label uppercase tracking-wider">Support</a>
                        </div>
                    </div>
                    <button onClick={() => navigate('/brief')} className="lp-btn-pulse bg-primary text-on-primary px-6 py-2 rounded font-body-strong text-body-strong transition-all">
                        Read the brief
                    </button>
                </div>
            </nav>

            <main className="pt-28 max-w-7xl mx-auto w-full px-6 md:px-8">

                {/* ── 1 · Editorial hero ── */}
                <section className="lp-register-editorial pt-10 pb-20 flex flex-col items-center text-center">
                    <div className="flex items-center gap-2 px-4 py-1.5 rounded-full border border-border-subtle bg-bg-surface/70 backdrop-blur-md mb-8">
                        <span className="w-2 h-2 rounded-full bg-primary shadow-[0_0_8px_rgba(104,219,174,0.7)] animate-pulse" />
                        <span className="font-technical-label text-technical-label text-primary uppercase tracking-widest">Atlas · narrative intelligence · live</span>
                    </div>

                    <h1 className="font-display-xl text-text-primary leading-[1.04] text-5xl md:text-7xl tracking-tight">
                        Follow the thread.
                    </h1>

                    <p className="font-body-main text-text-secondary max-w-2xl text-lg mt-7 leading-relaxed">
                        Every live story is a web of countries, sources, and people. Watch a narrative move across the
                        world — how it spreads, mutates, and polarizes — then pull the thread into an investigation.
                    </p>

                    <div className="w-full max-w-4xl mt-10 mb-9">
                        <HeroThread />
                    </div>

                    <div className="flex flex-wrap justify-center gap-3">
                        <button onClick={() => navigate('/brief')} className="lp-btn-pulse bg-primary text-on-primary px-8 py-3.5 rounded font-body-strong text-body-strong transition-all flex items-center gap-2">
                            Start with the brief
                            <span className="material-symbols-outlined text-lg" style={FILL_0}>arrow_forward</span>
                        </button>
                        <button onClick={() => navigate('/app')} className="px-8 py-3.5 rounded border border-emerald-500/40 bg-bg-surface/60 text-emerald-200 hover:border-primary/70 hover:text-white transition-all font-body-strong text-body-strong">
                            Open the console
                        </button>
                        <a href="/docs" onClick={e => { e.preventDefault(); navigate('/docs') }} className="px-8 py-3.5 rounded border border-border-subtle text-text-secondary hover:border-primary/60 hover:text-text-primary transition-all font-body-strong text-body-strong">
                            Read the docs
                        </a>
                    </div>

                    <div className="flex flex-wrap justify-center gap-x-10 gap-y-3 mt-10 font-technical-label text-technical-label text-text-secondary uppercase tracking-wider">
                        <span className="tabular-nums"><span className="text-primary">{liveSignals ?? '—'}</span> signals indexed</span>
                        <span className="tabular-nums"><span className="text-primary">126</span> countries of voice</span>
                        <span><span className="text-primary">{liveStatus === 'degraded' ? 'Degraded' : 'Live'}</span> · ingesting every 15 min</span>
                    </div>
                </section>

                {/* ── 2 · Moving right now (editorial) ── */}
                <RevealSection id="moving" className="lp-register-editorial border-t border-white/10 py-16 scroll-mt-24">
                    <div className="font-technical-label text-technical-label text-primary uppercase tracking-widest mb-3">The world tonight</div>
                    <h2 className="font-headline-md text-text-primary text-3xl md:text-4xl mb-8">Moving right now</h2>
                    {movers === null && (
                        <p className="font-body-main text-text-secondary">Loading the latest narratives…</p>
                    )}
                    {movers !== null && movers.length === 0 && (
                        <p className="font-body-main text-text-secondary">No narratives are clearing the quality gate in this window. The console shows the full live stream.</p>
                    )}
                    {lead && (
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                            <button onClick={() => navigate('/app')} className="lp-lead-card text-left lg:col-span-2 bg-bg-surface border border-border-subtle rounded-xl p-8 hover:border-primary/50 transition-colors">
                                <span className={`lp-trend lp-trend--${lead.trend} font-technical-label uppercase tracking-wider`}>{TREND_LABEL[lead.trend] ?? lead.trend}</span>
                                <h3 className="font-headline-md text-text-primary text-2xl md:text-3xl mt-3 leading-snug">{lead.label}</h3>
                                <p className="font-body-main text-text-secondary mt-3 tabular-nums">Across {lead.countries} {lead.countries === 1 ? 'country' : 'countries'} — open the thread to see who's covering it and how.</p>
                            </button>
                            <div className="flex flex-col gap-3">
                                {rest.map(m => (
                                    <button key={m.id} onClick={() => navigate('/app')} className="text-left bg-bg-surface/60 border border-border-subtle rounded-lg px-5 py-4 hover:border-primary/40 transition-colors">
                                        <div className="flex items-center justify-between gap-3">
                                            <span className="font-body-strong text-text-primary text-sm leading-snug">{m.label}</span>
                                            <span className={`lp-trend lp-trend--${m.trend} font-technical-label uppercase shrink-0`}>{TREND_LABEL[m.trend] ?? m.trend}</span>
                                        </div>
                                        <span className="font-technical-label text-technical-label text-text-secondary tabular-nums">{m.countries} countries</span>
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}
                </RevealSection>

                {/* ── 3 · How narratives move (transition) ── */}
                <RevealSection id="how" className="lp-register-transition border-t border-white/10 py-16 scroll-mt-24">
                    <div className="font-technical-label text-technical-label text-primary uppercase tracking-widest mb-3">What Atlas reads</div>
                    <h2 className="font-headline-md text-text-primary text-3xl md:text-4xl mb-3">A story doesn't stay still.</h2>
                    <p className="font-body-main text-text-secondary max-w-2xl mb-10">Atlas measures the three ways a narrative changes as it travels — the asymmetries that are the actual intelligence.</p>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                        {[
                            { k: 'Spread', d: 'A story crosses borders — appearing in three countries while stalling in two others. That asymmetry is the signal.' },
                            { k: 'Mutation', d: 'Framing and sentiment shift as coverage travels. The same event is told differently from one source family to the next.' },
                            { k: 'Polarization', d: 'The same topic, opposite framing. When two countries cover one story with inverted sentiment, that is a polarized narrative.' },
                        ].map(c => (
                            <div key={c.k} className="bg-bg-surface/50 border-l-2 border-primary/40 pl-5 py-2">
                                <div className="font-headline-md text-text-primary text-xl mb-2">{c.k}</div>
                                <p className="font-body-main text-text-secondary text-sm leading-relaxed">{c.d}</p>
                            </div>
                        ))}
                    </div>
                </RevealSection>

                {/* ── 4 · Soft beat ── */}
                <div className="lp-beat py-10 text-center">
                    <span className="font-technical-label text-technical-label text-primary uppercase tracking-[0.3em]">From reading → investigating</span>
                </div>

                {/* ── 5 · Research Workflow (console climax) ── */}
                <RevealSection id="research" className="lp-register-console rounded-2xl border border-primary/25 bg-gradient-to-b from-emerald-950/20 to-transparent p-8 md:p-10 py-12 scroll-mt-24">
                    <div className="font-technical-label text-technical-label text-primary uppercase tracking-widest mb-3">Research · Workflow</div>
                    <h2 className="font-headline-md text-text-primary text-3xl md:text-4xl mb-3">From a question to an investigation.</h2>
                    <p className="font-body-main text-text-secondary max-w-2xl mb-9">Ask Atlas a real question. It returns a research plan you can interrogate — ranked anchors, honest gaps, and a workbench to assemble the evidence. The first answer is a starting board, never a closed verdict.</p>
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                        {[
                            { k: 'Ask', v: '"water stress in Iran"', chips: null },
                            { k: 'Anchors', v: 'ranked evidence', chips: ['direct', 'context', 'weak'] },
                            { k: 'Gaps', v: "what's missing — reported, not hidden", chips: null },
                            { k: 'Workbench', v: 'pin · trail · export', chips: null },
                        ].map((s, i) => (
                            <div key={s.k} className="lp-step bg-bg-surface border border-primary/20 rounded-lg p-4 relative">
                                <span className="lp-step-num font-technical-label text-text-secondary tabular-nums">0{i + 1}</span>
                                <div className="font-technical-label text-technical-label text-primary uppercase tracking-wider mt-1">{s.k}</div>
                                <div className="font-body-main text-text-primary text-sm mt-1">{s.v}</div>
                                {s.chips && (
                                    <div className="flex gap-1.5 mt-2.5 flex-wrap">
                                        {s.chips.map(c => <span key={c} className={`lp-chip lp-chip--${c} font-technical-label uppercase`}>{c}</span>)}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                    <button onClick={() => navigate('/app')} className="lp-btn-pulse bg-primary text-on-primary px-7 py-3 rounded font-body-strong text-body-strong mt-8 inline-flex items-center gap-2">
                        Start an investigation
                        <span className="material-symbols-outlined text-lg" style={FILL_0}>arrow_forward</span>
                    </button>
                </RevealSection>

                {/* ── 6 · The surfaces (console, non-uniform) ── */}
                <RevealSection id="surfaces" className="lp-register-console border-t border-white/10 py-16 scroll-mt-24">
                    <div className="font-technical-label text-technical-label text-primary uppercase tracking-widest mb-3">The instruments</div>
                    <h2 className="font-headline-md text-text-primary text-3xl md:text-4xl mb-8">Five surfaces, one connected console.</h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <button onClick={() => navigate('/app')} className="lp-surface-lead text-left md:col-span-2 md:row-span-2 bg-bg-surface border border-border-subtle rounded-xl p-8 hover:border-primary/50 transition-colors flex flex-col">
                            <span className="material-symbols-outlined text-primary text-3xl mb-3" style={FILL_0}>public</span>
                            <h3 className="font-headline-md text-text-primary text-2xl mb-2">Globe &amp; flows</h3>
                            <p className="font-body-main text-text-secondary">Country heat by composite anomaly — not raw volume. Flow arcs trace where a story originates and where it gets picked up. Focus a country and every surface re-scopes to its relations.</p>
                        </button>
                        {[
                            { icon: 'stream', title: 'Signal Stream', text: 'A pivot engine — click a country, source, person, or theme to refocus the console.' },
                            { icon: 'list', title: 'Narrative Threads', text: 'Living topics clustered from related coverage, ranked by spread, movement, and sentiment.' },
                            { icon: 'warning', title: 'Anomaly Alert', text: 'Statistical spikes when coverage breaks from a country’s own baseline.' },
                            { icon: 'account_tree', title: 'Workspace', text: 'Pin countries, sources, people, and signals into a saved investigation graph.' },
                        ].map(s => (
                            <button key={s.title} onClick={() => navigate('/app')} className="text-left bg-bg-surface/60 border border-border-subtle rounded-xl p-5 hover:border-primary/45 transition-colors">
                                <span className="material-symbols-outlined text-primary text-2xl mb-2" style={FILL_0}>{s.icon}</span>
                                <h3 className="font-body-strong text-text-primary text-base mb-1">{s.title}</h3>
                                <p className="font-body-main text-text-secondary text-sm">{s.text}</p>
                            </button>
                        ))}
                    </div>
                </RevealSection>

                {/* ── 7 · Data + voice (console) ── */}
                <RevealSection id="data" className="lp-register-console border-t border-white/10 py-16 scroll-mt-24">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        <div>
                            <div className="font-technical-label text-technical-label text-primary uppercase tracking-widest mb-3">The data</div>
                            <h2 className="font-headline-md text-text-primary text-2xl md:text-3xl mb-5">Open signals, one intelligence layer.</h2>
                            <ul className="flex flex-col gap-2.5">
                                {[
                                    ['GDELT media graph', 'global multilingual baseline'],
                                    ['RSS · ReliefWeb · news APIs', 'regional voice + crisis provenance'],
                                    ['Reddit', 'commentary, kept separate from evidence'],
                                    ['Google Trends · Wikipedia', 'public search + reference attention'],
                                    ['NLP + e5 embeddings', 'sentiment, entities, framing, semantic recall'],
                                ].map(([n, d]) => (
                                    <li key={n} className="flex items-baseline gap-3">
                                        <span className="w-1.5 h-1.5 rounded-full bg-primary mt-2 shrink-0" />
                                        <span className="font-body-main text-text-primary text-sm">{n} <span className="text-text-secondary">— {d}</span></span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                        <div className="bg-bg-surface border border-border-subtle rounded-xl p-7">
                            <div className="font-technical-label text-technical-label text-primary uppercase tracking-widest mb-3">Voice</div>
                            <h3 className="font-headline-md text-text-primary text-xl md:text-2xl mb-3">Global without the monoculture.</h3>
                            <p className="font-body-main text-text-secondary text-sm mb-5">"Global" is a measured claim. Atlas separates a country being <em>talked about</em> from a country having its own <em>voice</em> — self-coverage by outlet ownership, not language.</p>
                            <div className="flex gap-8">
                                <div><div className="font-headline-md text-primary text-2xl tabular-nums">126</div><div className="font-technical-label text-technical-label text-text-secondary uppercase">countries of voice</div></div>
                                <div><div className="font-headline-md text-primary text-2xl tabular-nums">31</div><div className="font-technical-label text-technical-label text-text-secondary uppercase">languages ingested</div></div>
                                <div><div className="font-headline-md text-primary text-2xl tabular-nums">0.71</div><div className="font-technical-label text-technical-label text-text-secondary uppercase">voice entropy</div></div>
                            </div>
                        </div>
                    </div>
                </RevealSection>

                {/* ── 8 · Audience ── */}
                <RevealSection className="lp-register-console border-t border-white/10 py-16">
                    <div className="font-technical-label text-technical-label text-primary uppercase tracking-widest mb-6">Who it's for</div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {[
                            { who: 'Journalists', desc: 'Move from a global signal to country context, source concentration, and investigation notes.' },
                            { who: 'Researchers', desc: 'Track narrative patterns, sentiment shifts, coverage anomalies, and source provenance over time.' },
                            { who: 'Curious readers', desc: "Start with the brief and see what the world is paying attention to beyond one outlet's front page." },
                        ].map(a => (
                            <div key={a.who} className="border-l border-border-subtle pl-5">
                                <div className="font-body-strong text-primary mb-1">{a.who}</div>
                                <p className="font-body-main text-text-secondary text-sm">{a.desc}</p>
                            </div>
                        ))}
                    </div>
                </RevealSection>

                {/* ── Support ── */}
                <RevealSection id="support" className="py-16 scroll-mt-24">
                    <div className="relative overflow-hidden rounded-2xl border border-primary/40 bg-gradient-to-r from-bg-surface via-bg-surface to-emerald-950/30 p-8 md:p-10 flex flex-col md:flex-row items-center justify-between gap-6">
                        <div className="flex flex-col gap-2 z-10">
                            <span className="font-technical-label text-technical-label text-primary uppercase tracking-widest">Keep Atlas free</span>
                            <p className="font-headline-md text-text-primary text-2xl">Atlas is free. Help keep it that way.</p>
                            <p className="font-body-main text-text-secondary max-w-lg">No ads, no paywalls, no tracking. The real-time pipeline runs 24/7 at real cost. If Atlas is useful to you, consider supporting it.</p>
                        </div>
                        <div className="flex flex-col items-center gap-2 z-10 shrink-0">
                            <a href="https://ko-fi.com/observatoryglobalatlas" target="_blank" rel="noopener noreferrer" className="lp-btn-pulse bg-primary text-on-primary px-10 py-3.5 rounded font-body-strong text-body-strong transition-all whitespace-nowrap">
                                Support Atlas on Ko-fi
                            </a>
                            <span className="font-technical-label text-technical-label text-text-secondary">One-time or recurring · No account needed</span>
                        </div>
                    </div>
                </RevealSection>
            </main>

            {/* ── Footer ── */}
            <footer className="bg-slate-950 w-full py-12 border-t border-emerald-500/10 mt-8">
                <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center px-8 gap-6">
                    <span className="text-emerald-500/70 font-technical-label uppercase text-[11px] tracking-widest">Atlas · Observatory Global · Free &amp; Open</span>
                    <div className="flex flex-wrap gap-6 justify-center">
                        {[
                            { label: 'GDELT', href: 'https://gdeltproject.org' },
                            { label: 'Google Trends', href: 'https://trends.google.com' },
                            { label: 'Wikipedia', href: 'https://wikipedia.org' },
                            { label: 'ReliefWeb', href: 'https://reliefweb.int' },
                            { label: 'GitHub', href: 'https://github.com/pedro-cmyks/Observatory-Global' },
                            { label: 'Support', href: 'https://ko-fi.com/observatoryglobalatlas' },
                        ].map(({ label, href }) => (
                            <a key={label} href={href} target="_blank" rel="noopener noreferrer" className="text-slate-500 hover:text-emerald-400 transition-colors font-technical-label uppercase text-[11px] tracking-widest">{label}</a>
                        ))}
                    </div>
                </div>
            </footer>
        </div>
    )
}
