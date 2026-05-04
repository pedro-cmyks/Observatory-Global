import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './Docs.css'

const NAV = [
    { id: 'overview', label: 'Overview' },
    {
        id: 'data-sources', label: 'Data Sources', children: [
            { id: 'gdelt-gkg', label: 'GDELT GKG' },
            { id: 'gdelt-events', label: 'GDELT Events' },
            { id: 'google-trends', label: 'Google Trends' },
            { id: 'wikipedia', label: 'Wikipedia' },
            { id: 'acled', label: 'ACLED' },
        ]
    },
    { id: 'signal-pipeline', label: 'Signal Pipeline' },
    { id: 'narrative-threads', label: 'Narrative Threads' },
    { id: 'cross-source', label: 'Cross-Source Intelligence' },
    { id: 'the-math', label: 'The Math' },
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
                    <a href="https://github.com/pedro-cmyks/Observatory-Global" target="_blank" rel="noreferrer">GitHub</a>
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
                        <strong>Core insight:</strong> A narrative that appears simultaneously in GDELT media signals,
                        Google trending searches, and Wikipedia editing activity has crossed three independent signal
                        layers. That cross-source convergence is a strong indicator of real-world salience — not just
                        one outlet amplifying a story.
                    </div>
                    <h3>What Atlas ingests every 15 minutes</h3>
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
                            <tr>
                                <td>GDELT GKG 2.0</td>
                                <td>Media narratives, themes, sentiment, persons</td>
                                <td>15 min</td>
                                <td>~100 countries, 65+ languages</td>
                            </tr>
                            <tr>
                                <td>GDELT Events</td>
                                <td>Actor–action–actor geopolitical events (CAMEO)</td>
                                <td>15 min</td>
                                <td>Global</td>
                            </tr>
                            <tr>
                                <td>Google Trends</td>
                                <td>Public search interest by keyword and country</td>
                                <td>30 min</td>
                                <td>50+ countries</td>
                            </tr>
                            <tr>
                                <td>Wikipedia Pageviews</td>
                                <td>Article reading volume by language/country</td>
                                <td>24 h</td>
                                <td>Global, 20+ languages</td>
                            </tr>
                            <tr>
                                <td>ACLED</td>
                                <td>Verified armed conflict and protest events</td>
                                <td>60 min</td>
                                <td>Global (API key required)</td>
                            </tr>
                        </tbody>
                    </table>
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
                                <span className="docs-source-badge badge-acled">ACLED</span>
                                <span className="docs-source-title">Armed Conflict Location</span>
                            </div>
                            <p>
                                Human-verified conflict events: battles, explosions, riots, protests.
                                Unlike GDELT's media-derived signals, ACLED events are field-verified.
                                They appear as red markers on the map and in the Kinetic Conflicts section.
                            </p>
                            <div className="docs-source-meta">
                                <div className="docs-source-meta-item">Latency <span>~60 min</span></div>
                                <div className="docs-source-meta-item">Table <span>acled_conflicts_v2</span></div>
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
                        Google Trends data is ingested via the <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>pytrends</code> library
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

                <section className="docs-section" id="acled">
                    <h3>ACLED — Kinetic Ground Truth</h3>
                    <p>
                        ACLED is unique among Atlas's sources: it is human-verified. Every event in
                        <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}> acled_conflicts_v2</code> has been reviewed by
                        regional analysts. This makes it the most reliable signal for ground-truth conflict
                        activity, but also the smallest dataset and the one requiring API credentials.
                    </p>
                    <p>
                        ACLED events appear as colored map markers: red for battles/explosions, orange for
                        riots/protests, yellow for other. Fatality counts drive marker size (capped at radius 15px).
                    </p>
                    <div className="docs-callout">
                        <strong>Note:</strong> ACLED requires a free API key from{' '}
                        <span style={{ color: '#38bdf8' }}>acleddata.com</span>. Without credentials,
                        the <code style={{ fontFamily: 'monospace' }}>ingest_acled</code> service skips silently.
                        Set <code style={{ fontFamily: 'monospace' }}>ACLED_API_KEY</code> and{' '}
                        <code style={{ fontFamily: 'monospace' }}>ACLED_EMAIL</code> in your environment to activate it.
                    </div>
                </section>

                <hr className="docs-divider" />

                {/* ── Signal Pipeline ── */}
                <section className="docs-section" id="signal-pipeline">
                    <div className="docs-section-eyebrow">Architecture</div>
                    <h2>Signal Pipeline</h2>
                    <p className="docs-lead">
                        Raw GDELT files arrive as compressed CSVs every 15 minutes. Atlas transforms them
                        through a four-stage pipeline into queryable narrative intelligence in under 30 seconds.
                    </p>
                    <div className="docs-pipeline">
                        <div className="docs-pipeline-step">
                            <div className="docs-pipeline-num">01</div>
                            <div className="docs-pipeline-step-body">
                                <h4>Fetch & Decompress</h4>
                                <p>
                                    The GDELT lastupdate.txt file is polled for the latest GKG URL.
                                    Both the English and Translingual feeds are downloaded in parallel.
                                    ZIP files are decompressed in memory — no disk writes.
                                    CSV field size limit is raised to 10MB to handle GDELT's large theme columns.
                                </p>
                            </div>
                        </div>
                        <div className="docs-pipeline-step">
                            <div className="docs-pipeline-num">02</div>
                            <div className="docs-pipeline-step-body">
                                <h4>Parse & Normalize</h4>
                                <p>
                                    Each GKG row is parsed into a signal dict. FIPS country codes are converted
                                    to ISO 3166. Themes are deduplicated and capped at 10 per signal.
                                    Sentiment is extracted from the V2TONE vector's first component.
                                    Crisis classification (severity, event_type, crisis_score) is computed
                                    from the theme set using a keyword taxonomy.
                                </p>
                            </div>
                        </div>
                        <div className="docs-pipeline-step">
                            <div className="docs-pipeline-num">03</div>
                            <div className="docs-pipeline-step-body">
                                <h4>Insert into signals_v2</h4>
                                <p>
                                    Parsed signals are batch-inserted with <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>ON CONFLICT DO NOTHING</code> (deduplication
                                    by source_url + timestamp). The <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>themes</code> column
                                    stores a PostgreSQL <code style={{ fontFamily: 'monospace' }}>text[]</code> array with a GIN index
                                    enabling sub-millisecond <code style={{ fontFamily: 'monospace' }}>&&</code> (array overlap) queries.
                                </p>
                            </div>
                        </div>
                        <div className="docs-pipeline-step">
                            <div className="docs-pipeline-num">04</div>
                            <div className="docs-pipeline-step-body">
                                <h4>Pre-aggregate into theme_hourly_v2</h4>
                                <p>
                                    After each ingest, the last 2 hours of signals are aggregated into
                                    <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}> theme_hourly_v2</code> — one row per (hour, theme) with
                                    signal_count, country_count, source_count, and avg_sentiment.
                                    This table is the backbone of the Narrative Threads endpoint:
                                    it makes any time window query (1h, 24h, 7d) instant by avoiding
                                    a full <code style={{ fontFamily: 'monospace' }}>unnest(themes)</code> scan on 300K+ rows.
                                </p>
                            </div>
                        </div>
                    </div>
                    <h3>Database schema overview</h3>
                    <div className="docs-code">
                        {`signals_v2          Raw article-level signals (GIN index on themes[])
theme_hourly_v2     Pre-aggregated (hour, theme) counts — powers Narrative Threads
country_hourly_v2   Materialized view: per-country hourly signal counts + sentiment
events_v2           GDELT CAMEO actor→action→actor events
trends_v2           Google Trends keywords by country
wiki_pageviews_v2   Wikipedia article views by country/language
acled_conflicts_v2  ACLED verified conflict events
countries_v2        Country centroids and metadata`}
                    </div>
                </section>

                <hr className="docs-divider" />

                {/* ── Narrative Threads ── */}
                <section className="docs-section" id="narrative-threads">
                    <div className="docs-section-eyebrow">Intelligence Layer</div>
                    <h2>Narrative Threads</h2>
                    <p className="docs-lead">
                        A narrative thread is a GDELT theme code that has accumulated significant
                        coverage within the selected time window — characterized by its volume,
                        velocity, geographic spread, and sentiment trajectory.
                    </p>
                    <p>
                        The threads endpoint runs a two-phase query designed to answer any time window
                        (1 hour to 7 days) without exceeding a 20-second statement timeout:
                    </p>
                    <h3>Phase 1 — Theme ranking (from pre-aggregated table)</h3>
                    <div className="docs-code">
                        {`SELECT theme,
       SUM(signal_count)  AS signal_count,
       SUM(country_count) AS country_count,
       AVG(avg_sentiment) AS avg_sentiment
FROM theme_hourly_v2
WHERE hour > NOW() - $hours_interval
GROUP BY theme
ORDER BY signal_count DESC
LIMIT 5`}
                    </div>
                    <p>
                        This query reads only <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>theme_hourly_v2</code> —
                        a small pre-aggregated table with ~50K rows — rather than scanning
                        the full <code style={{ fontFamily: 'monospace' }}>signals_v2</code> table.
                        Response time: typically under 50ms.
                    </p>
                    <h3>Phase 2 — Velocity, timeline, countries (GIN-indexed lookup)</h3>
                    <p>
                        Once the top 5 themes are known, a second query scopes into <code style={{ fontFamily: 'monospace' }}>signals_v2</code>
                        using the GIN index on the <code style={{ fontFamily: 'monospace' }}>themes</code> column. Because it uses
                        <code style={{ fontFamily: 'monospace' }}> themes && $top_themes::text[]</code> (array overlap), PostgreSQL
                        uses the GIN index to fetch only rows containing at least one of the top 5 themes —
                        a fraction of the full table.
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
                            <tr><td>has_public_interest</td><td>True if theme words match Google trending keywords</td></tr>
                            <tr><td>has_wiki_activity</td><td>True if theme words match Wikipedia article titles</td></tr>
                        </tbody>
                    </table>
                </section>

                <hr className="docs-divider" />

                {/* ── Cross-Source Intelligence ── */}
                <section className="docs-section" id="cross-source">
                    <div className="docs-section-eyebrow">Validation Model</div>
                    <h2>Cross-Source Intelligence</h2>
                    <p className="docs-lead">
                        The most valuable signal in Atlas is not any single source — it's the intersection.
                        When the same topic appears independently across GDELT media signals, Google search
                        behavior, and Wikipedia reading patterns, the probability that it reflects genuine
                        real-world salience is substantially higher.
                    </p>
                    <div className="docs-callout">
                        <strong>The three-layer model:</strong> Media coverage (GDELT) → Public curiosity
                        (Google Trends) → Reference-seeking (Wikipedia). Each layer represents a different
                        cognitive and behavioral response to an event. A narrative that activates all three
                        is deeply embedded in public consciousness, not just a media cycle.
                    </div>
                    <h3>How SEARCH and WIKI badges are computed</h3>
                    <p>
                        At the end of each narratives query, Atlas runs two batch enrichment queries.
                        For each of the top 5 narrative themes:
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

                    <h3>Crisis score</h3>
                    <div className="docs-formula">
                        <div className="docs-formula-label">Per-signal crisis classification</div>
                        {`crisis_score = Σ weights[theme] for each crisis_theme in signal.themes
               / len(crisis_themes)

Themes are matched against a crisis keyword taxonomy.
Severity is derived from the max-weight crisis theme present:
  weight ≥ 0.8 → "critical"
  weight ≥ 0.5 → "high"
  weight ≥ 0.3 → "medium"
  else         → "low"`}
                    </div>
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
                            <span className="docs-endpoint-path">/api/v2/narratives</span>
                        </div>
                        <div className="docs-endpoint-body">
                            Top narrative threads for the given time window. Cached 5 minutes in Redis.
                            <br /><br />
                            <strong style={{ color: '#e2e8f0' }}>Params:</strong>{' '}
                            <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>hours</code> (1–8760, default 24),{' '}
                            <code style={{ fontFamily: 'monospace', color: '#38bdf8' }}>limit</code> (1–20, default 5)
                        </div>
                    </div>

                    <div className="docs-endpoint">
                        <div className="docs-endpoint-header">
                            <span className="docs-method">GET</span>
                            <span className="docs-endpoint-path">/api/v2/nodes</span>
                        </div>
                        <div className="docs-endpoint-body">
                            Country-level signal aggregates: total signals, sentiment, top themes, lat/lon.
                            Powers the map globe heatmap.
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
                            Individual article-level signals for the Signal Stream panel.
                            Optionally filtered by country or theme.
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
                            <span className="docs-endpoint-path">/api/v2/trends</span>
                        </div>
                        <div className="docs-endpoint-body">
                            Google trending search keywords. Optionally filtered by country code.
                            Global query returns keywords ranked by number of countries that searched for them.
                        </div>
                    </div>

                    <div className="docs-endpoint">
                        <div className="docs-endpoint-header">
                            <span className="docs-method">GET</span>
                            <span className="docs-endpoint-path">/api/v2/acled</span>
                        </div>
                        <div className="docs-endpoint-body">
                            ACLED conflict events with location, type, actors, fatalities, and source notes.
                            Returns empty array if ACLED credentials are not configured.
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
