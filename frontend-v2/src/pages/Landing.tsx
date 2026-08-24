import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { prefetchBriefing } from '../lib/briefingPrefetch'
import { resolveVoiceStats, VOICE_BASELINE_LABEL, type VoiceStats } from '../lib/voiceStats'
import { formatSignalCount, formatCountriesCovering, resolveLiveStat, type CountriesCovering } from '../lib/landingStats'
import { decodeEntities } from '../lib/attentionEclipse'
import { useReaderTheme, ReaderThemeToggle, type ReaderTheme } from '../lib/readerTheme'
import { AtlasMark } from '../components/AtlasMark'
import '../styles/readerTheme.css'
import './Landing.css'

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

function RevealSection({ children, className = '', id, labelledBy }: { children: React.ReactNode; className?: string; id?: string; labelledBy?: string }) {
    const ref = useReveal()
    return (
        <section ref={ref} id={id} aria-labelledby={labelledBy} className={`lp-reveal ${className}`}>
            {children}
        </section>
    )
}

// formatSignalCount / formatCountriesCovering / resolveLiveStat live in
// lib/landingStats.ts (council P1-12: TDD'd formatters so the templates can
// never render "$ countries covering" or a silent em-dash again).

interface Mover { id: string; label: string; trend: string; covering: CountriesCovering | null }

const TREND_LABEL: Record<string, string> = {
    accelerating: 'accelerating',
    fading: 'fading',
    stable: 'steady',
}

const ArrowRight = () => (
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" /></svg>
)

// Same stroke language as ArrowRight (currentColor, 2.2 stroke) so the
// mobile toggle reads as part of this page's identity, not a bolted-on emoji.
const NavGlyph = ({ open }: { open: boolean }) => (
    <svg viewBox="0 0 24 24" width={17} height={17} stroke="currentColor" strokeWidth={2.2} fill="none" aria-hidden="true">
        {open
            ? <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
            : <path d="M4 7h16M4 12h16M4 17h16" strokeLinecap="round" />}
    </svg>
)

/* Ambient constellation field — Atlas's own "universe" of stories, kept faint.
   Deterministic seed per load; reduced-motion draws a single static frame;
   off-screen pauses the loop; the hero box re-syncs the bitmap on resize so
   the star field never stretches. Accent re-reads on reader-theme change. */
function ConstellationField({ theme }: { theme: ReaderTheme }) {
    const ref = useRef<HTMLCanvasElement>(null)
    useEffect(() => {
        const canvas = ref.current
        if (!canvas) return
        const ctx = canvas.getContext('2d')
        if (!ctx) return
        const reduce = typeof window.matchMedia === 'function'
            && window.matchMedia('(prefers-reduced-motion: reduce)').matches

        // tokens are SCOPED to .atlas-reader (never :root) — read off the canvas
        let accent = getComputedStyle(canvas).getPropertyValue('--r-accent').trim() || '#0f7b5a'

        const DPR = Math.min(window.devicePixelRatio || 1, 2)
        const N = 46
        const LINK = 132 // px distance to draw an edge (semantic-neighbor motif)
        let W = 0
        let H = 0
        interface Node { x: number; y: number; vx: number; vy: number; r: number; bright: boolean }
        let nodes: Node[] = []

        // deterministic pseudo-random so the field is stable per load
        let seed = 20260714
        const rnd = () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296 }

        function build() {
            if (!canvas) return
            const r = canvas.getBoundingClientRect()
            W = Math.max(1, r.width); H = Math.max(1, r.height)
            canvas.width = W * DPR; canvas.height = H * DPR
            ctx!.setTransform(DPR, 0, 0, DPR, 0, 0)
            seed = 20260714; nodes = []
            for (let i = 0; i < N; i++) {
                nodes.push({
                    x: rnd() * W, y: rnd() * H,
                    vx: (rnd() - 0.5) * 0.14, vy: (rnd() - 0.5) * 0.14,
                    r: 0.8 + rnd() * 1.7,
                    bright: rnd() > 0.82, // a few "lead" stories glow a touch
                })
            }
        }

        function hexA(hex: string, a: number): string {
            let h = hex.replace('#', '')
            if (h.length === 3) h = h[0] + h[0] + h[1] + h[1] + h[2] + h[2]
            const n = parseInt(h, 16)
            if (Number.isNaN(n)) return `rgba(15,123,90,${a})`
            return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`
        }

        function draw() {
            ctx!.clearRect(0, 0, W, H)
            for (let i = 0; i < nodes.length; i++) {
                for (let j = i + 1; j < nodes.length; j++) {
                    const a = nodes[i], b = nodes[j]
                    const dx = a.x - b.x, dy = a.y - b.y, d = Math.sqrt(dx * dx + dy * dy)
                    if (d < LINK) {
                        ctx!.strokeStyle = hexA(accent, (1 - d / LINK) * 0.16)
                        ctx!.lineWidth = 0.7
                        ctx!.beginPath(); ctx!.moveTo(a.x, a.y); ctx!.lineTo(b.x, b.y); ctx!.stroke()
                    }
                }
            }
            for (const p of nodes) {
                if (p.bright) {
                    ctx!.fillStyle = hexA(accent, 0.10)
                    ctx!.beginPath(); ctx!.arc(p.x, p.y, p.r * 4.5, 0, Math.PI * 2); ctx!.fill()
                }
                ctx!.fillStyle = hexA(accent, p.bright ? 0.62 : 0.34)
                ctx!.beginPath(); ctx!.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx!.fill()
            }
        }

        let raf: number | null = null
        let running = false
        function step() {
            for (const p of nodes) {
                p.x += p.vx; p.y += p.vy
                if (p.x < -10) p.x = W + 10; else if (p.x > W + 10) p.x = -10
                if (p.y < -10) p.y = H + 10; else if (p.y > H + 10) p.y = -10
            }
            draw()
            raf = requestAnimationFrame(step)
        }
        function start() { if (running || reduce) return; running = true; raf = requestAnimationFrame(step) }
        function stop() { running = false; if (raf !== null) cancelAnimationFrame(raf); raf = null }

        build()
        draw() // always paint one frame (covers reduced-motion + first paint)

        let io: IntersectionObserver | null = null
        if (!reduce) {
            if ('IntersectionObserver' in window) {
                io = new IntersectionObserver(
                    es => { es.forEach(e => { if (e.isIntersecting) start(); else stop() }) },
                    { threshold: 0.02 },
                )
                io.observe(canvas)
            } else {
                start()
            }
        }

        function rebuildNow() {
            accent = getComputedStyle(canvas!).getPropertyValue('--r-accent').trim() || accent
            const was = running
            stop(); build(); draw()
            if (was && !reduce) start()
        }
        let rt: ReturnType<typeof setTimeout> | undefined
        const rebuildSoon = () => { clearTimeout(rt); rt = setTimeout(rebuildNow, 140) }
        window.addEventListener('resize', rebuildSoon)

        // the hero box changes as fonts load / text reflows — re-sync the
        // bitmap 1:1 immediately so the field never smears into streaks
        let ro: ResizeObserver | null = null
        if ('ResizeObserver' in window) {
            let lastW = 0, lastH = 0
            ro = new ResizeObserver(es => {
                const r = es[0].contentRect
                if (Math.abs(r.width - lastW) > 1 || Math.abs(r.height - lastH) > 1) {
                    lastW = r.width; lastH = r.height
                    rebuildNow()
                }
            })
            ro.observe(canvas)
        }
        if (document.fonts?.ready) document.fonts.ready.then(rebuildNow).catch(() => {})

        return () => {
            stop()
            clearTimeout(rt)
            window.removeEventListener('resize', rebuildSoon)
            io?.disconnect()
            ro?.disconnect()
        }
    }, [theme]) // theme flips the scoped --r-accent: rebuild with the new hue
    return <canvas ref={ref} className="lp-field" aria-hidden="true" />
}

const PILLARS = [
    {
        pc: 'lp-pc-em',
        tag: 'Measured, not editorialized',
        h: 'Read from coverage',
        b: <>Prominence and position come from <b>coverage volume, languages and countries</b> — not an angle. Country heat is a composite anomaly signal, not raw volume, so the loudest outlet doesn't decide the map.</>,
    },
    {
        pc: 'lp-pc-em',
        tag: 'Who says what',
        h: 'Across borders and languages',
        b: <>Open any story to see who is covering it, in which countries and languages, and press against public. <b>Self-voice is measured by who owns the outlet</b>, not what language it prints — a country talked about is not the same as a country with its own voice.</>,
    },
    {
        pc: 'lp-pc-oc',
        tag: 'What is missing',
        h: 'Gaps, reported not hidden',
        b: <>A gaps lane names the under-covered story instead of dropping it. Nothing is filtered in silence — when a story is ranked down, <b>the ledger says why</b>. Absence is a finding, and Atlas prints it.</>,
    },
    {
        pc: 'lp-pc-pl',
        tag: 'Nothing is dropped',
        h: 'A newspaper with sections',
        b: <>Sport, markets and farándula each get a <b>section, not a gate</b>. Atlas damps noise, it doesn't delete it — a lens over the day, never a filter that decides what you're allowed to see.</>,
    },
]

// The header's real link set, verified against the JSX below (was Console +
// Docs; both are in-app routes navigated via react-router, not <a href>
// anchors, so the mobile copy must reuse navigate() too or it would trigger
// a full page reload instead of client-side routing).
const NAV_LINKS: Array<{ label: string; to: string }> = [
    { label: 'Console', to: '/app' },
    { label: 'Docs', to: '/docs' },
    { label: 'Create account', to: '/register' },
]

const DATA_SOURCES: Array<[string, string]> = [
    ['GDELT media graph', 'global multilingual baseline'],
    ['RSS · news APIs', 'regional voice + crisis provenance'],
    ['ReliefWeb', 'wired, pending institutional access — not currently producing'],
    ['Bluesky · Lemmy · Reddit (legacy)', 'commentary, kept separate from evidence'],
    ['Google Trends · Wikipedia', 'public search + reference attention'],
    ['NLP + e5 embeddings', 'sentiment, entities, framing, semantic recall'],
]

export function Landing() {
    const navigate = useNavigate()
    const { theme, toggle } = useReaderTheme()
    const [liveSignals, setLiveSignals] = useState<string | null>(null)
    const [liveFailed, setLiveFailed] = useState(false)
    const [liveStatus, setLiveStatus] = useState<'live' | 'degraded' | null>(null)
    const [movers, setMovers] = useState<Mover[] | null>(null)
    // L0 review item: these were hardcoded marketing numbers (126/31/0.71,
    // measured 2026-06-23) that would drift silently — now fetched live from
    // /api/v2/voice-mix. On fetch failure we fall back to that dated baseline
    // and SAY SO (resolveVoiceStats flags it; a suffix is rendered) so a
    // degraded fetch never asserts month-old numbers as current.
    const [voice, setVoice] = useState<VoiceStats | null>(null)
    // Mobile nav dropdown (#236): Console/Docs vanish below 560px with
    // nothing replacing them (`.lp-hidesm`, Landing.css:54) — this is the fix.
    const [navOpen, setNavOpen] = useState(false)
    const navWrapRef = useRef<HTMLDivElement>(null)

    useEffect(() => { prefetchBriefing(24) }, [])

    // Close on outside tap/click or Escape. No focus trap — four links behind
    // a marketing hamburger doesn't warrant one, but a menu that only closes
    // by re-tapping the same button is a real phone annoyance worth the ~10
    // lines it costs here.
    useEffect(() => {
        if (!navOpen) return
        const onPointerDown = (e: PointerEvent) => {
            if (navWrapRef.current && e.target instanceof Node && !navWrapRef.current.contains(e.target)) {
                setNavOpen(false)
            }
        }
        const onKeyDown = (e: KeyboardEvent) => { if (e.key === 'Escape') setNavOpen(false) }
        document.addEventListener('pointerdown', onPointerDown)
        document.addEventListener('keydown', onKeyDown)
        return () => {
            document.removeEventListener('pointerdown', onPointerDown)
            document.removeEventListener('keydown', onKeyDown)
        }
    }, [navOpen])

    useEffect(() => {
        fetch('/api/v2/voice-mix?hours=168')
            .then(r => r.ok ? r.json() : null)
            .then(d => {
                if (d?.distinct_origin_countries) setVoice({
                    countries: d.distinct_origin_countries,
                    langs: d.distinct_known_languages ?? 31,
                    entropy: (d.voice_entropy ?? 0.71).toFixed(2),
                })
            })
            .catch(() => {})
    }, [])

    useEffect(() => {
        fetch('/health')
            .then(r => r.ok ? r.json() : null)
            .then(d => {
                if (d?.total_signals) setLiveSignals(formatSignalCount(d.total_signals))
                else setLiveFailed(true)
                if (d?.status) setLiveStatus(d.status === 'healthy' ? 'live' : 'degraded')
            })
            .catch(() => setLiveFailed(true))
    }, [])

    useEffect(() => {
        fetch('/api/v2/threads?hours=24&limit=4')
            .then(r => r.ok ? r.json() : null)
            .then(d => {
                const list: unknown[] = d?.threads ?? d ?? []
                const out: Mover[] = (Array.isArray(list) ? list : []).map((item) => {
                    const t = item as Record<string, unknown>
                    const rawLabel = (t.label ?? t.title) as string
                    return {
                        id: (t.thread_id ?? t.id) as string,
                        label: typeof rawLabel === 'string' ? decodeEntities(rawLabel) : rawLabel,
                        trend: (t.trend as string) ?? 'stable',
                        // formatter rejects garbage + marks the capped top-countries
                        // list as a floor — the "5 countries covering ×3" fix.
                        covering: formatCountriesCovering(
                            t.country_count as number | null | undefined,
                            Array.isArray(t.top_countries) ? (t.top_countries as unknown[]).length : 0,
                        ),
                    }
                }).filter(m => Boolean(m.id && m.label))
                if (out.length) setMovers(out)
                else setMovers([])
            })
            .catch(() => setMovers([]))
    }, [])

    const voiceStats = resolveVoiceStats(voice)
    const signalsStat = resolveLiveStat(liveSignals, liveFailed)
    const openThread = (id: string) => navigate(`/app?theme=${encodeURIComponent(id)}&entry=landing`)

    return (
        <div className="atlas-reader lp-root" data-rtheme={theme}>
            <div className="lp-wrap">
                <div className="lp-topbar" />

                {/* ============ NAV ============ */}
                <header className="lp-nav">
                    <div className="lp-mk"><AtlasMark size={15} />ATLAS<span className="lp-dot">.</span></div>
                    <nav className="lp-navr" aria-label="Primary">
                        {NAV_LINKS.map(l => (
                            <button key={l.to} className="lp-nlink lp-hidesm" onClick={() => navigate(l.to)}>{l.label}</button>
                        ))}
                        <button className="lp-npill" onClick={() => navigate('/brief')}>Read the Brief</button>
                        <ReaderThemeToggle theme={theme} onToggle={toggle} />
                        {/* relative wrapper is scoped to just the toggle+menu, not the
                            whole header — the dropdown anchors off ITS OWN box
                            (top-full) instead of a guessed header-height offset. */}
                        <div className="relative hidden max-[560px]:block" ref={navWrapRef}>
                            <button
                                type="button"
                                className="appearance-none flex items-center justify-center min-h-[44px] min-w-[44px] rounded-full border-0 bg-transparent cursor-pointer text-[color:var(--r-ink-soft)] hover:text-[color:var(--r-ink)]"
                                aria-expanded={navOpen}
                                aria-haspopup="menu"
                                aria-controls="lp-mobile-nav"
                                aria-label={navOpen ? 'Close menu' : 'Menu'}
                                onClick={() => setNavOpen(o => !o)}
                            >
                                <NavGlyph open={navOpen} />
                            </button>
                            {navOpen && (
                                <nav
                                    id="lp-mobile-nav"
                                    aria-label="Mobile"
                                    className="absolute right-0 top-full mt-2 z-20 flex min-w-[170px] flex-col rounded-[5px] border border-[color:var(--r-line)] bg-[color:var(--r-surface)] p-1.5 shadow-lg"
                                >
                                    {NAV_LINKS.map(l => (
                                        <button
                                            key={l.to}
                                            className="appearance-none block w-full min-h-[44px] rounded-[4px] border-0 bg-transparent cursor-pointer px-3 py-2 text-left text-[13px] font-semibold text-[color:var(--r-ink-soft)] hover:bg-[color:var(--r-chip)] hover:text-[color:var(--r-ink)]"
                                            onClick={() => { setNavOpen(false); navigate(l.to) }}
                                        >
                                            {l.label}
                                        </button>
                                    ))}
                                </nav>
                            )}
                        </div>
                    </nav>
                </header>

                {/* ============ HERO ============ */}
                <section className="lp-hero" aria-label="Atlas — the news of the world, measured">
                    <ConstellationField theme={theme} />
                    <div className="lp-hero-mask" aria-hidden="true" />
                    <div className="lp-hero-in">
                        <p className="lp-hero-eye"><span className="lp-live" />Narrative intelligence · measured</p>
                        <h1 className="lp-wordmark">ATLAS<span className="lp-dot">.</span></h1>
                        <p className="lp-thesis">The news of the world, <em>measured.</em></p>
                        <p className="lp-subthesis">Who is saying what across countries and languages — and, just as plainly, <b>what is missing</b>. Positions are read from coverage, never editorialized.</p>
                        <div className="lp-cta-row">
                            <button className="lp-btn lp-btn-primary" onClick={() => navigate('/brief')}>Read the Brief<ArrowRight /></button>
                            <button className="lp-btn lp-btn-ghost" onClick={() => navigate('/app')}>Open the console</button>
                        </div>
                        <div className="lp-ticker" aria-label="Live totals">
                            <span className="lp-tk">
                                <span className="lp-tv">{signalsStat.display}</span>
                                <span className="lp-tl">{signalsStat.state === 'live' ? 'signals indexed' : `signals indexed · ${signalsStat.note}`}</span>
                            </span>
                            <span className="lp-tk">
                                <span className="lp-tv">{voiceStats.countries}</span>
                                <span className="lp-tl">countries of voice · attributable-origin base{voiceStats.isBaseline && <span className="lp-tbase"> ({VOICE_BASELINE_LABEL})</span>}</span>
                            </span>
                            <span className="lp-tnote"><span className="lp-g">●</span> {liveStatus === 'degraded' ? 'degraded' : 'live'} · ingesting every ~15 min</span>
                        </div>
                    </div>
                </section>

                {/* ============ WHAT ATLAS IS ============ */}
                <RevealSection className="lp-sect" labelledBy="lp-wai">
                    <p className="lp-kicker">What Atlas is</p>
                    <h2 className="lp-sect-title" id="lp-wai">A measured read on how the world is covered.</h2>
                    <p className="lp-sect-lede">Atlas aggregates the world's news into stories and tells you four honest things about each one — who is covering it, how the framing moves across borders, what is under-covered, and where the quiet sections are. No single front page, no editor's verdict.</p>
                    <div className="lp-pillars">
                        {PILLARS.map(p => (
                            <article key={p.tag} className={`lp-pill-card ${p.pc}`}>
                                <p className="lp-pill-tag"><i />{p.tag}</p>
                                <h3 className="lp-pill-h">{p.h}</h3>
                                <p className="lp-pill-b">{p.b}</p>
                            </article>
                        ))}
                    </div>
                </RevealSection>

                {/* ============ LIVE PROOF ============ */}
                <RevealSection id="proof" className="lp-sect lp-proof" labelledBy="lp-lp">
                    <p className="lp-kicker">Measured, in the open</p>
                    <h2 className="lp-sect-title" id="lp-lp">The claim of &ldquo;global&rdquo; is a number, not a slogan.</h2>
                    <p className="lp-sect-lede">Every figure below is read live from the Atlas API. When a live read fails, Atlas falls back to its last measured baseline and says so — a degraded fetch never asserts old numbers as current.</p>

                    <div className="lp-instrument" aria-label="Measured vitals">
                        <div className="lp-vital">
                            <div className="lp-vk">Signals</div>
                            <div className="lp-vv">{signalsStat.display}</div>
                            <div className="lp-vsub">
                                {signalsStat.state === 'live'
                                    ? 'indexed across the live store · ingesting every ~15 min'
                                    : signalsStat.note}
                            </div>
                        </div>
                        <div className="lp-vital">
                            <div className="lp-vk">Countries of voice</div>
                            <div className="lp-vv">{voiceStats.countries}</div>
                            <div className="lp-vsub">attributable-origin base · 7-day voice-mix{voiceStats.isBaseline ? ` · ${VOICE_BASELINE_LABEL}` : ''}</div>
                        </div>
                        <div className="lp-vital">
                            <div className="lp-vk">Languages</div>
                            <div className="lp-vv">{voiceStats.langs}</div>
                            <div className="lp-vsub">ingested · 7-day voice-mix{voiceStats.isBaseline ? ` · ${VOICE_BASELINE_LABEL}` : ''}</div>
                        </div>
                        <div className="lp-vital lp-hi">
                            <div className="lp-vk">Voice entropy</div>
                            <div className="lp-vv">{voiceStats.entropy}</div>
                            <div className="lp-vsub">origin diversity — &ldquo;global&rdquo; as a measured claim, self-coverage by outlet ownership, not language{voiceStats.isBaseline ? ` · ${VOICE_BASELINE_LABEL}` : ''}</div>
                        </div>
                    </div>
                    {voiceStats.isBaseline && (
                        <p className="lp-vnote">Live voice-mix unavailable — showing the dated baseline ({VOICE_BASELINE_LABEL}, measured 2026-06-23) rather than pretending it is current.</p>
                    )}

                    <p className="lp-subhead">Moving right now — the day's stories, measured</p>
                    {movers === null && (
                        <p className="lp-loading">Loading the latest narratives…</p>
                    )}
                    {movers !== null && movers.length === 0 && (
                        <p className="lp-loading">No narratives are clearing the quality gate in this window. The console shows the full live stream.</p>
                    )}
                    {movers !== null && movers.length > 0 && (
                        <div className="lp-today">
                            {movers.slice(0, 3).map(m => (
                                <button key={m.id} className="lp-tcard" onClick={() => openThread(m.id)}>
                                    <p className={`lp-tcat lp-trend--${m.trend}`}><i />{TREND_LABEL[m.trend] ?? m.trend}</p>
                                    <h3 className="lp-tlabel">{m.label}</h3>
                                    {m.covering && (
                                        <p className="lp-tmeta">
                                            <span data-tip={m.covering.approx
                                                ? 'A floor read from the story\'s capped top-countries list — the true count is at least this many.'
                                                : undefined}
                                            >
                                                <b>{m.covering.value}</b> {m.covering.noun} covering
                                            </span>
                                        </p>
                                    )}
                                    <div className="lp-trec"><span className="lp-rq">Open the story — who is covering it, and how <ArrowRight /></span></div>
                                </button>
                            ))}
                        </div>
                    )}
                    <p className="lp-todaynote">Stories are clustered live from cross-language coverage and ranked by spread, movement and coherence — <b>never by a single outlet's front page</b>. Opening one lands in the console, scoped to that story.</p>
                </RevealSection>

                {/* ============ HONEST LIMITS ============ */}
                <RevealSection className="lp-sect lp-limits" labelledBy="lp-hl">
                    <p className="lp-kicker">Where it is thin</p>
                    <h2 className="lp-sect-title" id="lp-hl">What Atlas is not.</h2>
                    <p className="lp-sect-lede">Atlas is measured — and measurement has edges. It is not omniscient, and pretending otherwise would break the one thing it's built on. Here is where it's thin today, in plain terms.</p>
                    <div className="lp-limitbox">
                        <p className="lp-lh">Honesty as a feature, not a footnote.</p>
                        <p className="lp-li">If a number would drift, we date it. If a lane runs empty, we leave the space empty. If English dominates, we print the share.</p>
                        <ul className="lp-limitlist">
                            <li><b>English is still the lingua franca of the wire.</b> Atlas pulls hundreds of feeds in dozens of languages to push back — and shows the measured share in-product instead of hiding it.</li>
                            <li><b>The live window is thin on purpose.</b> The hot store holds roughly the last week; everything older lives in the archive. The front door reads the hot window.</li>
                            <li><b>Prominence is coverage-volume share</b> — a proxy for attention, not a count of audience eyeballs. A loud story is well-covered, not necessarily well-read.</li>
                            <li><b>Some segments run degraded, and say so.</b> When a verification gate finds no admissible row, Atlas shows an honest empty state rather than filling the space with a fabricated answer.</li>
                        </ul>
                    </div>
                </RevealSection>

                {/* ============ ENTRY ============ */}
                <RevealSection className="lp-sect lp-entry" labelledBy="lp-en">
                    <div className="lp-entry-in">
                        <p className="lp-kicker lp-kicker-center">Start here</p>
                        <h2 className="lp-entry-h" id="lp-en">Read today's edition<span className="lp-dot">.</span></h2>
                        <p className="lp-entry-p">The Brief is the front page — measured, last 24 hours, with the receipts. The console is the full instrument: the globe, the stories, the gaps, and the workbench behind them.</p>
                        <div className="lp-entry-cta">
                            <button className="lp-btn lp-btn-primary" onClick={() => navigate('/brief')}>Read the Brief<ArrowRight /></button>
                            <button className="lp-btn lp-btn-ghost" onClick={() => navigate('/app')}>Open the console</button>
                        </div>
                        <p className="lp-entry-sub">or <a href="/docs" onClick={e => { e.preventDefault(); navigate('/docs') }}>read the docs</a> to see how the measuring is done.</p>
                    </div>
                </RevealSection>

                {/* ============ ACCOUNT CTA (campaign door) ============ */}
                <RevealSection id="account" className="lp-sect lp-account" labelledBy="lp-ac">
                    <div className="lp-accountbox">
                        <div>
                            <p className="lp-kicker">Your account</p>
                            <h2 className="lp-account-h" id="lp-ac">Free. Your account syncs your investigations across devices.</h2>
                            <p className="lp-account-p">You do not need an account to read Atlas. An account adds one thing: the investigations you pin in the workbench sync from laptop to phone. No ads, no paywalls.</p>
                        </div>
                        <div className="lp-account-cta">
                            <button className="lp-btn lp-btn-primary" onClick={() => navigate('/register')}>Create your free account<ArrowRight /></button>
                            <button className="lp-btn lp-btn-ghost" onClick={() => navigate('/register?mode=login')}>Sign in</button>
                        </div>
                    </div>
                </RevealSection>

                {/* ============ SUPPORT ============ */}
                <RevealSection id="support" className="lp-sect lp-support" labelledBy="lp-su">
                    <div className="lp-supportbox">
                        <div>
                            <p className="lp-kicker">Keep Atlas free</p>
                            <h2 className="lp-support-h" id="lp-su">Atlas is free. Help keep it that way.</h2>
                            <p className="lp-support-p">No ads, no paywalls, no tracking. The real-time pipeline runs 24/7 at real cost. If Atlas is useful to you, consider supporting it.</p>
                        </div>
                        <div className="lp-support-cta">
                            <a className="lp-btn lp-btn-primary" href="https://ko-fi.com/observatoryglobalatlas" target="_blank" rel="noopener noreferrer">Support Atlas on Ko-fi</a>
                            <span className="lp-support-sub">One-time or recurring · No account needed</span>
                        </div>
                    </div>
                </RevealSection>

                {/* ============ METHOD FOOTER ============ */}
                <footer className="lp-method">
                    <div className="lp-mtext">
                        <p><b>Positions and prominence are measured from coverage volume, languages and countries — not editorialized.</b> Nothing is hidden: every story has a section, and what a gate rejects is reported, not filled in. &ldquo;Global&rdquo; is a measured claim (voice entropy, distinct origin countries and languages), and self-coverage is measured by outlet ownership, not language. Receipts link to the original source. Where a subject geography or an admissible row could not be established, Atlas says so plainly.</p>
                        <ul className="lp-sources" aria-label="Data sources">
                            {DATA_SOURCES.map(([n, d]) => (
                                <li key={n}><b>{n}</b> — {d}</li>
                            ))}
                        </ul>
                        <div className="lp-flinks">
                            {[
                                { label: 'GDELT', href: 'https://gdeltproject.org' },
                                { label: 'Google Trends', href: 'https://trends.google.com' },
                                { label: 'Wikipedia', href: 'https://wikipedia.org' },
                                { label: 'ReliefWeb', href: 'https://reliefweb.int' },
                                { label: 'Support', href: 'https://ko-fi.com/observatoryglobalatlas' },
                            ].map(({ label, href }) => (
                                <a key={label} href={href} target="_blank" rel="noopener noreferrer">{label}</a>
                            ))}
                        </div>
                    </div>
                    <div className="lp-mmeta">
                        <div className="lp-wordmark-sm"><AtlasMark size={13} />ATLAS<span className="lp-dot">.</span></div>
                        <div>The Front Door · L0</div>
                        <div>Atlas · Observatory Global · Free &amp; Open</div>
                        <div>Measured · last 24 hours</div>
                        <div>Source: atlas-api-pedro /api/v2</div>
                    </div>
                </footer>
            </div>
        </div>
    )
}
