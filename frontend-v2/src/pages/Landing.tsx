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
                        onClick={() => navigate('/app')}
                        className="lp-btn-pulse bg-primary text-on-primary px-6 py-2 rounded font-body-strong text-body-strong transition-all"
                    >
                        Open Atlas
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
                            <span className="font-technical-label text-technical-label text-primary uppercase tracking-widest">Live Data</span>
                        </div>

                        <h1 className="font-display-xl text-display-xl text-text-primary leading-tight">
                            The news,<br />before you read it.
                        </h1>

                        <p className="font-body-main text-body-main text-text-secondary max-w-xl text-lg">
                            See how 200+ countries cover the same world — simultaneously, without editorial filter.
                            Understand the coverage before you form an opinion.
                        </p>

                        <div className="flex gap-4 mt-4">
                            <button
                                onClick={() => navigate('/app')}
                                className="lp-btn-pulse bg-primary text-on-primary px-10 py-4 rounded font-body-strong text-body-strong transition-all flex items-center gap-2"
                            >
                                Open Atlas
                                <span className="material-symbols-outlined" style={FILL_0}>arrow_forward</span>
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
                            { value: '65,000+', label: 'Sources' },
                            { value: '15 min',  label: 'Refresh cycle' },
                            { value: '100+',    label: 'Languages' },
                            { value: '6',       label: 'Live data sources' },
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
                        <h2 className="font-headline-md text-headline-md text-text-primary">Six intelligence panels,<br />one coherent picture.</h2>
                        <p className="font-body-main text-body-main text-text-secondary">
                            Every panel answers a different question about the global information landscape.
                        </p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-component">
                        <BentoCard icon="public"   title="Globe"              text="Live heatmap of narrative activity by country. Flows show information pathways between nations." />
                        <BentoCard icon="stream"   title="Signal Stream"      text="Real-time feed of individual media signals from GDELT. Click any tag to filter the entire view." />
                        <BentoCard icon="list"     title="Narrative Threads"  text="Top global topics ranked by coverage volume, with sentiment trend and country spread." />
                        <BentoCard icon="grid_on"  title="Correlation Matrix" text="Shows which countries share narrative focus. Bright cells mean two nations report heavily on the same topic." />
                        <BentoCard icon="warning"  title="Anomaly Alert"      text="Statistical detection of unusual spikes in coverage — when a topic suddenly gets far more attention than its 7-day baseline." />
                        <BentoCard icon="verified" title="Source Integrity"   text="Monitors the diversity and quality of active sources. High concentration in a single outlet is flagged as a bias signal." />
                    </div>
                </RevealSection>

                {/* ── Data sources ── */}
                <RevealSection id="data" className="flex flex-col gap-gutter scroll-mt-24">
                    <div className="flex flex-col gap-stack-sm max-w-2xl">
                        <span className="font-technical-label text-technical-label text-primary uppercase tracking-widest">The data</span>
                        <h2 className="font-headline-md text-headline-md text-text-primary">Six open sources.<br />One coherent signal.</h2>
                        <p className="font-body-main text-body-main text-text-secondary">
                            All sources are open datasets. Atlas normalizes them into a unified signal without human editorial intervention.
                        </p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-component">
                        {[
                            { name: 'GDELT 2.0',      badge: 'Media coverage',   desc: '65,000+ news sources in 100+ languages, updated every 15 minutes. The backbone of Atlas.' },
                            { name: 'Google Trends',   badge: 'Public interest',  desc: 'What people are searching for, by country. Captures public attention before media catches up.' },
                            { name: 'Wikipedia',       badge: 'What people read', desc: 'Top-read articles by country and language. Wikipedia spikes often precede news events.' },
                            { name: 'ACLED',           badge: 'Conflict events',  desc: 'Armed Conflict Location & Event Data — the gold standard for tracking conflict events globally.' },
                            { name: 'ADS-B Exchange',  badge: 'Live aircraft',    desc: 'Real-time military and civilian aircraft positions worldwide via ADS-B transponder data.' },
                            { name: 'AISStream',       badge: 'Live vessels',     desc: 'Live ship positions at global chokepoints — Suez, Hormuz, Panama, Malacca — updated continuously.' },
                        ].map(({ name, badge, desc }) => (
                            <div key={name} className="lp-card-hover bg-bg-surface border border-border-subtle rounded-xl p-6 flex flex-col gap-stack-sm">
                                <div className="flex items-center justify-between">
                                    <span className="font-body-strong text-body-strong text-text-primary">{name}</span>
                                    <span className="font-technical-label text-technical-label text-primary border border-border-subtle rounded-full px-3 py-1 uppercase text-[10px] tracking-wider">{badge}</span>
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
                                { who: 'Journalists',     desc: 'See how your story is covered globally before you file. Understand the international angle instantly.' },
                                { who: 'Researchers',     desc: 'Track narrative patterns, sentiment shifts, and coverage anomalies across time and geography.' },
                                { who: 'Curious readers', desc: "Start your news day with a global overview instead of a single outlet's editorial priority." },
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
                            Atlas runs 24/7 on open data. 1.3M+ signals indexed, 6 live sources, no ads.
                        </p>
                        <div className="flex gap-12 pt-4 border-t border-border-subtle w-full justify-center z-10">
                            {[
                                { value: '1.3M+', label: 'signals indexed' },
                                { value: '15 min', label: 'refresh, 24/7' },
                                { value: '6', label: 'live sources' },
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
                            { label: 'ACLED',         href: 'https://acleddata.com' },
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
