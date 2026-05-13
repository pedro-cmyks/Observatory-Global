import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import './Landing.css'

const FILL_0 = { fontVariationSettings: "'FILL' 0" }

const SIGNAL_DOTS = [
    { top: '22%', left: '18%', delay: '0s' },
    { top: '38%', left: '78%', delay: '0.6s' },
    { top: '58%', left: '25%', delay: '1.2s' },
    { top: '70%', left: '65%', delay: '0.3s' },
    { top: '30%', left: '55%', delay: '1.8s' },
    { top: '15%', left: '42%', delay: '0.9s' },
    { top: '80%', left: '45%', delay: '1.5s' },
    { top: '50%', left: '88%', delay: '0.4s' },
]

function BentoCard({ icon, title, text }: { icon: string; title: string; text: string }) {
    return (
        <div className="lp-card-hover bg-bg-surface border border-border-subtle rounded-xl p-8 backdrop-blur-md relative overflow-hidden flex flex-col gap-stack-sm min-h-[220px]">
            <div className="absolute top-0 right-0 w-32 h-32 bg-primary/5 rounded-bl-full blur-xl pointer-events-none" />
            <span className="material-symbols-outlined text-primary text-3xl mb-2" style={FILL_0}>{icon}</span>
            <h3 className="font-body-strong text-body-strong text-text-primary text-lg">{title}</h3>
            <p className="font-body-main text-body-main text-text-secondary text-sm mt-auto">{text}</p>
        </div>
    )
}

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

function RevealSection({
    children,
    className = '',
    id,
}: {
    children: React.ReactNode
    className?: string
    id?: string
}) {
    const ref = useReveal()
    return (
        <section ref={ref} id={id} className={`lp-reveal ${className}`}>
            {children}
        </section>
    )
}

export function Landing() {
    const navigate = useNavigate()

    return (
        <div className="dark min-h-screen lp-bg text-on-surface font-body-main antialiased selection:bg-primary selection:text-on-primary">

            {/* ── Nav ── */}
            <nav className="fixed top-0 w-full z-50 bg-slate-950/80 backdrop-blur-xl border-b border-emerald-500/20 shadow-[0_8px_32px_rgba(0,0,0,0.4)]">
                <div className="flex justify-between items-center px-12 h-20 max-w-7xl mx-auto w-full">
                    <div className="flex items-center gap-12">
                        <a href="/" className="text-2xl font-black tracking-tighter text-emerald-500 drop-shadow-[0_0_8px_rgba(29,158,117,0.5)] font-['Outfit']">
                            ATLAS
                        </a>
                        <div className="hidden md:flex items-center gap-8">
                            <a href="#features" className="text-emerald-400 border-b border-emerald-500 font-bold px-1 py-2 font-nav-link text-nav-link">
                                Features
                            </a>
                            <a href="#data" className="text-slate-400 hover:text-emerald-300 transition-colors py-2 font-nav-link text-nav-link">
                                Data Sources
                            </a>
                            <a href="#support" className="text-slate-400 hover:text-emerald-300 transition-colors py-2 font-nav-link text-nav-link">
                                Support
                            </a>
                            <button
                                onClick={() => navigate('/docs')}
                                className="lp-nav-text-btn text-slate-400 hover:text-emerald-300 transition-colors py-2 font-nav-link text-nav-link"
                            >
                                Docs
                            </button>
                        </div>
                    </div>
                    <button
                        onClick={() => navigate('/brief')}
                        className="lp-btn-pulse bg-primary text-on-primary px-6 py-2 rounded font-body-strong text-body-strong transition-all"
                    >
                        Open Brief
                    </button>
                </div>
            </nav>

            <main className="pt-32 pb-20 px-8 max-w-7xl mx-auto w-full flex flex-col gap-section">

                {/* ── Hero ── */}
                <section className="relative isolate min-h-[680px] flex flex-col items-center justify-center text-center overflow-hidden">
                    {/* Radar visual */}
                    <div className="absolute inset-0 -z-10 flex items-center justify-center pointer-events-none" aria-hidden="true">
                        {SIGNAL_DOTS.map((d, i) => (
                            <span
                                key={i}
                                className="lp-signal-dot"
                                style={{ top: d.top, left: d.left, animationDelay: d.delay }}
                            />
                        ))}
                        <div className="relative w-[600px] h-[600px]">
                            <div className="absolute inset-0 border border-emerald-500/30 rounded-full" />
                            <div className="absolute inset-[90px] border border-emerald-500/20 rounded-full" />
                            <div className="absolute inset-[170px] border border-emerald-500/15 rounded-full" />
                            <div className="lp-radar-sweep" />
                            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-3 h-3 bg-primary rounded-full shadow-[0_0_20px_rgba(104,219,174,0.9)]" />
                        </div>
                    </div>

                    <div className="lp-hero-content z-10 max-w-4xl flex flex-col items-center gap-component">
                        <div className="flex items-center gap-2 px-4 py-1.5 rounded-full border border-border-subtle bg-bg-surface/80 backdrop-blur-md">
                            <span className="w-2 h-2 rounded-full bg-primary shadow-[0_0_8px_rgba(104,219,174,0.7)] animate-pulse" />
                            <span className="font-technical-label text-technical-label text-primary uppercase tracking-widest">Public intelligence</span>
                        </div>

                        <h1 className="font-display-xl text-display-xl text-text-primary leading-tight">
                            Atlas
                        </h1>

                        <p className="font-body-main text-body-main text-text-secondary max-w-xl text-lg">
                            A public narrative intelligence console that turns open global signals into
                            a daily brief, live map, country context, anomaly alerts, and investigation workspace.
                        </p>

                        <div className="flex flex-wrap justify-center gap-4 mt-4">
                            <button
                                onClick={() => navigate('/brief')}
                                className="lp-btn-pulse bg-primary text-on-primary px-10 py-4 rounded font-body-strong text-body-strong transition-all flex items-center gap-2"
                            >
                                Open Daily Brief
                                <span className="material-symbols-outlined" style={FILL_0}>arrow_forward</span>
                            </button>
                            <button
                                onClick={() => navigate('/app')}
                                className="px-10 py-4 rounded border border-emerald-500/40 bg-bg-surface/70 text-emerald-200 hover:border-primary/70 hover:text-white transition-all font-body-strong text-body-strong"
                            >
                                Open Console
                            </button>
                            <a
                                href="#features"
                                className="px-10 py-4 rounded border border-border-subtle text-text-secondary hover:border-primary/60 hover:text-text-primary transition-all font-body-strong text-body-strong"
                            >
                                See how it works
                            </a>
                        </div>
                    </div>
                </section>

                {/* ── Stats ── */}
                <RevealSection className="flex justify-center">
                    <div className="flex flex-wrap justify-center gap-0 bg-bg-surface border border-border-subtle rounded-xl overflow-hidden backdrop-blur-md divide-x divide-border-subtle">
                        {[
                            { value: '1.3M+', label: 'Signals indexed' },
                            { value: 'Multi', label: 'Open signal families' },
                            { value: '100+',  label: 'Languages observed' },
                            { value: 'Live',  label: 'Brief + console' },
                        ].map(({ value, label }) => (
                            <div key={label} className="flex flex-col items-center px-10 py-6">
                                <span className="lp-stat-num font-headline-md text-headline-md text-primary">{value}</span>
                                <span className="font-technical-label text-technical-label text-text-secondary uppercase mt-1">{label}</span>
                            </div>
                        ))}
                    </div>
                </RevealSection>

                {/* ── Support (early — easy to find) ── */}
                <RevealSection id="support" className="scroll-mt-24">
                    <div className="relative overflow-hidden rounded-xl border border-primary/40 bg-gradient-to-r from-bg-surface via-bg-surface to-emerald-950/30 p-8 flex flex-col md:flex-row items-center justify-between gap-6">
                        <div className="absolute inset-0 bg-gradient-to-r from-primary/5 to-transparent pointer-events-none" />
                        <div className="flex flex-col gap-2 z-10">
                            <span className="font-technical-label text-technical-label text-primary uppercase tracking-widest">Keep Atlas free</span>
                            <p className="font-headline-md text-headline-md text-text-primary">Atlas is free. Help keep it that way.</p>
                            <p className="font-body-main text-body-main text-text-secondary max-w-lg">
                                No ads, no paywalls, no tracking. The real-time data pipeline runs 24/7 at real cost.
                                If Atlas is useful to you, consider supporting it.
                            </p>
                        </div>
                        <div className="flex flex-col items-center gap-2 z-10 shrink-0">
                            <a
                                href="https://ko-fi.com/observatoryglobalatlas"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="lp-btn-pulse bg-primary text-on-primary px-10 py-3.5 rounded font-body-strong text-body-strong transition-all whitespace-nowrap"
                            >
                                Support Atlas on Ko-fi
                            </a>
                            <span className="font-technical-label text-technical-label text-text-secondary">One-time or recurring · No account needed</span>
                        </div>
                    </div>
                </RevealSection>

                {/* ── Features ── */}
                <RevealSection id="features" className="flex flex-col gap-gutter scroll-mt-24">
                    <div className="flex flex-col gap-stack-sm max-w-2xl">
                        <span className="font-technical-label text-technical-label text-primary uppercase tracking-widest">What you see</span>
                        <h2 className="font-headline-md text-headline-md text-text-primary">A daily brief for orientation.<br />A console for investigation.</h2>
                        <p className="font-body-main text-body-main text-text-secondary">
                            Atlas is designed for readers who need a global overview and analysts who need
                            to move from a signal into context, sources, and a workspace.
                        </p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-component">
                        <BentoCard icon="newspaper" title="Daily Brief"        text="A readable front page of global signal density, major themes, country mood, and source activity." />
                        <BentoCard icon="public"    title="Globe"              text="Live narrative activity by country. Flows show information pathways between nations." />
                        <BentoCard icon="stream"    title="Signal Stream"      text="A curated feed of notable open signals. Click a country, person, source, or theme to pivot the console." />
                        <BentoCard icon="list"      title="Narrative Threads"  text="Top global topics ranked by coverage volume, country spread, sentiment, and acceleration." />
                        <BentoCard icon="warning"   title="Anomaly Alert"      text="Statistical detection of unusual spikes when coverage breaks away from recent baselines." />
                        <BentoCard icon="account_tree" title="Workspace"       text="Pin countries, themes, people, sources, public-attention topics, and signals into an investigation graph." />
                    </div>
                </RevealSection>

                {/* ── Data sources ── */}
                <RevealSection id="data" className="flex flex-col gap-gutter scroll-mt-24">
                    <div className="flex flex-col gap-stack-sm max-w-2xl">
                        <span className="font-technical-label text-technical-label text-primary uppercase tracking-widest">The data</span>
                        <h2 className="font-headline-md text-headline-md text-text-primary">Open signals.<br />One coherent intelligence layer.</h2>
                        <p className="font-body-main text-body-main text-text-secondary">
                            Atlas normalizes open datasets into a unified signal layer. Different sources
                            update at different cadences, so the interface shows patterns instead of pretending
                            every feed refreshes on the same clock.
                        </p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-component">
                        {[
                            { name: 'Open media signals', badge: 'News coverage', desc: 'GDELT and normalized media events show how countries, sources, and themes are being covered.' },
                            { name: 'Curated RSS',        badge: 'Source breadth', desc: 'Regional, state, NGO, and non-English feeds expand coverage beyond the default global media layer.' },
                            { name: 'ReliefWeb / OCHA',   badge: 'Humanitarian',   desc: 'Crisis-country feeds add humanitarian context with provenance and geo-confidence metadata.' },
                            { name: 'Google Trends',      badge: 'Search demand',  desc: 'Country-level search interest helps compare what publics are looking for with what media covers.' },
                            { name: 'Wikipedia',          badge: 'Reading attention', desc: 'Top-read pages reveal public attention spikes that can appear before or beside media signals.' },
                            { name: 'NLP enrichment',     badge: 'Intel layer',    desc: 'Sentiment, named entities, framing, source family, language, and provenance fields make the signal investigable.' },
                        ].map(({ name, badge, desc }) => (
                            <div key={name} className="lp-card-hover bg-bg-surface border border-border-subtle rounded-xl p-6 flex flex-col gap-stack-sm">
                                <div className="flex items-center justify-between">
                                    <span className="font-body-strong text-body-strong text-text-primary">{name}</span>
                                    <span className="font-technical-label text-technical-label border border-border-subtle rounded-full px-3 py-1 uppercase text-[10px] tracking-wider text-primary">{badge}</span>
                                </div>
                                <p className="font-body-main text-body-main text-text-secondary">{desc}</p>
                            </div>
                        ))}
                    </div>
                </RevealSection>

                {/* ── Audience ── */}
                <RevealSection className="">
                    <div className="lp-card-hover bg-bg-surface border border-border-subtle rounded-xl p-10 backdrop-blur-md">
                        <div className="flex flex-col gap-stack-sm mb-8">
                            <span className="font-technical-label text-technical-label text-primary uppercase tracking-widest">Who it's for</span>
                            <h2 className="font-headline-md text-headline-md text-text-primary">Built for the curious.<br />Useful for everyone.</h2>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-component">
                            {[
                                { who: 'Journalists',     desc: 'Move from a global signal to country context, source concentration, headlines, and investigation notes.' },
                                { who: 'Researchers',     desc: 'Track narrative patterns, sentiment shifts, coverage anomalies, and source provenance across time and geography.' },
                                { who: 'Curious readers', desc: "Start with the daily brief and see what the world is paying attention to beyond one outlet's front page." },
                            ].map(({ who, desc }) => (
                                <div key={who} className="flex flex-col gap-stack-sm border-l border-border-subtle pl-6">
                                    <span className="font-body-strong text-body-strong text-primary">{who}</span>
                                    <p className="font-body-main text-body-main text-text-secondary">{desc}</p>
                                </div>
                            ))}
                        </div>
                    </div>
                </RevealSection>

                {/* ── Support (bottom — repeat for those who scrolled) ── */}
                <RevealSection className="">
                    <div className="bg-bg-surface border border-primary/25 rounded-xl p-10 text-center flex flex-col items-center gap-4 relative overflow-hidden">
                        <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-transparent pointer-events-none" />
                        <p className="font-body-main text-body-main text-text-secondary max-w-xl text-base z-10">
                            Atlas runs 24/7 on open data. 1.3M+ signals indexed, multi-source coverage, no ads.
                        </p>
                        <div className="flex gap-12 pt-4 border-t border-border-subtle w-full justify-center z-10">
                            {[
                                { value: '1.3M+', label: 'signals indexed' },
                                { value: 'Multi', label: 'source cadences' },
                                { value: 'Free', label: 'public access' },
                            ].map(({ value, label }) => (
                                <div key={label} className="flex flex-col items-center">
                                    <span className="lp-stat-num font-headline-md text-headline-md text-primary">{value}</span>
                                    <span className="font-technical-label text-technical-label text-text-secondary">{label}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </RevealSection>

            </main>

            {/* ── Footer ── */}
            <footer className="bg-slate-950 w-full py-14 border-t border-emerald-500/10">
                <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center px-8 gap-6">
                    <span className="text-emerald-500/70 font-['Space_Grotesk'] uppercase text-[11px] tracking-widest">
                        ATLAS · Observatory Global · Free & Open
                    </span>
                    <div className="flex flex-wrap gap-6 justify-center">
                        {[
                            { label: 'GDELT',         href: 'https://gdeltproject.org' },
                            { label: 'Google Trends', href: 'https://trends.google.com' },
                            { label: 'Wikipedia',     href: 'https://wikipedia.org' },
                            { label: 'ReliefWeb',     href: 'https://reliefweb.int' },
                            { label: 'GitHub',        href: 'https://github.com' },
                            { label: 'Support',       href: 'https://ko-fi.com/observatoryglobalatlas' },
                        ].map(({ label, href }) => (
                            <a key={label} href={href} target="_blank" rel="noopener noreferrer"
                                className="text-slate-500 hover:text-emerald-400 transition-colors font-['Space_Grotesk'] uppercase text-[11px] tracking-widest">
                                {label}
                            </a>
                        ))}
                    </div>
                </div>
            </footer>
        </div>
    )
}
