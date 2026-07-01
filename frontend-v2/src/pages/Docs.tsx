import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './Docs.css'

const NAV = [
    { id: 'overview', label: 'Overview' },
    {
        id: 'panel-guide', label: 'Panel Guide', children: [
            { id: 'globe-panel', label: 'Globe' },
            { id: 'signal-stream-panel', label: 'Signal Stream' },
            { id: 'public-attention-panel', label: 'Public Attention' },
            { id: 'source-integrity-panel', label: 'Source Integrity' },
        ]
    },
    {
        id: 'methodology', label: 'Methodology', children: [
            { id: 'coverage-methodology', label: 'Coverage Bias' },
            { id: 'sentiment-methodology', label: 'Sentiment' },
            { id: 'multilingual-methodology', label: 'Multilingual NLP' },
        ]
    },
    { id: 'use-cases', label: 'Use Cases' },
    {
        id: 'data-sources', label: 'Data Sources', children: [
            { id: 'gdelt-gkg', label: 'GDELT GKG' },
            { id: 'gdelt-events', label: 'GDELT Events' },
            { id: 'news-apis', label: 'News APIs' },
            { id: 'social', label: 'Social & Forums' },
            { id: 'google-trends', label: 'Google Trends' },
            { id: 'wikipedia', label: 'Wikipedia' },
        ]
    },
    { id: 'signal-pipeline', label: 'Signal Pipeline' },
    { id: 'narrative-threads', label: 'Narrative Threads' },
    { id: 'research-workflow', label: 'Research Workflow' },
    { id: 'cross-source', label: 'Cross-Source Intelligence' },
    { id: 'voice-coverage', label: 'Voice & Coverage' },
    { id: 'the-math', label: 'The Math' },
    { id: 'research-validation', label: 'Research & Validation' },
    { id: 'api-reference', label: 'API Reference' },
]

export function Docs() {
    const navigate = useNavigate()
    const [activeId, setActiveId] = useState('overview')
    const mainRef = useRef<HTMLDivElement>(null)

    // Scroll-spy: update active nav item based on scroll position
    useEffect(() => {
        const observer = new IntersectionObserver(
            (entries) => {
                for (const entry of entries) {
                    if (entry.isIntersecting) {
                        setActiveId(entry.target.id)
                    }
                }
            },
            { rootMargin: '-20% 0px -70% 0px', threshold: 0 }
        )
        document.querySelectorAll('.docs-section[id]').forEach(el => observer.observe(el))
        return () => observer.disconnect()
    }, [])

    const scrollTo = (id: string) => {
        document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }

    return (
        <div className="docs-root">
            {/* Top nav */}
            <nav className="docs-topnav">
                <a className="docs-brand" href="/" onClick={e => { e.preventDefault(); navigate('/') }}>
                    <span className="docs-brand-dot" />
                    ATLAS
                </a>
                <span style={{ fontSize: '12px', color: '#334155', fontFamily: 'JetBrains Mono, monospace' }}>/</span>
                <span style={{ fontSize: '12px', color: '#64748b' }}>Documentation</span>
                <div className="docs-topnav-links">
                    <a onClick={() => navigate('/app')} style={{ cursor: 'pointer' }}>Dashboard</a>
                    <a href="https://github.com/pedro-cmyks/Observatory-Global" target="_blank" rel="noopener noreferrer">GitHub</a>
                </div>
            </nav>

            {/* Sidebar */}
            <aside className="docs-sidebar">
                {NAV.map(item => (
                    <div key={item.id} className="docs-nav-section">
                        <button
                            className={`docs-nav-item ${activeId === item.id ? 'active' : ''}`}
                            onClick={() => scrollTo(item.id)}
                        >
                            {item.label}
                        </button>
                        {item.children && (
                            <div className="docs-nav-sub">
                                {item.children.map(child => (
                                    <button
                                        key={child.id}
                                        className={`docs-nav-item ${activeId === child.id ? 'active' : ''}`}
                                        onClick={() => scrollTo(child.id)}
                                    >
                                        {child.label}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                ))}
            </aside>

            {/* Main content */}
            <main className="docs-main" ref={mainRef}>

                {/* ── Overview ── */}
                <section className="docs-section" id="overview">
                    <div className="docs-section-eyebrow">Introduction</div>
                    <h2>How Atlas Works</h2>
                    <p className="docs-lead">
                        Atlas is a narrative intelligence engine. It doesn't track news — it tracks how topics spread,
                        mutate, and polarize across global media sources. The signal isn't <em>what</em> happened,
                        it's <em>how the world is talking about it</em>.
                    </p>
                    <p>
                        Most geopolitical dashboards show you a live feed of events. Atlas shows you something harder
                        to see: the statistical shape of a narrative over time, across countries, across source families.
                        When a story accelerates in three countries but stalls in two others, that asymmetry is intelligence.
                    </p>
                    <div className="docs-callout">
                        <strong>Core insight:</strong> A narrative that appears simultaneously in media signals,
                        regional/non-English sources, social commentary, Google searches, and Wikipedia reading
                        has crossed independent signal layers. That convergence is stronger than one outlet or one
                        country flooding the global feed.
                    </div>
                    <h3>What Atlas ingests</h3>
                    <table className="docs-table">
                        <thead>
                            <tr>
                                <th>Source</th>
                                <th>Signal type</th>
                                <th>Cadence</th>
                                <th>Coverage</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td>GDELT GKG 2.0</td><td>Media narratives, themes, sentiment, persons</td><td>15 min</td><td>Global, multilingual baseline</td></tr>
                            <tr><td>GDELT Events</td><td>Actor-action geopolitical events using CAMEO</td><td>15 min</td><td>Global</td></tr>
                            <tr><td>RSS / ReliefWeb</td><td>Curated regional, humanitarian, NGO, institutional feeds</td><td>60 min</td><td>Source provenance and crisis-country context</td></tr>
                            <tr><td>NewsData.io</td><td>Multilingual media coverage expansion</td><td>60 min</td><td>Language and country buckets</td></tr>
                            <tr><td>MediaStack</td><td>Country-specific media expansion</td><td>2 h</td><td>LatAm and regional coverage</td></tr>
                            <tr><td>NewsAPI.org</td><td>Targeted crisis-query coverage</td><td>2 h</td><td>Focused crisis monitoring</td></tr>
                            <tr><td>Reddit</td><td>Public social commentary from geopolitical subreddits</td><td>60 min</td><td>Commentary layer, not news evidence</td></tr>
                            <tr><td>Bluesky</td><td>Public social posts via the Jetstream firehose</td><td>~60 min</td><td>Global social commentary, multilingual</td></tr>
                            <tr><td>Lemmy</td><td>Federated forum posts across public instances</td><td>~60 min</td><td>Instance-tagged social commentary</td></tr>
                            <tr><td>Google Trends</td><td>Public search interest by keyword and country</td><td>30 min</td><td>Availability varies by country</td></tr>
                            <tr><td>Wikipedia Pageviews</td><td>Article reading volume by language/country</td><td>24 h</td><td>Reference-seeking public attention</td></tr>
                        </tbody>
                    </table>
                </section>

                <hr className="docs-divider" />

                {/* ── Panel Guide ── */}
                <section className="docs-section" id="panel-guide">
                    <div className="docs-section-eyebrow">Console Manual</div>
                    <h2>Panel Guide</h2>
                    <p className="docs-lead">
                        Atlas has a readable Brief for orientation and a console for investigation. The console panels
                        are connected: a click in one panel should give you a next step in another panel or the Workspace.
                    </p>
                    <div className="docs-source-grid">
                        <div className="docs-source-card" id="globe-panel">
                            <div className="docs-source-card-head">
                                <span className="docs-source-badge badge-gdelt">MAP</span>
                                <span className="docs-source-title">Globe</span>
                            </div>
                            <p>
                                The Globe is the orientation layer. The Heat layer colors each country by a composite
                                anomaly score (velocity, surprise, source diversity, local voice) relative to its own
                                recent baseline — not raw volume. Raw signal volume adds evidence density (border
                                thickness), but it is not read as direct real-world importance.
                            </p>
                        </div>
                        <div className="docs-source-card" id="signal-stream-panel">
                            <div className="docs-source-card-head">
                                <span className="docs-source-badge badge-wiki">STREAM</span>
                                <span className="docs-source-title">Signal Stream</span>
                            </div>
                            <p>
                                The stream is the default investigation entry. It is a pivot engine: click a country,
                                theme, person, source, or headline to turn a raw signal into a focused panel.
                            </p>
                        </div>
                        <div className="docs-source-card" id="public-attention-panel">
                            <div className="docs-source-card-head">
                                <span className="docs-source-badge badge-trends">ATTN</span>
                                <span className="docs-source-title">Public Attention</span>
                            </div>
                            <p>
                                Public Attention is the counterpart to media signals. It captures what people are
                                reading or searching where those feeds are available, then provides pivots into
                                countries, themes, and narrative threads.
                            </p>
                        </div>
                        <div className="docs-source-card" id="source-integrity-panel">
                            <div className="docs-source-card-head">
                                <span className="docs-source-badge badge-events">SRC</span>
                                <span className="docs-source-title">Source Integrity</span>
                            </div>
                            <p>
                                Source Integrity checks whether coverage is broad or concentrated. A high concentration
                                score is a warning to inspect which publishers are dominating a country or theme.
                            </p>
                        </div>
                    </div>
                    <div className="docs-callout" id="correlation-panel">
                        <strong>Correlation Matrix:</strong> use this as a lead generator. Bright cells indicate shared
                        narrative coverage, not agreement or causality.
                    </div>
                </section>

                <hr className="docs-divider" />

                {/* ── Methodology ── */}
                <section className="docs-section" id="methodology">
                    <div className="docs-section-eyebrow">Interpretation</div>
                    <h2>Methodology Notes</h2>
                    <p className="docs-lead">
                        Atlas should make coverage bias visible instead of hiding it. The product separates signal
                        volume, normalized activity, source concentration, and public attention so one metric does not
                        overrule the others.
                    </p>
                    <div className="docs-callout" id="coverage-methodology">
                        <strong>Coverage bias:</strong> countries with more open-source media produce more raw signals.
                        Atlas can use that volume as more evidence, but map heat and narrative ranking should be
                        compared against each country's own baseline whenever possible.
                    </div>
                    <div className="docs-callout" id="sentiment-methodology">
                        <strong>Sentiment:</strong> sentiment is a noisy contextual indicator. It should be read with
                        signal count, source diversity, country spread, and the underlying headlines before drawing an
                        analytic conclusion.
                    </div>
                    <div className="docs-callout" id="multilingual-methodology">
                        <strong>Multilingual NLP:</strong> the language-agnostic layer is the embedding model — a
                        multilingual e5 encoder embeds every signal regardless of language, so recall, threading,
                        and semantic neighbors already work across CJK, Russian, Persian, and Arabic (see
                        Cross-Source Intelligence). The <em>labeling</em> layer (sentiment, entities, framing) is
                        currently English-first: RoBERTa sentiment and spaCy NER run on English signals, and
                        non-English entities are typed by a multilingual gazetteer and flagged
                        <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}> unverified</code> rather than
                        asserted. Full cross-lingual NLP labeling (an XLM path) is gated on worker throughput and a
                        non-Latin NER model — not on by default today. NLP is an enrichment layer, never ground truth.
                    </div>
                </section>

                <hr className="docs-divider" />

                {/* ── Use Cases ── */}
                <section className="docs-section" id="use-cases">
                    <div className="docs-section-eyebrow">Applied Flows</div>
                    <h2>Use Cases</h2>
                    <p className="docs-lead">
                        Atlas is most useful when a user moves from orientation into evidence. These are the core
                        workflows the product is being shaped around.
                    </p>
                    <div className="docs-source-grid">
                        <div className="docs-source-card">
                            <div className="docs-source-card-head">
                                <span className="docs-source-badge badge-gdelt">JOURNALIST</span>
                                <span className="docs-source-title">Build an investigation dossier</span>
                            </div>
                            <p>
                                Start in Brief, open a country or theme in the console, pin relevant countries,
                                sources, people, and signals, then export a Workspace dossier with notes and evidence.
                            </p>
                        </div>
                        <div className="docs-source-card">
                            <div className="docs-source-card-head">
                                <span className="docs-source-badge badge-events">RISK</span>
                                <span className="docs-source-title">Monitor drift before it becomes obvious</span>
                            </div>
                            <p>
                                Use country heat, narrative velocity, sentiment drift, and source concentration to
                                watch whether a country is moving away from its own baseline.
                            </p>
                        </div>
                        <div className="docs-source-card">
                            <div className="docs-source-card-head">
                                <span className="docs-source-badge badge-trends">READER</span>
                                <span className="docs-source-title">Understand why a topic is visible</span>
                            </div>
                            <p>
                                Compare media coverage with search and Wikipedia attention. A topic that appears in
                                all three layers is different from a topic amplified by one source family.
                            </p>
                        </div>
                    </div>
                </section>

                <hr className="docs-divider" />

                {/* ── Data Sources ── */}
                <section className="docs-section" id="data-sources">
                    <div className="docs-section-eyebrow">Feeds</div>
                    <h2>Data Sources</h2>
                    <p className="docs-lead">
                        Each source captures a different dimension of how a topic exists in the world.
                        No single source is sufficient — the intelligence emerges from their convergence.
                    </p>
                    <div className="docs-source-grid">
                        <div className="docs-source-card">
                            <div className="docs-source-card-head">
                                <span className="docs-source-badge badge-gdelt">GDELT GKG</span>
                                <span className="docs-source-title">Global Knowledge Graph</span>
                            </div>
                            <p>
                                The core feed. GDELT processes every major news outlet globally and extracts
                                structured events, themes, sentiment, named persons, and geographic locations.
                                Atlas uses the V2 GKG file published every 15 minutes.
                            </p>
                            <div className="docs-source-meta">
                                <div className="docs-source-meta-item">Latency <span>~15 min</span></div>
                                <div className="docs-source-meta-item">Table <span>signals_v2</span></div>
                            </div>
                        </div>
                        <div className="docs-source-card">
                            <div className="docs-source-card-head">
                                <span className="docs-source-badge badge-events">GDELT Events</span>
                                <span className="docs-source-title">CAMEO Event Codes</span>
                            </div>
                            <p>
                                Extracts Actor1 → Action → Actor2 triples using the CAMEO taxonomy (300+ event types:
                                diplomatic, military, economic). These feed the Signal Stream as geopolitical
                                event cards alongside GKG articles.
                            </p>
                            <div className="docs-source-meta">
                                <div className="docs-source-meta-item">Latency <span>~15 min</span></div>
                                <div className="docs-source-meta-item">Table <span>events_v2</span></div>
                            </div>
                        </div>
                        <div className="docs-source-card">
                            <div className="docs-source-card-head">
                                <span className="docs-source-badge badge-trends">Google Trends</span>
                                <span className="docs-source-title">Public Search Interest</span>
                            </div>
                            <p>
                                Measures what people are actively searching for. When a GDELT narrative theme
                                also appears in Google Trends, it means the story has crossed from media
                                coverage into public awareness. This triggers the <strong>SEARCH</strong> badge.
                            </p>
                            <div className="docs-source-meta">
                                <div className="docs-source-meta-item">Latency <span>~30 min</span></div>
                                <div className="docs-source-meta-item">Table <span>trends_v2</span></div>
                            </div>
                        </div>
                        <div className="docs-source-card">
                            <div className="docs-source-card-head">
                                <span className="docs-source-badge badge-wiki">Wikipedia</span>
                                <span className="docs-source-title">Encyclopedia Pageviews</span>
                            </div>
                            <p>
                                Tracks which articles are being read heavily across language editions.
                                Wikipedia activity indicates that a topic has reached the level where
                                people seek reference knowledge — a signal of narrative entrenchment.
                                Triggers the <strong>WIKI</strong> badge.
                            </p>
                            <div className="docs-source-meta">
                                <div className="docs-source-meta-item">Latency <span>24 h</span></div>
                                <div className="docs-source-meta-item">Table <span>wiki_pageviews_v2</span></div>
                            </div>
                        </div>
                        <div className="docs-source-card">
                            <div className="docs-source-card-head">
                                <span className="docs-source-badge badge-acled">RSS</span>
                                <span className="docs-source-title">Curated + ReliefWeb Feeds</span>
                            </div>
                            <p>
                                Curated feeds add regional, state, NGO, and humanitarian sources with stronger
                                provenance. ReliefWeb/OCHA coverage is especially useful for crisis-country context.
                            </p>
                            <div className="docs-source-meta">
                                <div className="docs-source-meta-item">Latency <span>~60 min</span></div>
                                <div className="docs-source-meta-item">Table <span>signals_v2</span></div>
                            </div>
                        </div>
                        <div className="docs-source-card">
                            <div className="docs-source-card-head">
                                <span className="docs-source-badge badge-gdelt">NEWS</span>
                                <span className="docs-source-title">NewsData / MediaStack / NewsAPI</span>
                            </div>
                            <p>
                                Additional media APIs improve voice diversity and crisis-specific coverage. These
                                feeds matter most when they add local-language or region-specific sources that GDELT
                                does not surface prominently.
                            </p>
                            <div className="docs-source-meta">
                                <div className="docs-source-meta-item">Latency <span>60-120 min</span></div>
                                <div className="docs-source-meta-item">Table <span>signals_v2</span></div>
                            </div>
                        </div>
                        <div className="docs-source-card">
                            <div className="docs-source-card-head">
                                <span className="docs-source-badge badge-wiki">SOCIAL</span>
                                <span className="docs-source-title">Reddit Commentary</span>
                            </div>
                            <p>
                                Reddit is treated as commentary, not as article evidence. It can reveal early public
                                discussion, but it should be scored separately from media and institutional sources.
                            </p>
                            <div className="docs-source-meta">
                                <div className="docs-source-meta-item">Latency <span>~60 min</span></div>
                                <div className="docs-source-meta-item">Class <span>commentary</span></div>
                            </div>
                        </div>
                        <div className="docs-source-card">
                            <div className="docs-source-card-head">
                                <span className="docs-source-badge badge-wiki">SOCIAL</span>
                                <span className="docs-source-title">Bluesky Firehose</span>
                            </div>
                            <p>
                                Public Bluesky posts are drained from the Jetstream firehose (no credentials, one
                                global network). Country is inferred by NER geocode and language from the post's own
                                tag. Like Reddit it is commentary — it attaches to threads as discussion, never as
                                article evidence, and never seeds a cluster.
                            </p>
                            <div className="docs-source-meta">
                                <div className="docs-source-meta-item">Latency <span>~60 min</span></div>
                                <div className="docs-source-meta-item">Class <span>commentary</span></div>
                            </div>
                        </div>
                        <div className="docs-source-card">
                            <div className="docs-source-card-head">
                                <span className="docs-source-badge badge-wiki">SOCIAL</span>
                                <span className="docs-source-title">Lemmy Instances</span>
                            </div>
                            <p>
                                Federated forum posts are pulled from public Lemmy instances, with each instance mapped
                                to a source origin country (the same ownership model used for news feeds). Also
                                commentary: embedded and attached as discussion, kept out of cluster seeding.
                            </p>
                            <div className="docs-source-meta">
                                <div className="docs-source-meta-item">Latency <span>~60 min</span></div>
                                <div className="docs-source-meta-item">Class <span>commentary</span></div>
                            </div>
                        </div>
                    </div>
                </section>

                <section className="docs-section" id="gdelt-gkg">
                    <h3>GDELT GKG — Field Mapping</h3>
                    <p>
                        Each GKG record is a news article. Atlas extracts the following fields from the V2 GKG
                        tab-separated format and normalizes them into <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>signals_v2</code>:
                    </p>
                    <table className="docs-table">
                        <thead><tr><th>GKG Field</th><th>Column Index</th><th>Atlas Field</th><th>Notes</th></tr></thead>
                        <tbody>
                            <tr><td>DATE</td><td>0</td><td>timestamp</td><td>YYYYMMDDHHMMSS → UTC</td></tr>
                            <tr><td>V2ENHANCEDLOCATIONS</td><td>10</td><td>country_code, lat, lon</td><td>FIPS → ISO 3166 conversion applied</td></tr>
                            <tr><td>V2ENHANCEDTHEMES</td><td>8</td><td>themes[]</td><td>Up to 10 themes per signal</td></tr>
                            <tr><td>V2ENHANCEDPERSONS</td><td>12</td><td>persons[]</td><td>Up to 10 persons per signal</td></tr>
                            <tr><td>V2TONE</td><td>15</td><td>sentiment</td><td>First component of tone vector</td></tr>
                            <tr><td>V2EXTRASXML PAGE_TITLE</td><td>26</td><td>headline</td><td>Falls back to URL slug if absent</td></tr>
                        </tbody>
                    </table>
                    <p>
                        Country codes in GDELT use FIPS 10-4, not ISO 3166. Atlas applies a full FIPS→ISO
                        lookup table on ingest so all downstream queries use standard ISO codes.
                    </p>
                </section>

                <section className="docs-section" id="gdelt-events">
                    <h3>GDELT Events — CAMEO Taxonomy</h3>
                    <p>
                        The CAMEO (Conflict and Mediation Event Observations) taxonomy defines ~300 event types
                        organized in a tree: top-level categories (1 = Make Statement, 14 = Protest, 19 = Fight)
                        with 2–4 digit sub-codes for specificity.
                    </p>
                    <div className="docs-code">
                        <span className="cm">// Example CAMEO codes in events_v2</span>
                        {`
"14"    → Protest
"145"   → Protest violently
"19"    → Fight
"1823"  → Physically assault   (prefix fallback: 182 → "Physically assault")
"193"   → Fight with small arms
"020"   → Make an appeal
`}
                    </div>
                    <p>
                        Atlas uses prefix fallback for 4-digit sub-codes not in the top-level dictionary:
                        if code "1823" isn't found, it tries "182", then "18", returning the closest parent label.
                        This prevents events showing "Action 1823" when a readable label exists at a higher level.
                    </p>
                </section>

                <section className="docs-section" id="google-trends">
                    <h3>Google Trends — Public Interest Signal</h3>
                    <p>
                        Google Trends data is ingested from the public RSS feed
                        <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>trends.google.com/trending/rss</code>
                        every 30 minutes across 50+ country codes. Each record stores the keyword, its rank,
                        approximate search volume, and the country. The Anomaly Panel's right column shows the
                        top globally-trending keywords (ranked by how many countries searched for the same term).
                    </p>
                    <p>
                        At the narrative thread level, Atlas performs a semantic match: it extracts meaningful
                        words from each GDELT theme label and checks whether any match trending keywords
                        via partial string overlap. A match sets <code style={{ fontFamily: 'monospace', color: '#4ade80' }}>has_public_interest: true</code> and
                        displays the SEARCH badge on that thread.
                    </p>
                </section>

                <section className="docs-section" id="wikipedia">
                    <h3>Wikipedia Pageviews — Entrenchment Signal</h3>
                    <p>
                        Wikipedia pageview data is fetched daily via the Wikimedia REST API for the top 50
                        articles per country/language. It serves a different role than Trends:
                        while Trends measures <em>fleeting curiosity</em>, Wikipedia pageviews indicate
                        a topic has reached <em>reference-seeking behavior</em> — people want to understand
                        the background, context, and history. This is a signal of narrative entrenchment.
                    </p>
                    <p>
                        The WIKI badge on a narrative thread means that the theme's label words appear
                        in highly-read Wikipedia article titles within the last 3 days.
                    </p>
                </section>

                <section className="docs-section" id="news-apis">
                    <h3>News APIs — Voice Diversity Layer</h3>
                    <p>
                        NewsData.io, MediaStack, and NewsAPI.org add a second media layer around GDELT. The point is
                        not raw volume; it is voice diversity, local-language coverage, and targeted crisis monitoring.
                    </p>
                    <div className="docs-callout">
                        <strong>Method note:</strong> additional news APIs should be evaluated by what they add to
                        source mix, country coverage, language mix, and local voice ratio. More rows are only useful
                        when they reduce blind spots or improve confidence.
                    </div>
                </section>

                <section className="docs-section" id="social">
                    <h3>Social &amp; Forums — Commentary Signal</h3>
                    <p>
                        Three social layers feed Atlas as <em>commentary</em>, never article evidence: Reddit
                        (geopolitical and country subreddits), Bluesky (the Jetstream firehose), and Lemmy (federated
                        forum instances). All three are embedded with the same multilingual model as news, then
                        attached to narrative threads with a <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>discussion</code> role
                        so social attention is scored separately and does not contaminate media-source scoring.
                    </p>
                    <p>
                        A clustering guard keeps social signals out of thread <em>seeding</em> — they can join and
                        discuss a thread, but a topic is never created from social posts alone. The useful pattern is
                        early movement: a theme surfacing in discussion before media can become an investigation lead,
                        but it still needs corroboration from media, public-attention, or institutional sources before
                        it is treated as evidence.
                    </p>
                </section>

                <hr className="docs-divider" />

                {/* ── Signal Pipeline ── */}
                <section className="docs-section" id="signal-pipeline">
                    <div className="docs-section-eyebrow">Architecture</div>
                    <h2>Signal Pipeline</h2>
                    <p className="docs-lead">
                        Atlas receives signals from file feeds, APIs, RSS, and public-attention endpoints. Every
                        source is normalized into shared signal fields before enrichment, aggregation, and user-facing
                        views.
                    </p>
                    <div className="docs-pipeline">
                        <div className="docs-pipeline-step">
                            <div className="docs-pipeline-num">01</div>
                            <div className="docs-pipeline-step-body">
                                <h4>Fetch</h4>
                                <p>
                                    GDELT files, RSS feeds, news APIs, Reddit JSON, Trends, and Wikipedia are fetched
                                    on their own cadences. Source family, language, attribution method, and confidence
                                    metadata are attached as early as possible.
                                </p>
                            </div>
                        </div>
                        <div className="docs-pipeline-step">
                            <div className="docs-pipeline-num">02</div>
                            <div className="docs-pipeline-step-body">
                                <h4>Parse & Normalize</h4>
                                <p>
                                    Rows and API objects are converted into shared country, source, URL, headline,
                                    timestamp, theme, source-family, language, and geo-confidence fields. GDELT FIPS
                                    codes are converted to ISO 3166 for downstream consistency.
                                </p>
                            </div>
                        </div>
                        <div className="docs-pipeline-step">
                            <div className="docs-pipeline-num">03</div>
                            <div className="docs-pipeline-step-body">
                                <h4>Insert into signals_v2</h4>
                                <p>
                                    Parsed signals are batch-inserted with <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>ON CONFLICT DO NOTHING</code> (deduplication
                                    by source URL and timestamp where available). The <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>themes</code> column
                                    stores a PostgreSQL <code style={{ fontFamily: 'monospace' }}>text[]</code> array with a GIN index
                                    enabling fast <code style={{ fontFamily: 'monospace' }}>&&</code> array-overlap queries.
                                </p>
                            </div>
                        </div>
                        <div className="docs-pipeline-step">
                            <div className="docs-pipeline-num">04</div>
                            <div className="docs-pipeline-step-body">
                                <h4>Enrich & Aggregate</h4>
                                <p>
                                    NLP enrichment adds sentiment, entities, framing, language, method, and confidence
                                    metadata, and a multilingual e5 model writes a semantic embedding per signal. A
                                    clustering job then groups those embeddings into living narrative threads.
                                    Aggregates power threads, country brief views, and country heat without repeatedly
                                    scanning raw rows.
                                </p>
                            </div>
                        </div>
                    </div>
                    <h3>Database schema overview</h3>
                    <div className="docs-code">
                        {`signals_v2           Raw normalized signals and source provenance
events_v2            GDELT CAMEO actor-action-actor events
dynamic_topics       Living narrative threads (clustered signals)
emergent_clusters    Raw clustering snapshots behind dynamic_topics
signal_embeddings    Per-signal e5 vectors for semantic search/neighbors (pgvector)
signal_translations  Cached on-demand headline translations
trends_v2            Google Trends keywords by country
wiki_pageviews_v2    Wikipedia article views by country/language
country_heat_v2      Country heat view for normalized attention ranking
countries_v2         Country centroids and metadata`}
                    </div>
                </section>

                <hr className="docs-divider" />

                {/* ── Narrative Threads ── */}
                <section className="docs-section" id="narrative-threads">
                    <div className="docs-section-eyebrow">Intelligence Layer</div>
                    <h2>Narrative Threads</h2>
                    <p className="docs-lead">
                        A narrative thread is a <em>living topic</em> — a cluster of semantically related
                        signals that Atlas discovers by grouping message embeddings, not a fixed GDELT
                        theme code. Each thread is backed by a <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>dynamic_topics</code> record
                        and characterized by its volume, velocity, geographic spread, and sentiment
                        trajectory. A GDELT theme code is one input to a signal — never the identity of a thread.
                    </p>
                    <h3>How threads are formed</h3>
                    <p>
                        A clustering job groups signals by the similarity of their e5 text embeddings (HDBSCAN),
                        labels each surviving cluster, and writes it to
                        <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}> dynamic_topics</code>. A quality gate drops
                        incoherent clusters, and a content-entropy roundup classifier diverts
                        "miscellaneous regional news" buckets to a separate tray instead of the live list.
                    </p>
                    <p>
                        Clustering runs over the <strong>persisted embedding corpus</strong>, not just the most recent
                        rows, and in <strong>scoped per-country passes</strong> as well as globally. A single global
                        pass drowns regional stories; scoping the clustering to each country recovers narratives a
                        worldwide pass would bury — a local corruption probe, a national heatwave — and lets
                        non-English narratives surface as their own threads instead of being absorbed into English ones.
                    </p>
                    <h3>How threads are served</h3>
                    <p>
                        <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>/api/v2/threads</code> ranks dynamic and
                        atlas-topic threads together by a single relevance score — log-damped volume, relative
                        movement, and coherence — with <strong>no bias by origin</strong>. A persistent atlas topic
                        that keeps growing is a live thread and is not demoted just for being an aggregate; a loose
                        cluster is held back by the coherence term. (The older "dynamic first, then fill with atlas"
                        rule was retired in favor of this unified ranking.) Per-thread counts, velocity, and the
                        hourly sparkline are computed against pre-aggregated hourly tables and the GIN-indexed
                        <code style={{ fontFamily: 'monospace' }}> themes</code> array on
                        <code style={{ fontFamily: 'monospace' }}> signals_v2</code>, so any window from 1 hour to 7
                        days answers within the statement timeout.
                    </p>
                    <h3>Categories &amp; crisis relevance</h3>
                    <p>
                        Every thread carries an open <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>category</code>
                        (shown as a badge) and a <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>crisis_relevant</code>
                        flag. The category set is <em>anchored-emergent</em>: a seed set of crisis domains (armed
                        conflict, disaster, economic shock, and so on) anchors the taxonomy, but the set grows —
                        emergent non-crisis domains get their own categories rather than being force-fit. Typing is
                        done by an LLM reading each thread's evidence (embedding cosine alone proved unreliable), so
                        <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}> crisis_relevant</code> is an analyst
                        filter — narrow to crises, or keep the full picture — not a hidden gate.
                    </p>
                    <h3>Umbrella hierarchy</h3>
                    <p>
                        Related threads are grouped under <strong>umbrella</strong> topics (a centroid-of-centroids
                        clustering with complete linkage). The global list shows top-level items — umbrellas plus
                        standalone threads, de-duplicated — so one big story reads as one row; drilling in, or opening
                        a country view, expands the umbrella into its child threads
                        (<code style={{ fontFamily: 'monospace' }}>parent_id</code> /
                        <code style={{ fontFamily: 'monospace' }}> is_umbrella</code>). Umbrellas are rebuilt each pass,
                        so a country view surfaces the region-specific children a global row would otherwise hide.
                    </p>
                    <h3>Typed membership &amp; relationship</h3>
                    <p>
                        A thread's members are typed by role —
                        <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}> evidence</code> (media /
                        institutional), <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>discussion</code>
                        (social / forum), <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>mood</code>
                        (sentiment), and <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>movement</code>.
                        From the ratio of those roles Atlas classifies each thread's <em>relationship</em> — media-led,
                        public-led, social-led, silent-risk (public attention with thin media), or uncoupled — served
                        by <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>/api/v2/topic/{'{id}'}/relationship</code>.
                        These differentiate as social and public-attention volume grows; today most threads are
                        media-led.
                    </p>
                    <h3>Thread fields explained</h3>
                    <table className="docs-table">
                        <thead><tr><th>Field</th><th>Meaning</th></tr></thead>
                        <tbody>
                            <tr><td>signal_count</td><td>Total articles mentioning this theme in the window</td></tr>
                            <tr><td>country_count</td><td>Number of distinct countries with coverage</td></tr>
                            <tr><td>velocity</td><td>Signal count in the most recent 1-hour bucket</td></tr>
                            <tr><td>trend</td><td>accelerating / stable / fading (see formula below)</td></tr>
                            <tr><td>spread_pct</td><td>country_count ÷ total active countries × 100</td></tr>
                            <tr><td>avg_sentiment</td><td>Mean tone score across all signals (negative = negative coverage)</td></tr>
                            <tr><td>top_countries</td><td>Top 3 countries by signal count for this theme</td></tr>
                            <tr><td>top_persons</td><td>Most-mentioned people within this theme in the window</td></tr>
                            <tr><td>hourly_timeline</td><td>Array of {'{hour, count}'} objects for the sparkline chart</td></tr>
                            <tr><td>category</td><td>Open category badge — crisis-anchored, LLM-typed from evidence</td></tr>
                            <tr><td>crisis_relevant</td><td>Analyst filter flag: is this thread crisis-relevant?</td></tr>
                            <tr><td>is_umbrella / parent_id</td><td>Umbrella grouping — top-level umbrella vs child thread</td></tr>
                            <tr><td>has_public_interest</td><td>True if theme words match Google trending keywords</td></tr>
                            <tr><td>has_wiki_activity</td><td>True if theme words match Wikipedia article titles</td></tr>
                        </tbody>
                    </table>
                </section>

                <hr className="docs-divider" />

                {/* ── Research Workflow ── */}
                <section className="docs-section" id="research-workflow">
                    <div className="docs-section-eyebrow">Investigation</div>
                    <h2>Research Workflow</h2>
                    <p className="docs-lead">
                        Atlas turns a natural-language question into a guided investigation, not a finished
                        answer. A search like <em>"climate and water stress in Iran"</em> becomes a research
                        plan — ranked anchors, coverage gaps, and pin candidates that you assemble into a
                        Workspace dossier. The first response is a starting board, never a closed verdict.
                    </p>
                    <h3>From query to plan</h3>
                    <p>
                        A deterministic intent parser reads the query, then several discovery lanes run in
                        parallel: country context, country-scoped and global narrative threads, public
                        attention, related branches, and a language-agnostic semantic lane over
                        <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}> signal_embeddings</code>.
                        Every result is an <strong>anchor</strong>, labelled by the role it can play as evidence
                        so nothing arrives unqualified.
                    </p>
                    <div className="docs-source-grid">
                        <div className="docs-source-card">
                            <div className="docs-source-card-head">
                                <span className="docs-source-badge badge-trends">DIRECT</span>
                                <span className="docs-source-title">Direct evidence</span>
                            </div>
                            <p>Anchors that speak to the question head-on — the spine of the investigation.</p>
                        </div>
                        <div className="docs-source-card">
                            <div className="docs-source-card-head">
                                <span className="docs-source-badge badge-gdelt">CONTEXT</span>
                                <span className="docs-source-title">Context</span>
                            </div>
                            <p>Background that frames the question without answering it directly.</p>
                        </div>
                        <div className="docs-source-card">
                            <div className="docs-source-card-head">
                                <span className="docs-source-badge badge-wiki">WEAK</span>
                                <span className="docs-source-title">Weak support</span>
                            </div>
                            <p>Loosely related material — kept and flagged, never presented as proof.</p>
                        </div>
                    </div>
                    <div className="docs-callout">
                        <strong>Gaps are evidence too.</strong> A lane that returns nothing emits a coverage-gap
                        note rather than failing silently. An absent perspective — no local voice, no public
                        attention, a thread that doesn't clear the quality gate — is reported as part of the plan,
                        not hidden by it.
                    </div>
                    <h3>Ranking you can inspect</h3>
                    <p>
                        Anchors are ordered by an <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>investigative_score</code> that
                        weighs intent fit, evidence strength, movement, and source value. Ranking is never
                        silent filtering:
                    </p>
                    <div className="docs-pipeline">
                        <div className="docs-pipeline-step">
                            <div className="docs-pipeline-num">→</div>
                            <div className="docs-pipeline-step-body">
                                <h4>Ranking explanations</h4>
                                <p>Each anchor carries reason codes for why it placed where it did, plus the relevance gate it cleared.</p>
                            </div>
                        </div>
                        <div className="docs-pipeline-step">
                            <div className="docs-pipeline-num">→</div>
                            <div className="docs-pipeline-step-body">
                                <h4>Downranking ledger</h4>
                                <p>Candidate → shown → downranked → omitted reconciles exactly, so you can audit what was demoted and why — nothing disappears off the books.</p>
                            </div>
                        </div>
                        <div className="docs-pipeline-step">
                            <div className="docs-pipeline-num">→</div>
                            <div className="docs-pipeline-step-body">
                                <h4>Low-confidence tray</h4>
                                <p>Noise lanes — sports, entertainment, news roundups — are moved to an inspectable tray, not deleted. You can always look at what was set aside.</p>
                            </div>
                        </div>
                    </div>
                    <h3>Workbench — investigation memory</h3>
                    <p>
                        The Workspace overlay holds multiple saved investigations side by side, so pins from
                        unrelated sessions never mix. Within one investigation you keep a <strong>Trail</strong> (the
                        chronological path you took) and <strong>Pinned</strong> evidence (countries, sources, people,
                        signals, and threads you curated), export the whole state as JSON, and every impression,
                        open, and pin is recorded in a pin-event log. A report is an optional later output generated
                        from pinned state — not the first thing Atlas hands you.
                    </p>
                </section>

                <hr className="docs-divider" />

                {/* ── Cross-Source Intelligence ── */}
                <section className="docs-section" id="cross-source">
                    <div className="docs-section-eyebrow">Validation Model</div>
                    <h2>Cross-Source Intelligence</h2>
                    <p className="docs-lead">
                        The most valuable signal in Atlas is not any single source — it's the intersection.
                        When the same topic appears independently across media signals, local-language sources,
                        social commentary, Google search behavior, and Wikipedia reading patterns, the probability
                        that it reflects genuine real-world salience is substantially higher.
                    </p>
                    <div className="docs-callout">
                        <strong>The layer model:</strong> media coverage, local/regional voice, public commentary,
                        search curiosity, and reference-seeking each represent a different response to an event. A
                        narrative that activates several layers is more meaningful than a raw volume spike in one feed.
                    </div>
                    <h3>Semantic matching across sources</h3>
                    <p>
                        The strongest cross-source link is semantic, not keyword. Atlas embeds signal text with a
                        multilingual e5 model and stores the vectors in <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>signal_embeddings</code> (pgvector,
                        HNSW index). Because the embedding space is language-agnostic, a Persian headline and an
                        English one about the same event land near each other — so a thread, a research anchor, or the
                        "semantic neighbors" on a signal can connect coverage that shares no literal keywords. This is
                        what lets convergence be detected across languages and source families. The SEARCH and WIKI
                        badges below are a lighter, complementary keyword check, not the primary mechanism.
                    </p>
                    <h3>How SEARCH and WIKI badges are computed</h3>
                    <p>
                        As a fast secondary signal, Atlas runs two batch enrichment queries.
                        For each top narrative theme label:
                    </p>
                    <div className="docs-pipeline">
                        <div className="docs-pipeline-step">
                            <div className="docs-pipeline-num">→</div>
                            <div className="docs-pipeline-step-body">
                                <h4>Theme label word extraction</h4>
                                <p>
                                    The GDELT theme code (e.g. <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>ECON_INFLATION</code>) is
                                    resolved to a human label ("Inflation"). Words longer than 3 characters
                                    are extracted as search terms.
                                </p>
                            </div>
                        </div>
                        <div className="docs-pipeline-step">
                            <div className="docs-pipeline-num">→</div>
                            <div className="docs-pipeline-step-body">
                                <h4>Batch Trends query</h4>
                                <p>
                                    A single query fetches all trending keywords from the last 48 hours
                                    that partially match any of the extracted words. The result set is
                                    checked for each theme: if any of its words appears in a trending
                                    keyword, <code style={{ fontFamily: 'monospace', color: '#4ade80' }}>has_public_interest</code> is set to true.
                                </p>
                            </div>
                        </div>
                        <div className="docs-pipeline-step">
                            <div className="docs-pipeline-num">→</div>
                            <div className="docs-pipeline-step-body">
                                <h4>Batch Wikipedia query</h4>
                                <p>
                                    Same pattern against <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>wiki_pageviews_v2</code>
                                    for the last 3 days. Article titles that partially match the theme
                                    words trigger <code style={{ fontFamily: 'monospace', color: '#fbbf24' }}>has_wiki_activity</code> true.
                                </p>
                            </div>
                        </div>
                    </div>
                    <p>
                        Both enrichment queries run within the same database connection as the main
                        narratives query, adding roughly 20–50ms total overhead. They are wrapped in
                        a try/except and are non-fatal: if either table is empty or the query fails,
                        the flags default to false and threads are still returned.
                    </p>
                </section>

                <hr className="docs-divider" />

                {/* ── Voice & Coverage ── */}
                <section className="docs-section" id="voice-coverage">
                    <div className="docs-section-eyebrow">Provenance</div>
                    <h2>Voice &amp; Self-Coverage</h2>
                    <p className="docs-lead">
                        "Global" is a measured claim in Atlas, not a slogan. The system tracks not only what is
                        covered but who is doing the covering — and it separates a country being <em>talked
                        about</em> from a country having its own <em>voice</em>.
                    </p>
                    <div className="docs-callout">
                        <strong>Self-coverage is ownership, not language.</strong> BBC Persian reporting on Iran is
                        British eyes in Persian — not Iranian voice. Atlas measures self-coverage by outlet
                        ownership (origin country = subject country). A foreign outlet publishing in a local
                        language is tracked in a separate
                        <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}> soft_power_local_language</code> bucket
                        and never counted as domestic voice.
                    </div>
                    <h3>Voice Mix metrics</h3>
                    <p>
                        Served by <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>/api/v2/voice-mix</code> and
                        surfaced in the Country Brief as "X% covered by its own press":
                    </p>
                    <table className="docs-table">
                        <thead><tr><th>Metric</th><th>Meaning</th></tr></thead>
                        <tbody>
                            <tr><td>voice_entropy</td><td>Diversity of outlet <strong>origin</strong> countries — the headline objective metric (target band ≈ 0.65–0.70)</td></tr>
                            <tr><td>language_entropy</td><td>Diversity of the languages signals are written in</td></tr>
                            <tr><td>english_share_of_known</td><td>Share of language-known signals that are English</td></tr>
                            <tr><td>cjk_coverage</td><td>Presence of Chinese / Japanese / Korean coverage</td></tr>
                            <tr><td>self_voice_ratio</td><td>Share of a country's coverage from outlets it owns</td></tr>
                            <tr><td>diversity_score</td><td>0–100 composite of the measures above</td></tr>
                        </tbody>
                    </table>
                    <h3>How Atlas widens the aperture</h3>
                    <p>
                        Voice is raised at the source: 200+ native-language RSS feeds across 100+ countries and
                        30+ languages (uncapped, unlike metered news APIs), native-script geo-tagging so a Persian
                        or Chinese headline is attributed to the country it <em>names</em> rather than the outlet's
                        home country, multilingual NLP for in-window scoring, and on-demand translation.
                    </p>
                    <div className="docs-callout">
                        <strong>Honest ceiling.</strong> English is a real lingua franca and the GDELT English
                        firehose is large, so the diversity score climbs and then plateaus rather than reaching
                        100. Atlas reports the number rather than pretending the monoculture away.
                    </div>
                    <h3>Translation</h3>
                    <p>
                        Headlines not in the viewer's language are <strong>translated by default</strong> with a
                        "See original" toggle. Combined with own-voice sorting in the Country Brief, a country's own
                        press surfaces in the reader's language instead of being buried under English coverage about it.
                    </p>
                </section>

                <hr className="docs-divider" />

                {/* ── The Math ── */}
                <section className="docs-section" id="the-math">
                    <div className="docs-section-eyebrow">Formulas</div>
                    <h2>The Math</h2>
                    <p className="docs-lead">
                        Atlas's analytical layer is built on standard statistics applied to time-series
                        signal data. These are the core formulas driving the visual intelligence.
                    </p>

                    <h3>Trend direction (velocity ratio)</h3>
                    <div className="docs-formula">
                        <div className="docs-formula-label">Velocity classification</div>
                        {`last_hour  = signals in t-1h window
prev_hour  = signals in t-2h to t-1h window

trend = "accelerating"  if  last_hour > prev_hour × 1.2
trend = "fading"        if  last_hour < prev_hour × 0.8
trend = "stable"        otherwise`}
                    </div>
                    <p>
                        The 1.2× and 0.8× thresholds correspond to a 20% change in either direction.
                        This prevents noise-driven oscillation between states for topics with small
                        but steady signal flow.
                    </p>

                    <h3>Geographic spread</h3>
                    <div className="docs-formula">
                        <div className="docs-formula-label">Spread percentage</div>
                        {`spread_pct = (country_count / total_active_countries) × 100

total_active_countries = COUNT(DISTINCT country_code)
                         FROM signals_v2
                         WHERE timestamp > NOW() - window`}
                    </div>
                    <p>
                        A theme with 40 countries out of 80 active has spread_pct = 50%.
                        This normalizes for the fact that fewer countries are active at night
                        or during low-news periods.
                    </p>

                    <h3>Anomaly detection (z-score)</h3>
                    <div className="docs-formula">
                        <div className="docs-formula-label">Country anomaly score</div>
                        {`baseline = AVG(hourly_signal_count) over last 7 days
stddev   = STDDEV(hourly_signal_count) over last 7 days
z_score  = (current_count - baseline) / NULLIF(stddev, 0)

level = "critical"  if z_score ≥ 3.0
level = "elevated"  if z_score ≥ 2.0
level = "notable"   if z_score ≥ 1.5
multiplier = current_count / NULLIF(baseline, 0)`}
                    </div>
                    <p>
                        The multiplier (e.g. "4.2× above normal") is more readable than z-score for
                        users. Both are computed but only the multiplier is displayed in the panel.
                    </p>

                    <h3>Correlation matrix (Jaccard similarity)</h3>
                    <div className="docs-formula">
                        <div className="docs-formula-label">Country–country narrative similarity</div>
                        {`J(A, B) = |themes(A) ∩ themes(B)| / |themes(A) ∪ themes(B)|

Where themes(X) is the set of distinct themes in country X's
signals within the selected time window.

Ranges from 0 (no shared narratives) to 1.0 (identical topic set).`}
                    </div>
                    <p>
                        High Jaccard score between two countries doesn't mean they agree on a topic —
                        it means they are covering the same topics. Sentiment analysis determines
                        whether their framing diverges (positive in one country, negative in another).
                        That combination — same topic, opposite sentiment — is the signature of a
                        polarized narrative.
                    </p>

                    <h3>Sentiment normalization</h3>
                    <div className="docs-formula">
                        <div className="docs-formula-label">GDELT V2TONE sentiment extraction</div>
                        {`V2TONE = "tone,positive_score,negative_score,polarity,
           activity_ref_density,self_ref_density,word_count"

Atlas uses tone (first component) as the primary sentiment signal.
Tone = positive_score - negative_score, scaled approximately to [-100, +100].
Typical range in practice: [-10, +10].

avg_sentiment per theme = AVG(sentiment) across all signals in window`}
                    </div>

                    <h3>Crisis relevance (category typing)</h3>
                    <p>
                        Crisis is no longer a per-signal keyword-weight sum. Each <em>thread</em> is typed into an
                        open category and marked <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>crisis_relevant</code>
                        by an LLM reading its evidence, against an anchored-emergent taxonomy (crisis domains seed the
                        set; emergent domains extend it). Embedding cosine alone was measured to be unreliable for
                        this, so the classifier — not a lexicon — is the typer, and crisis relevance is exposed as a
                        filter rather than a hidden gate.
                    </p>
                    <div className="docs-formula">
                        <div className="docs-formula-label">Legacy per-signal crisis heuristic (fast tagging)</div>
                        {`crisis_score = Σ weights[theme] for each crisis_theme in signal.themes
               / len(crisis_themes)

Themes matched against a crisis keyword taxonomy; severity from the
max-weight crisis theme present:
  weight ≥ 0.8 → "critical"   weight ≥ 0.5 → "high"
  weight ≥ 0.3 → "medium"     else → "low"`}
                    </div>
                </section>

                <hr className="docs-divider" />

                {/* ── Research & Validation ── */}
                <section className="docs-section" id="research-validation">
                    <div className="docs-section-eyebrow">Methodology Program</div>
                    <h2>Research &amp; Validation</h2>
                    <p className="docs-lead">
                        Atlas is built alongside a research track that treats the engine as an experiment, not a
                        finished product. The methods behind narrative discovery, taxonomy typing, and cross-source
                        validation are written up as a set of working papers — and, importantly, the papers are kept
                        honest against what the engine actually does.
                    </p>
                    <div className="docs-callout">
                        <strong>Papers are registered and tracked.</strong> A master plan indexes the paper set
                        (open-set narrative discovery, taxonomy precision, cross-source validation, heat / attention,
                        analyst workflow). A <em>staleness ledger</em> records every claim in a paper that an engine
                        change has invalidated, as a closeable row — so a number in a paper either matches the live
                        system or is logged as pending reconciliation. Drift is registered, not hidden.
                    </div>
                    <h3>Measured vs. pending</h3>
                    <p>
                        Two results anchor the current write-up. First, an <strong>A/B</strong> comparing the old
                        split-brain construction (a lexical theme path and an embedding path that never reconciled)
                        against the unified single-substrate engine — the unified engine wins on coherence, purity,
                        and blob-resistance. Second, a taxonomy revision validated by <strong>inter-annotator
                        agreement</strong> across a model ensemble, which lifts labeling agreement by adding an
                        explicit reject class instead of force-fitting every story into a crisis category.
                    </p>
                    <p>
                        The track is deliberately honest about what is <em>not</em> done: several required experiments
                        — a theme-hint ablation, at least one external baseline (e.g. BERTopic), a temporal hold-out
                        with confidence intervals, and a crisis-only in-category agreement split — are logged as open
                        rows rather than claimed. The aim is validation you can audit, matching the product's own
                        no-silent-filtering principle.
                    </p>
                </section>

                <hr className="docs-divider" />

                {/* ── API Reference ── */}
                <section className="docs-section" id="api-reference">
                    <div className="docs-section-eyebrow">Endpoints</div>
                    <h2>API Reference</h2>
                    <p className="docs-lead">
                        The Atlas backend exposes a REST API at <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>atlas-api-pedro.fly.dev</code>.
                        All endpoints return JSON and support CORS for the frontend domain.
                    </p>

                    <div className="docs-endpoint">
                        <div className="docs-endpoint-header">
                            <span className="docs-method">GET</span>
                            <span className="docs-endpoint-path">/api/v2/threads</span>
                        </div>
                        <div className="docs-endpoint-body">
                            Living narrative threads (dynamic topics) for the window, with evidence headlines,
                            movement, country spread, and sentiment. Falls back to atlas-topic aggregates so the
                            list is never starved. Cached in Redis.
                            <br /><br />
                            <strong style={{ color: '#e2e8f0' }}>Params:</strong>{' '}
                            <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>hours</code>,{' '}
                            <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>limit</code>,{' '}
                            <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>country_code</code> (optional)
                        </div>
                    </div>

                    <div className="docs-endpoint">
                        <div className="docs-endpoint-header">
                            <span className="docs-method">GET</span>
                            <span className="docs-endpoint-path">/api/v2/threads/{'{thread_id}'}</span>
                        </div>
                        <div className="docs-endpoint-body">
                            Detail for one thread: evidence signals, hourly timeline, top countries, and the
                            key subjects (typed people, organizations, places, and events) most associated with it.
                        </div>
                    </div>

                    <div className="docs-endpoint">
                        <div className="docs-endpoint-header">
                            <span className="docs-method">GET</span>
                            <span className="docs-endpoint-path">/api/v2/topic/{'{topic_id}'}/relationship</span>
                        </div>
                        <div className="docs-endpoint-body">
                            The media/public/social relationship type for one thread — media-led, public-led,
                            social-led, silent-risk, or uncoupled — derived from the ratio of typed member roles
                            (evidence / discussion / mood / movement).
                        </div>
                    </div>

                    <div className="docs-endpoint">
                        <div className="docs-endpoint-header">
                            <span className="docs-method">GET</span>
                            <span className="docs-endpoint-path">/api/v2/briefing</span>
                        </div>
                        <div className="docs-endpoint-body">
                            The Daily Brief payload: lead threads with evidence, heating countries, and watchlist
                            rows with movement. Global or country-scoped.
                            <br /><br />
                            <strong style={{ color: '#e2e8f0' }}>Params:</strong>{' '}
                            <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>hours</code>,{' '}
                            <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>country</code> (optional)
                        </div>
                    </div>

                    <div className="docs-endpoint">
                        <div className="docs-endpoint-header">
                            <span className="docs-method post">POST</span>
                            <span className="docs-endpoint-path">/api/v2/research/plan</span>
                        </div>
                        <div className="docs-endpoint-body">
                            Turns a natural-language query into a research plan: ranked anchors labelled by
                            evidence role, coverage gaps, ranking explanations with reason codes, an inspectable
                            downranking ledger, and a low-confidence tray. Backs the Workspace investigation flow.
                            <br /><br />
                            <strong style={{ color: '#e2e8f0' }}>Body:</strong>{' '}
                            <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>query</code>,{' '}
                            <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>hours</code>
                        </div>
                    </div>

                    <div className="docs-endpoint">
                        <div className="docs-endpoint-header">
                            <span className="docs-method">GET</span>
                            <span className="docs-endpoint-path">/api/v2/voice-mix</span>
                        </div>
                        <div className="docs-endpoint-body">
                            Voice-diversity audit: language entropy, origin diversity (voice_entropy), and the
                            self-coverage ratio — how much of a country's coverage comes from outlets it owns
                            versus foreign or soft-power sources.
                            <br /><br />
                            <strong style={{ color: '#e2e8f0' }}>Params:</strong>{' '}
                            <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>hours</code>,{' '}
                            <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>country</code> (optional)
                        </div>
                    </div>

                    <div className="docs-endpoint">
                        <div className="docs-endpoint-header">
                            <span className="docs-method">GET</span>
                            <span className="docs-endpoint-path">/api/v2/signal/{'{signal_id}'}/context</span>
                        </div>
                        <div className="docs-endpoint-body">
                            For one signal: which narrative threads it belongs to (with gate status) and its
                            semantic neighbors — nearest signals by embedding similarity, across languages.
                        </div>
                    </div>

                    <div className="docs-endpoint">
                        <div className="docs-endpoint-header">
                            <span className="docs-method">GET</span>
                            <span className="docs-endpoint-path">/api/v2/heat/countries</span>
                        </div>
                        <div className="docs-endpoint-body">
                            Country heat composite — velocity, surprise, source diversity, and local voice
                            measured against each country's own baseline, not raw volume. Powers the map fill.
                        </div>
                    </div>

                    <div className="docs-endpoint">
                        <div className="docs-endpoint-header">
                            <span className="docs-method">GET</span>
                            <span className="docs-endpoint-path">/api/v2/nodes</span>
                        </div>
                        <div className="docs-endpoint-body">
                            Country-level signal aggregates: total signals, sentiment, top themes, lat/lon.
                            Powers globe glow density.
                            <br /><br />
                            <strong style={{ color: '#e2e8f0' }}>Params:</strong>{' '}
                            <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>range</code> (1h / 6h / 24h / 7d / 30d),{' '}
                            <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>country</code> (optional ISO code)
                        </div>
                    </div>

                    <div className="docs-endpoint">
                        <div className="docs-endpoint-header">
                            <span className="docs-method">GET</span>
                            <span className="docs-endpoint-path">/api/v2/signals</span>
                        </div>
                        <div className="docs-endpoint-body">
                            Individual article-level signals for the Signal Stream panel, with source language for
                            on-demand translation. Optionally filtered by country or theme.
                            <br /><br />
                            <strong style={{ color: '#e2e8f0' }}>Params:</strong>{' '}
                            <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>limit</code>,{' '}
                            <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>hours</code>,{' '}
                            <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>country</code>,{' '}
                            <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>theme</code>
                        </div>
                    </div>

                    <div className="docs-endpoint">
                        <div className="docs-endpoint-header">
                            <span className="docs-method">GET</span>
                            <span className="docs-endpoint-path">/api/v2/translate</span>
                        </div>
                        <div className="docs-endpoint-body">
                            On-demand headline translation to the viewer's language, cached in
                            <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}> signal_translations</code>. Powers the
                            "translated by default · See original" affordance in the Signal Stream and Brief.
                        </div>
                    </div>

                    <div className="docs-endpoint">
                        <div className="docs-endpoint-header">
                            <span className="docs-method">GET</span>
                            <span className="docs-endpoint-path">/api/v2/anomalies</span>
                        </div>
                        <div className="docs-endpoint-body">
                            Countries with statistically significant spikes vs 7-day rolling baseline.
                            Returns z-score, multiplier, and severity level for each anomalous country.
                        </div>
                    </div>

                    <div className="docs-endpoint">
                        <div className="docs-endpoint-header">
                            <span className="docs-method">GET</span>
                            <span className="docs-endpoint-path">/api/v2/flows</span>
                        </div>
                        <div className="docs-endpoint-body">
                            Narrative flow arcs between countries — where does a story originate and where
                            does it get picked up? Powered by co-occurrence of source and target countries
                            within the same signals.
                        </div>
                    </div>

                    <div className="docs-endpoint">
                        <div className="docs-endpoint-header">
                            <span className="docs-method">GET</span>
                            <span className="docs-endpoint-path">/api/v2/trends/search</span>
                        </div>
                        <div className="docs-endpoint-body">
                            Google trending search keywords. Optionally filtered by country code.
                            Global query returns keywords ranked by number of countries that searched for them.
                        </div>
                    </div>

                    <div className="docs-endpoint">
                        <div className="docs-endpoint-header">
                            <span className="docs-method">GET</span>
                            <span className="docs-endpoint-path">/health</span>
                        </div>
                        <div className="docs-endpoint-body">
                            Database and Redis connectivity check. Returns degraded status within 5 seconds
                            if the connection pool is exhausted, rather than blocking the health checker.
                        </div>
                    </div>

                    <p style={{ fontSize: '12px', color: '#64748b', marginTop: '20px' }}>
                        <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>/api/v2/narratives</code> remains as a
                        legacy GDELT-theme-ranked endpoint; <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>/api/v2/threads</code> is
                        the current product. <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>/api/v2/acled</code>,{' '}
                        <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>/api/v2/vessels</code>, and{' '}
                        <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>/api/v2/aircraft</code> back map-only layers and are not narrative inputs.
                    </p>

                    <div className="docs-callout" style={{ marginTop: '32px' }}>
                        <strong>All endpoints</strong> run with a statement_timeout between 5–20 seconds.
                        On timeout, endpoints return empty arrays rather than erroring — the dashboard
                        degrades gracefully and retries on the next auto-refresh cycle.
                    </div>
                </section>

            </main>
        </div>
    )
}
