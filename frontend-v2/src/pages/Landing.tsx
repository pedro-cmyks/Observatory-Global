import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './Landing.css'

// Animated globe SVG — same meridian style as the loader
function GlobeHero() {
    return (
        <div className="lp-globe-wrap" aria-hidden="true">
            <svg viewBox="0 0 280 280" className="lp-globe-svg">
                <defs>
                    <radialGradient id="glow" cx="50%" cy="50%" r="50%">
                        <stop offset="0%" stopColor="#1D9E75" stopOpacity="0.12" />
                        <stop offset="100%" stopColor="#1D9E75" stopOpacity="0" />
                    </radialGradient>
                </defs>
                {/* Background glow */}
                <circle cx="140" cy="140" r="130" fill="url(#glow)" />
                {/* Outer ring */}
                <circle cx="140" cy="140" r="118" fill="none" stroke="rgba(29,158,117,0.18)" strokeWidth="1" />
                {/* Latitude rings */}
                {[30, 55, 80, 105, 118].map((r, i) => (
                    <circle key={i} cx="140" cy="140" r={r}
                        fill="none" stroke="rgba(29,158,117,0.08)" strokeWidth="0.8" />
                ))}
                {/* Vertical meridians */}
                {[0, 45, 90, 135].map((deg, i) => (
                    <line key={i}
                        x1={140 + 118 * Math.cos(deg * Math.PI / 180)}
                        y1={140 + 118 * Math.sin(deg * Math.PI / 180)}
                        x2={140 - 118 * Math.cos(deg * Math.PI / 180)}
                        y2={140 - 118 * Math.sin(deg * Math.PI / 180)}
                        stroke="rgba(29,158,117,0.07)" strokeWidth="0.8"
                    />
                ))}
                {/* Spinning meridian ring */}
                <ellipse cx="140" cy="140" rx="118" ry="42"
                    fill="none" stroke="rgba(29,158,117,0.35)" strokeWidth="1"
                    className="lp-spin-meridian" />
                {/* Second meridian counter-rotating */}
                <ellipse cx="140" cy="140" rx="118" ry="70"
                    fill="none" stroke="rgba(29,158,117,0.2)" strokeWidth="0.8"
                    className="lp-spin-meridian-2" />
                {/* Sweeping scanner line */}
                <path d="M 140 22 A 118 118 0 0 1 140 258"
                    fill="none" stroke="rgba(29,158,117,0.6)" strokeWidth="1.5"
                    className="lp-sweep" />
                {/* Animated dots representing signals */}
                {[
                    { cx: 178, cy: 98 },
                    { cx: 110, cy: 155 },
                    { cx: 195, cy: 170 },
                    { cx: 88, cy: 115 },
                    { cx: 158, cy: 195 },
                    { cx: 125, cy: 85 },
                    { cx: 210, cy: 135 },
                    { cx: 70, cy: 158 },
                ].map((d, i) => (
                    <circle key={i} cx={d.cx} cy={d.cy} r="3"
                        fill="#1D9E75" opacity="0"
                        className="lp-signal-dot"
                        style={{ animationDelay: `${i * 0.4}s` }}
                    />
                ))}
                {/* Outer ring draw-in */}
                <circle cx="140" cy="140" r="118"
                    fill="none" stroke="#1D9E75" strokeWidth="1.5"
                    strokeDasharray="741" strokeDashoffset="741"
                    className="lp-ring-draw" />
            </svg>
        </div>
    )
}

// Animated counter for stats
function AnimatedStat({ value, label, suffix = '' }: { value: string; label: string; suffix?: string }) {
    return (
        <div className="lp-stat">
            <span className="lp-stat-value">{value}{suffix}</span>
            <span className="lp-stat-label">{label}</span>
        </div>
    )
}

// Panel preview card
function PanelCard({ icon, title, desc }: { icon: string; title: string; desc: string }) {
    return (
        <div className="lp-panel-card">
            <span className="lp-panel-icon">{icon}</span>
            <h4>{title}</h4>
            <p>{desc}</p>
        </div>
    )
}

// Step in the how-to section
function Step({ n, title, desc }: { n: number; title: string; desc: string }) {
    return (
        <div className="lp-step">
            <div className="lp-step-n">{n}</div>
            <div>
                <h4>{title}</h4>
                <p>{desc}</p>
            </div>
        </div>
    )
}

export function Landing() {
    const navigate = useNavigate()
    const [scrolled, setScrolled] = useState(false)

    useEffect(() => {
        const handler = () => setScrolled(window.scrollY > 20)
        window.addEventListener('scroll', handler)
        return () => window.removeEventListener('scroll', handler)
    }, [])

    return (
        <div className="lp-root">
            {/* ── Nav ── */}
            <nav className={`lp-nav ${scrolled ? 'lp-nav--scrolled' : ''}`}>
                <span className="lp-nav-brand">ATLAS</span>
                <div className="lp-nav-links">
                    <a href="#how">How it works</a>
                    <a href="#panels">What you see</a>
                    <a href="#data">Data</a>
                    <a onClick={() => navigate('/docs')} style={{ cursor: 'pointer' }}>Docs</a>
                    <a href="#support" className="lp-nav-support">Support</a>
                </div>
                <button className="lp-nav-cta" onClick={() => navigate('/app')}>
                    Open Atlas →
                </button>
            </nav>

            {/* ── Hero ── */}
            <section className="lp-hero">
                <div className="lp-hero-text">
                    <p className="lp-eyebrow">Global Media Intelligence</p>
                    <h1 className="lp-headline">
                        The news,<br />
                        before you read it.
                    </h1>
                    <p className="lp-subhead">
                        See how 200+ countries cover the same world — simultaneously,
                        without editorial filter. Understand the coverage before you
                        form an opinion.
                    </p>
                    <div className="lp-hero-actions">
                        <button className="lp-btn-primary" onClick={() => navigate('/app')}>
                            Open Atlas
                        </button>
                        <a href="#how" className="lp-btn-ghost">See how it works ↓</a>
                    </div>
                </div>
                <GlobeHero />
            </section>

            {/* ── Stats bar ── */}
            <div className="lp-stats-bar">
                <AnimatedStat value="200+" label="Countries tracked" />
                <div className="lp-stat-divider" />
                <AnimatedStat value="65K+" label="Global sources" />
                <div className="lp-stat-divider" />
                <AnimatedStat value="15" label="Minute refresh" suffix=" min" />
                <div className="lp-stat-divider" />
                <AnimatedStat value="100+" label="Languages" />
            </div>

            {/* ── What is it ── */}
            <section className="lp-section" id="how">
                <div className="lp-section-inner">
                    <div className="lp-section-tag">What Atlas is</div>
                    <h2>Not a news reader.<br />A coverage map.</h2>
                    <p className="lp-body">
                        Most news tools show you <em>what happened</em>. Atlas shows you <em>how it's being covered</em> —
                        which countries are paying attention, what tone they're using, and whether coverage is
                        accelerating or fading. You see the information landscape before you engage with individual articles.
                    </p>
                    <p className="lp-body">
                        The goal is impartiality by design. Instead of one editorial voice telling you what matters,
                        Atlas surfaces the raw signal across thousands of sources simultaneously. You form your own picture first —
                        then go read.
                    </p>
                    <div className="lp-quote">
                        "A decentralized way to see the news — you open Atlas,
                        understand the landscape, then go find the reporting."
                    </div>
                </div>
            </section>

            {/* ── How to use it ── */}
            <section className="lp-section lp-section--dark" id="how-to">
                <div className="lp-section-inner">
                    <div className="lp-section-tag">How to use it</div>
                    <h2>Three minutes to global context.</h2>
                    <div className="lp-steps">
                        <Step n={1}
                            title="Read the globe"
                            desc="Glowing regions show where media attention is concentrated right now. Brighter = more coverage. Click any country to see what it's reporting on and with what emotional tone."
                        />
                        <Step n={2}
                            title="Follow a narrative"
                            desc="Narrative Threads shows the dominant global stories. Click one to see how different countries frame it — the same event can look very different in Russian, Indian, or British media."
                        />
                        <Step n={3}
                            title="Find the signal"
                            desc="The Signal Stream shows individual articles in real time, prioritizing geopolitical content. Filter by country or topic to trace where a story is breaking."
                        />
                    </div>
                </div>
            </section>

            {/* ── Panels ── */}
            <section className="lp-section" id="panels">
                <div className="lp-section-inner">
                    <div className="lp-section-tag">What you see</div>
                    <h2>Six intelligence panels,<br />one coherent picture.</h2>
                    <div className="lp-panels-grid">
                        <PanelCard icon="🌍" title="Globe"
                            desc="Live heatmap of narrative activity by country. Flows show information pathways. Ships and aircraft track strategic assets at chokepoints." />
                        <PanelCard icon="📡" title="Signal Stream"
                            desc="Real-time feed of individual media signals from GDELT. Geopolitical content is prioritized. Click any tag to filter the entire view." />
                        <PanelCard icon="🧵" title="Narrative Threads"
                            desc="Top global topics ranked by coverage volume, with sentiment trend, country spread, and the key people being mentioned in each narrative." />
                        <PanelCard icon="⬛" title="Correlation Matrix"
                            desc="Shows which countries share narrative focus. Bright cells mean two nations are reporting heavily on the same topic simultaneously." />
                        <PanelCard icon="⚠️" title="Anomaly Alert"
                            desc="Statistical detection of unusual spikes in coverage — when a country or theme suddenly receives far more attention than its 7-day baseline." />
                        <PanelCard icon="🔍" title="Source Integrity"
                            desc="Monitors the diversity and quality of active sources. High concentration in a single outlet is flagged as a potential bias signal." />
                    </div>
                </div>
            </section>

            {/* ── Data ── */}
            <section className="lp-section lp-section--dark" id="data">
                <div className="lp-section-inner">
                    <div className="lp-section-tag">The data</div>
                    <h2>Four open sources.<br />One coherent signal.</h2>
                    <p className="lp-body">
                        Atlas crosses multiple public datasets to give you the full picture — not just
                        what media covers, but what people search, what they read, and where conflict is actually happening.
                    </p>
                    <div className="lp-sources-grid">
                        <div className="lp-source-card">
                            <div className="lp-source-name">GDELT 2.0</div>
                            <div className="lp-source-desc">65,000+ news sources in 100+ languages. Updated every 15 minutes. The backbone of Atlas.</div>
                            <div className="lp-source-badge">Media coverage</div>
                        </div>
                        <div className="lp-source-card">
                            <div className="lp-source-name">Google Trends</div>
                            <div className="lp-source-desc">What people are searching for, by country. Captures public attention before media catches up.</div>
                            <div className="lp-source-badge">Public interest</div>
                        </div>
                        <div className="lp-source-card">
                            <div className="lp-source-name">Wikipedia</div>
                            <div className="lp-source-desc">Top-read articles by country and language. Wikipedia spikes often precede news events.</div>
                            <div className="lp-source-badge">What people read</div>
                        </div>
                        <div className="lp-source-card">
                            <div className="lp-source-name">ACLED</div>
                            <div className="lp-source-desc">Armed Conflict Location & Event Data — the gold standard for tracking conflict events globally.</div>
                            <div className="lp-source-badge">Conflict events</div>
                        </div>
                    </div>
                    <p className="lp-body lp-body--muted">
                        All sources are open datasets. Atlas normalizes them into a unified signal without
                        human editorial intervention.
                    </p>
                </div>
            </section>

            {/* ── Who it's for ── */}
            <section className="lp-section">
                <div className="lp-section-inner lp-audience-inner">
                    <div className="lp-section-tag">Who it's for</div>
                    <h2>Built for the curious.<br />Useful for everyone.</h2>
                    <div className="lp-audience-grid">
                        <div className="lp-audience-card">
                            <span>Journalists</span>
                            <p>See how your story is covered globally before you file. Understand the international angle instantly.</p>
                        </div>
                        <div className="lp-audience-card">
                            <span>Researchers</span>
                            <p>Track narrative patterns, sentiment shifts, and coverage anomalies across time and geography.</p>
                        </div>
                        <div className="lp-audience-card">
                            <span>Curious readers</span>
                            <p>Start your news day with a global overview instead of a single outlet's editorial priority.</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* ── Support ── */}
            <section className="lp-section lp-section--dark" id="support">
                <div className="lp-section-inner lp-support-inner">
                    <div className="lp-support-left">
                        <div className="lp-section-tag">Keep Atlas free</div>
                        <h2>Atlas is free.<br />Help keep it that way.</h2>
                        <p className="lp-body">
                            Atlas has no ads, no paywalls, and no tracking. Like Wikipedia, it exists
                            because people believe open information is worth protecting.
                        </p>
                        <p className="lp-body">
                            Running the real-time data pipeline costs real money. If Atlas is useful to
                            you — for your work, your research, or just to understand the world better —
                            consider supporting it. Every contribution keeps the servers on and the data fresh.
                        </p>
                        <div className="lp-support-actions">
                            <a href="https://ko-fi.com" target="_blank" rel="noopener noreferrer" className="lp-btn-support">
                                Support Atlas
                            </a>
                            <span className="lp-support-note">One-time or recurring · No account needed</span>
                        </div>
                    </div>
                    <div className="lp-support-right">
                        <div className="lp-support-stat">
                            <span className="lp-support-num">278K+</span>
                            <span className="lp-support-label">signals processed today</span>
                        </div>
                        <div className="lp-support-stat">
                            <span className="lp-support-num">15 min</span>
                            <span className="lp-support-label">refresh cycle, 24/7</span>
                        </div>
                        <div className="lp-support-stat">
                            <span className="lp-support-num">4</span>
                            <span className="lp-support-label">live data sources</span>
                        </div>
                        <p className="lp-support-tagline">
                            "The goal is to remain free and open, like Wikipedia.
                            Future premium data sources may unlock a Pro tier —
                            but the core intelligence will always be public."
                        </p>
                    </div>
                </div>
            </section>

            {/* ── CTA ── */}
            <section className="lp-cta">
                <h2>Start with the overview.</h2>
                <p>See what the world's media is covering right now.</p>
                <button className="lp-btn-primary lp-btn-large" onClick={() => navigate('/app')}>
                    Open Atlas →
                </button>
                <p className="lp-cta-note">Free · No account required · Updated every 15 minutes</p>
            </section>

            {/* ── Footer ── */}
            <footer className="lp-footer">
                <span className="lp-footer-brand">ATLAS</span>
                <div className="lp-footer-links">
                    <span>GDELT · Google Trends · Wikipedia · ACLED</span>
                    <span>·</span>
                    <a href="https://github.com/pedro-cmyks/Observatory-Global" target="_blank" rel="noopener noreferrer">
                        GitHub
                    </a>
                    <span>·</span>
                    <a href="https://ko-fi.com" target="_blank" rel="noopener noreferrer">
                        Support
                    </a>
                </div>
            </footer>
        </div>
    )
}
