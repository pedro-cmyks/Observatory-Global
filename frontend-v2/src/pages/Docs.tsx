// Docs — "The news of the world, measured — and how to read the measurements."
//
// Re-skinned to the emerald reader identity (visual spec:
// artifact-backups/docs-atlas.html). Structure: hero + live vitals, sticky TOC
// (collapsing on mobile), What Atlas is / The four surfaces / The data layer /
// Method principles / Measured limits / FAQ.
//
// Theming is SCOPED: the .atlas-reader wrapper + data-rtheme carry the tokens
// (src/styles/readerTheme.css); nothing here touches :root/documentElement or
// ThemeContext — the console's Intel-Noir is untouched (keep-alive shell rule).

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useReaderTheme, ReaderThemeToggle } from '../lib/readerTheme'
import { AtlasMark } from '../components/AtlasMark'
import '../styles/readerTheme.css'
import './Docs.css'

const TOC: { id: string; label: string; children?: { id: string; label: string }[] }[] = [
    { id: 'what', label: 'What Atlas is' },
    { id: 'surfaces', label: 'The four surfaces' },
    { id: 'data', label: 'The data layer' },
    {
        id: 'method', label: 'Method principles', children: [
            { id: 'p-measured', label: 'Measured, not editorialized' },
            { id: 'p-heat', label: 'Heat is anomaly, not volume' },
            { id: 'p-lens', label: 'Lens, not gate' },
            { id: 'p-tiers', label: 'Verified vs UNVERIFIED' },
            { id: 'p-geo', label: 'Coverage-geo ≠ subject-geo' },
            { id: 'p-empty', label: 'Honest empties' },
        ]
    },
    { id: 'limits', label: 'Measured limits' },
    { id: 'faq', label: 'FAQ' },
]

interface DocsVitals {
    signals: number
    originCountries: number
    languages: number
    sources: number
    measuredAt: string // ISO date, UTC
}

function fmt(n: number): string {
    return n.toLocaleString('en-US')
}

export function Docs() {
    const navigate = useNavigate()
    const { theme, toggle } = useReaderTheme()
    const [activeId, setActiveId] = useState('what')
    const [tocOpen, setTocOpen] = useState(false)
    // Live vitals from the same measured feed the product uses (voice-mix,
    // 24h). On failure we show honest dashes — never a stale number asserted
    // as current (dated figures in the prose carry their own dates).
    const [vitals, setVitals] = useState<DocsVitals | null>(null)

    useEffect(() => {
        fetch('/api/v2/voice-mix?hours=24')
            .then(r => (r.ok ? r.json() : null))
            .then(d => {
                if (typeof d?.total_signals === 'number' && d.total_signals > 0) {
                    setVitals({
                        signals: d.total_signals,
                        originCountries: d.distinct_origin_countries ?? 0,
                        languages: d.distinct_known_languages ?? 0,
                        sources: d.distinct_sources ?? 0,
                        measuredAt: new Date().toISOString().slice(0, 10),
                    })
                }
            })
            .catch(() => { })
    }, [])

    // Scroll-spy over sections and the method-principle anchors.
    useEffect(() => {
        const observer = new IntersectionObserver(
            entries => {
                for (const entry of entries) {
                    if (entry.isIntersecting) setActiveId(entry.target.id)
                }
            },
            { rootMargin: '-15% 0px -75% 0px', threshold: 0 }
        )
        document
            .querySelectorAll('.docs-doc section[id], .docs-doc .docs-principle[id]')
            .forEach(el => observer.observe(el))
        return () => observer.disconnect()
    }, [])

    const scrollTo = (id: string) => {
        const reduced = typeof window !== 'undefined'
            && typeof window.matchMedia === 'function'
            && window.matchMedia('(prefers-reduced-motion: reduce)').matches
        document.getElementById(id)?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' })
        setTocOpen(false)
    }

    const tocLink = (id: string, label: string) => (
        <button
            key={id}
            className={`docs-toc-link ${activeId === id ? 'active' : ''}`}
            onClick={() => scrollTo(id)}
        >
            {label}
        </button>
    )

    return (
        <div className="atlas-reader docs-root" data-rtheme={theme}>
            <div className="docs-topbar" aria-hidden="true" />
            <div className="docs-wrap">

                {/* ── Masthead ── */}
                <header className="docs-nav">
                    <a
                        className="docs-mk"
                        href="/"
                        onClick={e => { e.preventDefault(); navigate('/') }}
                    >
                        <AtlasMark size={14} />Atlas<span className="docs-mk-dot">.</span>
                    </a>
                    <span className="docs-crumb">Documentation</span>
                    <div className="docs-nav-links">
                        <a onClick={() => navigate('/brief')} role="link" tabIndex={0}
                            onKeyDown={e => { if (e.key === 'Enter') navigate('/brief') }}>Brief</a>
                        <a onClick={() => navigate('/app')} role="link" tabIndex={0}
                            onKeyDown={e => { if (e.key === 'Enter') navigate('/app') }}>Console</a>
                        <ReaderThemeToggle theme={theme} onToggle={toggle} />
                    </div>
                </header>

                {/* ── Hero + live vitals ── */}
                <div className="docs-hero">
                    <p className="docs-kicker">How Atlas works</p>
                    <h1>The news of the world, measured — and how to read the measurements.</h1>
                    <p className="docs-lede">
                        Atlas is a narrative-intelligence system. It does not write news and it does not rank the world
                        by importance. It measures <em>coverage</em> — who is publishing what, about where, in which
                        languages, with how much movement — and shows you the shape of that coverage with the receipts
                        attached. This page explains the four surfaces, the data underneath them, and the method rules
                        that keep the numbers honest.
                    </p>
                    <div className="docs-statrow" role="group" aria-label="Live baseline measurements">
                        <div className="docs-stat">
                            <div className="docs-stat-n">{vitals ? fmt(vitals.signals) : '—'}</div>
                            <div className="docs-stat-l">signals / 24 h</div>
                        </div>
                        <div className="docs-stat">
                            <div className="docs-stat-n">{vitals ? fmt(vitals.originCountries) : '—'}</div>
                            <div className="docs-stat-l">origin countries · voice</div>
                        </div>
                        <div className="docs-stat">
                            <div className="docs-stat-n">{vitals ? fmt(vitals.languages) : '—'}</div>
                            <div className="docs-stat-l">languages detected</div>
                        </div>
                        <div className="docs-stat">
                            <div className="docs-stat-n">{vitals ? fmt(vitals.sources) : '—'}</div>
                            <div className="docs-stat-l">attributable sources · voice-mix base</div>
                        </div>
                        <span className="docs-measured-tag">
                            {vitals
                                ? `Measured · live API · ${vitals.measuredAt} UTC`
                                : 'Live vitals unavailable — dated figures below carry their own dates'}
                        </span>
                    </div>
                </div>

                <div className="docs-layout">

                    {/* ── TOC (sticky; collapsing on mobile) ── */}
                    <nav className={`docs-toc ${tocOpen ? 'open' : ''}`} aria-label="Contents">
                        <button
                            className="docs-toc-toggle"
                            aria-expanded={tocOpen}
                            aria-controls="docs-toc-body"
                            onClick={() => setTocOpen(v => !v)}
                        >
                            Contents
                        </button>
                        <div className="docs-toc-body" id="docs-toc-body">
                            <p className="docs-toc-title">Contents</p>
                            <ul>
                                {TOC.map(item => (
                                    <li key={item.id}>
                                        {tocLink(item.id, item.label)}
                                        {item.children && (
                                            <ul>
                                                {item.children.map(c => (
                                                    <li key={c.id}>{tocLink(c.id, c.label)}</li>
                                                ))}
                                            </ul>
                                        )}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </nav>

                    {/* ── Main ── */}
                    <main className="docs-doc">

                        {/* WHAT */}
                        <section id="what" aria-labelledby="what-h">
                            <p className="docs-eyebrow">Introduction</p>
                            <h2 id="what-h">What Atlas is</h2>
                            <p className="docs-lead">
                                Atlas ingests global news coverage and public-attention feeds, clusters them into living{' '}
                                <strong>narrative threads</strong>, and measures how those threads move: which countries
                                are covering them, in which languages, whose voice is present, whose is absent, and how
                                fast attention is accelerating or fading.
                            </p>
                            <p>
                                The unit of the product is the thread — a cluster of semantically related articles discovered
                                from multilingual text embeddings, not a fixed topic code. A thread carries its evidence
                                (real headlines with links), its geography of coverage, its movement over time, and its
                                open category badge. Categories are a <em>lens</em> laid over the threads, never the thing
                                you are reading.
                            </p>
                            <div className="docs-callout">
                                <p><strong>The core claim Atlas makes is small and checkable:</strong> "this many outlets,
                                    from these countries, in these languages, published about this — and here are the headlines."
                                    It deliberately does not claim to know what is <em>important</em>. Volume, movement, and
                                    diversity are measured separately so no single number can impersonate importance.</p>
                            </div>
                            <p>
                                Atlas is built for the narrative analyst — journalist, OSINT researcher, newsroom desk,
                                policy analyst — whose job is honest situational awareness on an event, topic, or country:
                                the real story, who is saying what across countries and languages, and what is missing.
                            </p>
                        </section>

                        {/* SURFACES */}
                        <section id="surfaces" aria-labelledby="surfaces-h">
                            <p className="docs-eyebrow">Product</p>
                            <h2 id="surfaces-h">The four surfaces</h2>
                            <p className="docs-lead">
                                Atlas is one system read at four depths. Each level has its own contract with time:
                                the Brief is the day, the Console treats time as a dimension you can scrub, and the
                                Workbench freezes time into evidence snapshots.
                            </p>
                            <div className="docs-cards">
                                <article className="docs-card">
                                    <span className="docs-tag">L0 · Landing</span>
                                    <h3>The front door</h3>
                                    <p>
                                        A public page that shows what the world's coverage looks like right now and states
                                        Atlas's diversity claims as live numbers rather than slogans — languages, origin
                                        countries, and self-voice ratios come from the same measured feed the product uses.
                                    </p>
                                    <p className="docs-card-do"><b>You can:</b> see today's measured shape of coverage and step into the Brief or Console.</p>
                                </article>
                                <article className="docs-card">
                                    <span className="docs-tag">L1 · Brief</span>
                                    <h3>The day, readable</h3>
                                    <p>
                                        A newspaper-style read of the last 24 hours — fixed window by design. A lead story
                                        built from the top thread with its evidence headlines, a watchlist with movement,
                                        a heating-countries strip, and a "what is missing" box listing categories with raw
                                        coverage but nothing that cleared the quality gate.
                                    </p>
                                    <p className="docs-card-do"><b>You can:</b> read the day in minutes, expand any story's receipts, and save a story into an investigation.</p>
                                </article>
                                <article className="docs-card">
                                    <span className="docs-tag">L2 · Console</span>
                                    <h3>Time as a dimension</h3>
                                    <p>
                                        The working view: an equal-area globe colored by composite heat, the live signal
                                        stream, narrative threads, a semantic universe of all active stories, and a
                                        public-attention dock. Scrubbers replay up to 30 days of real history; clicking a
                                        country, thread, or person re-scopes every panel to its relations.
                                    </p>
                                    <p className="docs-card-do"><b>You can:</b> orient, pivot, scrub back in time, and pull the day's archived receipts for any country.</p>
                                </article>
                                <article className="docs-card">
                                    <span className="docs-tag">L3 · Workbench</span>
                                    <h3>Time frozen</h3>
                                    <p>
                                        Investigations with pinned evidence. Every pin freezes a snapshot of what the data
                                        said at that moment, so your dossier does not drift under you. A research plan turns
                                        a natural-language question into ranked anchors with inspectable reasons; the dossier
                                        measures connections between your pins and exports as markdown.
                                    </p>
                                    <p className="docs-card-do"><b>You can:</b> pin, annotate, see measured relations between pinned stories, and export a dossier. Pins live in your browser, not on the server.</p>
                                </article>
                            </div>
                        </section>

                        {/* DATA */}
                        <section id="data" aria-labelledby="data-h">
                            <p className="docs-eyebrow">Substrate</p>
                            <h2 id="data-h">The data layer</h2>
                            <p className="docs-lead">
                                Every source is normalized into one signal schema, embedded with the same multilingual
                                model, and typed by the role it is allowed to play. Evidence, commentary, attention, and
                                context lanes never impersonate each other.
                            </p>
                            <div className="docs-tbl-scroll" tabIndex={0} role="region" aria-label="Data sources table">
                                <table>
                                    <thead>
                                        <tr><th>Source</th><th>Role</th><th>What it contributes</th></tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td>GDELT 2.0</td>
                                            <td><span className="docs-lane evidence">evidence</span></td>
                                            <td>The global media baseline — articles, themes, tone, persons, and CAMEO actor-action events, published every 15 minutes. The largest feed, and English-heavy (a measured limit, below).</td>
                                        </tr>
                                        <tr>
                                            <td>Native RSS network</td>
                                            <td><span className="docs-lane evidence">evidence</span></td>
                                            <td>219 hand-verified feeds across 126 countries and 31 languages (baseline 2026-06-23), built country by country so states have a domestic voice — outlet ownership is recorded, so "covered by its own press" is measurable.</td>
                                        </tr>
                                        <tr>
                                            <td>News APIs</td>
                                            <td><span className="docs-lane evidence">evidence</span></td>
                                            <td>NewsData, MediaStack, and NewsAPI add language- and region-targeted coverage where GDELT and RSS are thin, including the East-Asia language batch.</td>
                                        </tr>
                                        <tr>
                                            <td>Bluesky + Lemmy</td>
                                            <td><span className="docs-lane commentary">commentary</span></td>
                                            <td>The forum lane: public Bluesky posts (Jetstream firehose) and federated Lemmy instances. Always labeled UNVERIFIED, attached to threads as discussion only, and never allowed to seed a thread.</td>
                                        </tr>
                                        <tr>
                                            <td>Google Trends</td>
                                            <td><span className="docs-lane attention">attention</span></td>
                                            <td>What the public is searching, by country — the counterpart to what the press is publishing. Availability varies by country and the feed can lag; staleness is labeled, not hidden.</td>
                                        </tr>
                                        <tr>
                                            <td>Wikipedia pageviews</td>
                                            <td><span className="docs-lane attention">attention</span></td>
                                            <td>Reference-seeking behavior by language edition — a slower, deeper attention signal than search, fetched daily.</td>
                                        </tr>
                                        <tr>
                                            <td>USGS + GDACS</td>
                                            <td><span className="docs-lane context">events</span></td>
                                            <td>Natural-hazard events (earthquakes, floods, storms) that news taxonomies represent poorly, bound geo-temporally to threads so a disaster story carries its physical event.</td>
                                        </tr>
                                        <tr>
                                            <td>AIS vessels + aircraft</td>
                                            <td><span className="docs-lane context">map layer</span></td>
                                            <td>Live maritime and air traffic, rendered as map layers for situational context. Honestly labeled: these are visualization layers today, not narrative inputs.</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                            <div className="docs-callout ochre">
                                <p><strong>What is deliberately not on this list.</strong> ReliefWeb/OCHA ingestion is
                                    currently blocked at the institution's side (the open feeds were closed; API access
                                    requires an approved application) — the connector exists but produces nothing, so Atlas
                                    does not claim it. Reddit appears in older data as a social source but the live forum
                                    lane is Bluesky + Lemmy. When a source stops producing, the docs say so.</p>
                            </div>
                            <h3>Counting sources: two bases, two numbers</h3>
                            <p>
                                Two source counts appear across Atlas surfaces, and they are different measurements —
                                not a disagreement. The Daily Brief reports the count of{' '}
                                <strong>distinct outlet domains seen in the raw 24-hour feed</strong> (~62,000 at its
                                measurement), which includes the GDELT firehose's long tail of domains; firehose rows
                                carry no language or ownership metadata (see Measured limits). The attributable-source
                                count in this page's header is a narrower base: distinct sources among{' '}
                                <strong>attributable rows only</strong> — signals carrying language/origin metadata,
                                the same base every voice-mix and diversity measurement runs on. Same window, different
                                denominators, roughly 6× apart. Wherever a source count appears, its label names the
                                base; a raw-feed domain count and an attributable-source count should never be compared
                                directly.
                            </p>
                            <h3>From signal to thread</h3>
                            <p>
                                Every headline is embedded with a multilingual model, so a Persian and an English article
                                about the same event land near each other with no shared keywords. Clustering runs over
                                the persisted embedding corpus — globally and in per-country scoped passes, because a
                                single global pass drowns regional stories. Surviving clusters become living threads with
                                lifecycle: they persist, accumulate history, retire when quiet, and resurrect on a
                                centroid match rather than being re-founded.
                            </p>
                            <p>
                                The hot store holds a rolling ~7-day window (about 930,000 signals at the 2026-07-15
                                measurement); an external archive preserves history back to early May 2026 and backs the
                                day-by-day replay and archived evidence samples in the Console.
                            </p>
                        </section>

                        {/* METHOD */}
                        <section id="method" aria-labelledby="method-h">
                            <p className="docs-eyebrow">Method</p>
                            <h2 id="method-h">Method principles</h2>
                            <p className="docs-lead">
                                Six rules govern every surface. They exist because each one closes a specific way a
                                news dashboard can quietly lie.
                            </p>

                            <div className="docs-principle" id="p-measured">
                                <h3>Measured, not editorialized</h3>
                                <p>
                                    Numbers come from counting and math — signal counts, entropies, cosine similarities,
                                    z-scores — never from a model's opinion of what matters. Language models are used in
                                    exactly two narrow places: labeling a cluster with a human-readable name, and typing a
                                    thread's category from its evidence. Both outputs are decorations on measured structure;
                                    neither decides what you see or in what order.
                                </p>
                            </div>

                            <div className="docs-principle" id="p-heat">
                                <h3>Heat is a composite anomaly, not volume</h3>
                                <p>
                                    A country's map color is not its article count — by raw volume the United States would
                                    be permanently red and the map would be a population-of-newsrooms chart. Heat is a
                                    composite of measured components, each compared against that country's <em>own</em>{' '}
                                    recent baseline: velocity z-score, distributional surprise, source diversity, local-voice
                                    ratio, polyphony, geo-confidence, and a duplication penalty.
                                </p>
                                <p>
                                    That is why Côte d'Ivoire or Botswana can outrank the United States on a given day: 30
                                    signals in a country that normally produces 9 is a real anomaly; 25,000 in one that
                                    always produces 25,000 is not. Raw volume is still shown — as evidence density, labeled
                                    as volume.
                                </p>
                            </div>

                            <div className="docs-principle plum" id="p-lens">
                                <h3>Lens, not gate — nothing is dropped</h3>
                                <p>
                                    Filtering in Atlas is always inspectable, never silent. Ranking carries reason codes;
                                    a downranking ledger reconciles exactly (candidate → shown → downranked → omitted);
                                    low-confidence material moves to a tray you can open, not to a void.
                                </p>
                                <p>
                                    <strong>Farándula included.</strong> Sports, entertainment, and lifestyle coverage —
                                    the World Cup, a hotel review that went viral, celebrity news — are a real and large
                                    part of world coverage. Atlas does not delete them; they are classified into their own
                                    lane, damped in crisis-oriented rankings, and kept visible under Culture, Sport &amp;
                                    Life. A system that silently removed them would be lying about what the world's press
                                    actually publishes — and would miss the moments when entertainment coverage <em>is</em>{' '}
                                    the story.
                                </p>
                            </div>

                            <div className="docs-principle ochre" id="p-tiers">
                                <h3>Verified vs UNVERIFIED — two tiers, always labeled</h3>
                                <p>
                                    A quality gate scores every signal-to-thread assignment. <span className="docs-chip-ver">Verified</span>{' '}
                                    counts come from assignments the gate kept at its high-precision threshold.{' '}
                                    <span className="docs-chip-unv">Extended</span> coverage — material above a looser, explicitly
                                    stated threshold — is served separately and labeled with its approximate precision.
                                    When a thread has raw coverage but nothing cleared the gate, Atlas shows the raw
                                    headlines under an <span className="docs-chip-unv">Unverified</span> banner instead of showing
                                    nothing: hiding real relevant coverage because a classifier was strict would be its own
                                    kind of dishonesty.
                                </p>
                                <p>
                                    Forum and social content is UNVERIFIED by construction, permanently — it is commentary
                                    about coverage, not coverage.
                                </p>
                            </div>

                            <div className="docs-principle" id="p-geo">
                                <h3>Coverage geography is not subject geography</h3>
                                <p>
                                    When Atlas says "132,375 signals across 221 countries" (a 2026-07-15 measurement),
                                    that measures where coverage points and comes from — the countries named in and
                                    publishing the articles. It is not a
                                    claim about where events physically happened, and the two can diverge: a story about
                                    Iran written entirely by British outlets is Iranian subject-geography with zero Iranian
                                    voice. Atlas measures that distinction explicitly (self-voice by outlet <em>ownership</em>,
                                    not language) instead of letting the map imply local knowledge that isn't there.
                                </p>
                            </div>

                            <div className="docs-principle" id="p-empty">
                                <h3>Honest empties</h3>
                                <p>
                                    A country with signals but no coherent thread shows "0 threads" with an explanation —
                                    never a fallback padded with generic category volume. A research lane that finds nothing
                                    emits a coverage-gap note instead of failing silently. The Brief's "what is missing" box
                                    is built from exactly these gaps: categories with real raw coverage where nothing
                                    cleared the gate. In Atlas, an absence is a finding, and it is reported like one.
                                </p>
                            </div>
                        </section>

                        {/* LIMITS */}
                        <section id="limits" aria-labelledby="limits-h" className="docs-sec-ochre">
                            <p className="docs-eyebrow">Honesty</p>
                            <h2 id="limits-h">Measured limits</h2>
                            <p className="docs-lead">
                                These are the known ceilings, stated with the numbers that measure them. They move as the
                                system grows, but they are never pretended away.
                            </p>
                            <ul>
                                <li>
                                    <strong>English-heavy input.</strong> Of language-known signals in the measured 24 h
                                    window (2026-07-15), <strong>83.3% are English</strong>; 48 languages are present and
                                    CJK holds ~4% of the known-language mix. About half of all signals carry no language
                                    metadata at all (the GDELT firehose does not provide it). The native RSS network and
                                    multilingual embeddings widen this, but English is a real lingua franca and the
                                    diversity score (40.1/100 at measurement) climbs and plateaus rather than reaching 100.
                                </li>
                                <li>
                                    <strong>Clustering covers a fraction of the feed.</strong> Living threads are formed
                                    from the coherent, recurring part of the corpus — a large share of raw signals remain
                                    honest noise that never joins a thread. Thin substrate produces short lists; Atlas
                                    serves a short honest list rather than padding it.
                                </li>
                                <li>
                                    <strong>Archive window.</strong> The hot, fully-queryable store is a rolling ~7 days.
                                    The external archive extends to early May 2026 with day-level replay and sampled
                                    evidence (a few headlines per country-day, labeled "from the archive"), not full
                                    re-query. Anything before May 2026 does not exist in Atlas.
                                </li>
                                <li>
                                    <strong>Labels lag embeddings.</strong> Threading and semantic search are
                                    language-agnostic, but the labeling layer (sentiment, named entities) is English-first;
                                    non-English entities are typed by a gazetteer and flagged unverified rather than
                                    asserted.
                                </li>
                                <li>
                                    <strong>Attention feeds are uneven.</strong> Google Trends availability varies by
                                    country and the feed can be hours stale; Wikipedia pageviews are daily. Both are
                                    labeled with their freshness where shown.
                                </li>
                            </ul>
                            <div className="docs-callout warn">
                                <p><strong>What Atlas cannot tell you:</strong> whether a story is true, whether it is
                                    important, or what will happen next. It can tell you — with receipts — who is covering
                                    it, from where, in which languages, how that is changing, and who is silent. The judgment
                                    is yours; Atlas's job is to make sure you make it on measured ground.</p>
                            </div>
                        </section>

                        {/* FAQ */}
                        <section id="faq" aria-labelledby="faq-h" className="docs-faq">
                            <p className="docs-eyebrow">Questions</p>
                            <h2 id="faq-h">Honest FAQ</h2>

                            <details>
                                <summary>Is Atlas a news site?</summary>
                                <p>No. Atlas never writes or rewrites news. Every headline shown is a real published
                                    headline linking to its source outlet. Atlas's own output is measurement: counts,
                                    movement, diversity, gaps, and the connections between stories.</p>
                            </details>

                            <details>
                                <summary>Why does a huge story show only a handful of verified articles?</summary>
                                <p>The verified count is what cleared a high-precision quality gate, which is deliberately
                                    strict — especially on non-English and ambiguous coverage. The raw and extended tiers are
                                    always available and labeled. A small verified number next to a large raw number is the
                                    system telling you its own confidence, not the story's size.</p>
                            </details>

                            <details>
                                <summary>Why is my country dark on the map when there's plenty of news?</summary>
                                <p>Map heat is anomaly against that country's own baseline, not volume. A country having
                                    its normal amount of coverage — even a lot of it — reads as calm. It lights up when
                                    coverage departs from its own recent pattern. If a country has too few signals to measure
                                    at all, that shows as an honest empty, not manufactured heat.</p>
                            </details>

                            <details>
                                <summary>Can I trust the sentiment numbers?</summary>
                                <p>Treat sentiment as a noisy contextual indicator, not a verdict. It should be read
                                    alongside signal count, source diversity, and the underlying headlines. Where the score
                                    comes from a model rather than the wire feed, the provenance is badged.</p>
                            </details>

                            <details>
                                <summary>Where do my pins and investigations live?</summary>
                                <p>In your browser's local storage. The server records only anonymous usage events; your
                                    investigation content — pins, notes, dossiers — never leaves your device unless you
                                    export it yourself as JSON or markdown. The trade-off is honest too: pins do not sync
                                    between devices.</p>
                            </details>

                            <details>
                                <summary>Why do the numbers change between visits?</summary>
                                <p>Atlas is a living system over a rolling window. Threads form, grow, retire, and
                                    resurrect as coverage moves; the hot store advances daily. That is why the Workbench
                                    freezes snapshots at pin time — so the evidence in your dossier stays what it was when
                                    you cited it, even after the live numbers move on.</p>
                            </details>
                        </section>

                        <footer className="docs-footer">
                            <span className="docs-footer-mono">ATLAS DOCUMENTATION · numbers in the header marked
                                "measured" are from the live API at page load; dated figures in the prose name their
                                measurement date (feed-network figures are the 2026-06-23 baseline). Where a figure could
                                not be verified against the live system, it does not appear on this page.</span>
                        </footer>

                    </main>
                </div>
            </div>
        </div>
    )
}
