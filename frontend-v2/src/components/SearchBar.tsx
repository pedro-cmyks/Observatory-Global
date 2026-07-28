import { useState, useEffect, useCallback, useRef } from 'react'
import { track } from '../lib/telemetry'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import { useFocus } from '../contexts/FocusContext'
import type { RegionFilter } from '../contexts/FocusContext'
import { Search } from '../lib/icons'
import {
    SEARCH_LOOKUP_FAILED,
    degradedSearchSegments,
    describeDegradedSegments,
    hasVisibleSearchResults,
    searchEmptyVariant,
} from '../lib/searchResults'
import { decodeEntities } from '../lib/decodeEntities'
import { LabelReviewChip } from '../lib/labelReviewChip'
import { Flag } from './Flag'
import { classifyQuery } from '../lib/searchIntent'
import { isPublicAttentionRelevant } from '../lib/publicAttentionFilters'
import './SearchBar.css'

// Sorted longest-first so multi-word country names match before single-word substrings
const COUNTRY_ALIASES: [string, string, string][] = [
  // [alias (lowercase), code, display name]
  ['united states', 'US', 'United States'],
  ['estados unidos', 'US', 'United States'],
  ['united kingdom', 'GB', 'United Kingdom'],
  ['reino unido', 'GB', 'United Kingdom'],
  ['south africa', 'ZA', 'South Africa'],
  ['sudáfrica', 'ZA', 'South Africa'], ['sudafrica', 'ZA', 'South Africa'],
  ['south korea', 'KR', 'South Korea'], ['corea del sur', 'KR', 'South Korea'],
  ['north korea', 'KP', 'North Korea'], ['corea del norte', 'KP', 'North Korea'],
  ['saudi arabia', 'SA', 'Saudi Arabia'], ['arabia saudita', 'SA', 'Saudi Arabia'],
  ['new zealand', 'NZ', 'New Zealand'], ['nueva zelanda', 'NZ', 'New Zealand'],
  ['costa rica', 'CR', 'Costa Rica'],
  ['el salvador', 'SV', 'El Salvador'],
  ['sri lanka', 'LK', 'Sri Lanka'],
  ['puerto rico', 'PR', 'Puerto Rico'],
  ['dominican republic', 'DO', 'Dominican Rep.'],
  ['república dominicana', 'DO', 'Dominican Rep.'],
  ['colombia', 'CO', 'Colombia'],
  ['brazil', 'BR', 'Brazil'], ['brasil', 'BR', 'Brazil'],
  ['mexico', 'MX', 'Mexico'], ['méxico', 'MX', 'Mexico'],
  ['argentina', 'AR', 'Argentina'],
  ['venezuela', 'VE', 'Venezuela'],
  ['peru', 'PE', 'Peru'], ['perú', 'PE', 'Peru'],
  ['chile', 'CL', 'Chile'],
  ['ecuador', 'EC', 'Ecuador'],
  ['bolivia', 'BO', 'Bolivia'],
  ['uruguay', 'UY', 'Uruguay'],
  ['paraguay', 'PY', 'Paraguay'],
  ['panama', 'PA', 'Panama'], ['panamá', 'PA', 'Panama'],
  ['cuba', 'CU', 'Cuba'], ['haiti', 'HT', 'Haiti'], ['haití', 'HT', 'Haiti'],
  ['russia', 'RU', 'Russia'], ['rusia', 'RU', 'Russia'],
  ['china', 'CN', 'China'],
  ['india', 'IN', 'India'],
  ['germany', 'DE', 'Germany'], ['alemania', 'DE', 'Germany'],
  ['france', 'FR', 'France'], ['francia', 'FR', 'France'],
  ['spain', 'ES', 'Spain'], ['españa', 'ES', 'Spain'],
  ['italy', 'IT', 'Italy'], ['italia', 'IT', 'Italy'],
  ['japan', 'JP', 'Japan'], ['japón', 'JP', 'Japan'], ['japon', 'JP', 'Japan'],
  ['israel', 'IL', 'Israel'],
  ['iran', 'IR', 'Iran'], ['irán', 'IR', 'Iran'],
  ['ukraine', 'UA', 'Ukraine'], ['ucrania', 'UA', 'Ukraine'],
  ['turkey', 'TR', 'Turkey'], ['turquía', 'TR', 'Turkey'], ['turquia', 'TR', 'Turkey'],
  ['pakistan', 'PK', 'Pakistan'], ['pakistán', 'PK', 'Pakistan'],
  ['indonesia', 'ID', 'Indonesia'],
  ['canada', 'CA', 'Canada'], ['canadá', 'CA', 'Canada'],
  ['australia', 'AU', 'Australia'],
  ['nigeria', 'NG', 'Nigeria'],
  ['ghana', 'GH', 'Ghana'],
  ['kenya', 'KE', 'Kenya'], ['kenia', 'KE', 'Kenya'],
  ['ethiopia', 'ET', 'Ethiopia'], ['etiopía', 'ET', 'Ethiopia'],
  ['egypt', 'EG', 'Egypt'], ['egipto', 'EG', 'Egypt'],
  ['angola', 'AO', 'Angola'],
  ['sudan', 'SD', 'Sudan'], ['sudán', 'SD', 'Sudan'],
  ['congo', 'CD', 'DR Congo'],
  ['myanmar', 'MM', 'Myanmar'],
  ['syria', 'SY', 'Syria'], ['siria', 'SY', 'Syria'],
  ['poland', 'PL', 'Poland'], ['polonia', 'PL', 'Poland'],
  ['netherlands', 'NL', 'Netherlands'], ['holanda', 'NL', 'Netherlands'],
  ['sweden', 'SE', 'Sweden'], ['suecia', 'SE', 'Sweden'],
  ['norway', 'NO', 'Norway'], ['noruega', 'NO', 'Norway'],
  ['denmark', 'DK', 'Denmark'], ['dinamarca', 'DK', 'Denmark'],
  ['finland', 'FI', 'Finland'], ['finlandia', 'FI', 'Finland'],
  ['portugal', 'PT', 'Portugal'],
  ['greece', 'GR', 'Greece'], ['grecia', 'GR', 'Greece'],
  ['romania', 'RO', 'Romania'], ['rumania', 'RO', 'Romania'],
  ['afghanistan', 'AF', 'Afghanistan'], ['afganistán', 'AF', 'Afghanistan'],
  ['ethiopia', 'ET', 'Ethiopia'],
  ['somalia', 'SO', 'Somalia'],
  ['libya', 'LY', 'Libya'], ['libia', 'LY', 'Libya'],
  ['yemen', 'YE', 'Yemen'],
  ['iraq', 'IQ', 'Iraq'], ['irak', 'IQ', 'Iraq'],
  ['taiwan', 'TW', 'Taiwan'],
  ['vietnam', 'VN', 'Vietnam'],
  ['philippines', 'PH', 'Philippines'], ['filipinas', 'PH', 'Philippines'],
  ['malaysia', 'MY', 'Malaysia'], ['malasia', 'MY', 'Malaysia'],
  ['thailand', 'TH', 'Thailand'], ['tailandia', 'TH', 'Thailand'],
  ['bangladesh', 'BD', 'Bangladesh'],
]

interface ParsedQuery {
  topic: string
  countryCode: string | null
  countryDisplay: string | null
  // True when the query is JUST a country name (nothing left after stripping
  // it) → the primary action is "Go to <country>", not a topic story.
  bareCountry: boolean
}

function parseCompoundQuery(q: string): ParsedQuery {
  const lower = q.toLowerCase()
  for (const [alias, code, display] of COUNTRY_ALIASES) {
    if (lower.includes(alias)) {
      const topic = q
        .replace(new RegExp(`\\b(en|in|de|del|sobre|from|about)\\s+${alias}\\b`, 'i'), '')
        .replace(new RegExp(`\\b${alias}\\b`, 'gi'), '')
        .replace(/[,\s]+/g, ' ')
        .trim()
      const bareCountry = topic.length < 2
      return { topic: bareCountry ? q : topic, countryCode: code, countryDisplay: display, bareCountry }
    }
  }
  return { topic: q, countryCode: null, countryDisplay: null, bareCountry: false }
}

interface TopCountry {
    code: string
    name: string
    count: number
}

interface ThemeResult {
    theme: string
    label?: string
    category?: string
    description?: string
    source?: 'taxonomy' | 'signals'
    total_signals: number
    top_countries: TopCountry[]
}

interface PersonResult {
    person: string
    total_signals: number
    top_countries: TopCountry[]
}

interface CountryResult {
    code: string
    name: string
}

interface ConceptResult {
    slug: string
    label: string
    description: string
    themes: string[]
    related_concepts?: string[]
}

interface RegionResult {
    slug: string
    label: string
    emoji: string
    countries: string[]
}

interface PublicAttentionResult {
    title: string
    views: number
    country_count: number
}

interface SignalMatchResult {
    id: number
    timestamp: string
    country: string
    source: string
    headline: string | null
    themes: string[]
}

interface FuzzySuggestionResult {
    value: string
    type: 'person' | 'country' | 'public_attention' | string
    score: number
    signal_count: number
}

/** A served living thread matched by label (#245 / search-engine-plan P1). */
interface LiveThreadResult {
    id: string // 'dynamic-topic-<n>' — the theme-detail contract id
    label: string
    category: string | null
    crisis_relevant: boolean
    total_signals: number
    is_umbrella: boolean
    match: 'all' | 'partial'
    /** Label Court verdict (N15): 'entailed' | 'partial' | 'failed' | null. */
    label_status?: string | null
}

interface SearchResult {
    query?: string
    normalized_query?: string
    query_variants?: string[]
    themes: ThemeResult[]
    live_threads?: LiveThreadResult[]
    persons: PersonResult[]
    countries: CountryResult[]
    concepts?: ConceptResult[]
    concept_suggestions?: { slug: string; label: string; description: string }[]
    region?: RegionResult | null
    public_attention?: PublicAttentionResult[]
    signal_matches?: SignalMatchResult[]
    fuzzy_suggestions?: FuzzySuggestionResult[]
    /** True when a retrieval lane FAILED (timeout/error) — the backend appends
     *  degraded_segments only from except blocks, never for "ran and found
     *  nothing". A degraded response must not render as measured absence. */
    degraded?: boolean
    degraded_segments?: string[]
}

interface SearchBarProps {
    onThemeSelect: (theme: string, countryCode?: string, countryName?: string) => void
    onCountrySelect: (code: string) => void
    onPublicAttentionSelect?: (item: PublicAttentionResult) => void
    onStartInvestigation?: (query: string) => void
    /** Natural query → cross-thread STORY panel (research-plan anchors in the
     *  stream slot). Primary CTA + Enter (2026-07-04, Pedro: a search's first
     *  answer is the story, not a thread builder). */
    onOpenStory?: (query: string) => void
    externalQuery?: { q: string; id: number }
}

export function SearchBar({ onThemeSelect, onCountrySelect, onPublicAttentionSelect, onStartInvestigation, onOpenStory, externalQuery }: SearchBarProps) {
    const [query, setQuery] = useState('')
    const [results, setResults] = useState<SearchResult | null>(null)
    const [parsedQuery, setParsedQuery] = useState<ParsedQuery>({ topic: '', countryCode: null, countryDisplay: null, bareCountry: false })
    const [isOpen, setIsOpen] = useState(false)
    const [loading, setLoading] = useState(false)
    // Power tools (build-thread / investigation) collapse behind a "more"
    // affordance so each query leads with ONE obvious action.
    const [showMore, setShowMore] = useState(false)
    // Query-expansion variants are normalization internals ("usstrikesenergy…")
    // — progressive disclosure (council wish 7): a human sentence by default,
    // the variant chips one click away. Never deleted, just demoted.
    const [showVariants, setShowVariants] = useState(false)
    const inputRef = useRef<HTMLInputElement>(null)
    const { setFocus, setMapFlyCountry, setCountry, setTheme, setRegion } = useFocus()
    // Guards the close-vs-inflight-response race: pressing Enter (story) while
    // a search is in flight must not let the late response reopen the dropdown.
    const searchSeqRef = useRef(0)

    const doSearch = useCallback(async (q: string) => {
        const seq = ++searchSeqRef.current
        setShowMore(false)
        setShowVariants(false)
        if (q.length < 2) {
            setResults(null)
            setIsOpen(false)
            setParsedQuery({ topic: q, countryCode: null, countryDisplay: null, bareCountry: false })
            return
        }
        const parsed = parseCompoundQuery(q)
        setParsedQuery(parsed)
        const searchQ = parsed.topic.length >= 2 ? parsed.topic : q
        setLoading(true)
        // Never leave the previous query's results rendered under the new
        // query text: a degraded lane can hold the response for 5-25s, which
        // is how "Azad Kashmir" kept 12 Iran receipts on screen (gold UI eval
        // batch 3). The loading state owns that gap — stale results never do.
        setResults(null)
        const failedLookup: SearchResult = {
            themes: [], persons: [], countries: [],
            degraded: true, degraded_segments: [SEARCH_LOOKUP_FAILED],
        }
        try {
            const countryParam = parsed.countryCode ? `&country=${parsed.countryCode}` : ''
            const res = await fetch(`/api/v2/search/unified?q=${encodeURIComponent(searchQ)}&hours=168${countryParam}`)
            if (seq !== searchSeqRef.current) return  // closed/superseded while in flight
            if (res.ok) {
                const data = await res.json()
                if (seq !== searchSeqRef.current) return
                setResults(data)
                // P4 search telemetry: the wedge question is "do people FIND?"
                // — log what each settled query surfaced, esp. zero-results.
                const counts = {
                    live_threads: data?.live_threads?.length ?? 0,
                    themes: data?.themes?.length ?? 0,
                    persons: data?.persons?.length ?? 0,
                    countries: data?.countries?.length ?? 0,
                    concepts: data?.concepts?.length ?? 0,
                }
                track('search_query', {
                    q_len: searchQ.length,
                    country_scoped: !!parsed.countryCode,
                    ...counts,
                    zero: Object.values(counts).every(n => n === 0),
                })
            } else {
                // Fallback to basic search if unified endpoint not available yet
                const fallback = await fetch(`/api/v2/search?q=${encodeURIComponent(searchQ)}&hours=168`)
                if (seq !== searchSeqRef.current) return
                setResults(fallback.ok ? await fallback.json() : failedLookup)
            }
            if (seq !== searchSeqRef.current) return
            setIsOpen(true)
            // Warm the custom query-thread cache so clicking the option is instant.
            fetch(`/api/v2/search/thread?q=${encodeURIComponent(searchQ)}&hours=168${countryParam}`).catch(() => { })
        } catch {
            // A thrown fetch is a FAILED LOOKUP — render it as one. The old
            // silent catch left whatever was on screen standing forever.
            if (seq !== searchSeqRef.current) return
            setResults(failedLookup)
            setIsOpen(true)
        } finally {
            // Only the still-current search may clear the spinner: a
            // superseded response's finally must not un-load the newer
            // in-flight search (that would let an empty state render early).
            if (seq === searchSeqRef.current) setLoading(false)
        }
    }, [])

    useEffect(() => {
        const t = setTimeout(() => { if (query) doSearch(query) }, 300)
        return () => clearTimeout(t)
    }, [query, doSearch])

    // When an external component (e.g. Public Attention) triggers a search query
    useEffect(() => {
        if (!externalQuery) return
        setQuery(externalQuery.q)
        doSearch(externalQuery.q)
        inputRef.current?.focus()
    }, [externalQuery, doSearch])

    const close = () => {
        searchSeqRef.current++  // invalidate any in-flight search response
        setIsOpen(false)
        setQuery('')
        setResults(null)
        setShowMore(false)
        setParsedQuery({ topic: '', countryCode: null, countryDisplay: null, bareCountry: false })
    }

    const handleLiveThreadClick = (t: LiveThreadResult) => {
        track('search_result_click', { segment: 'live_thread', q_len: query.length })
        // The served dynamic-topic id IS the theme contract — same path a
        // NarrativeThreads row takes (#245: search now reaches live threads).
        onThemeSelect(t.id, parsedQuery.countryCode ?? undefined, parsedQuery.countryDisplay ?? undefined)
        close()
    }

    const handleThemeClick = (t: ThemeResult) => {
        track('search_result_click', { segment: 'theme', q_len: query.length })
        if (parsedQuery.countryCode) {
            setCountry(parsedQuery.countryCode)
            setTheme(t.theme)
            setMapFlyCountry(parsedQuery.countryCode)
            onThemeSelect(t.theme, parsedQuery.countryCode, parsedQuery.countryDisplay ?? undefined)
        } else {
            setFocus('theme', t.theme, getThemeLabel(t.theme))
            if (t.top_countries[0]) setMapFlyCountry(t.top_countries[0].code)
            onThemeSelect(t.theme)
        }
        close()
    }

    const handlePersonClick = (p: PersonResult) => {
        track('search_result_click', { segment: 'person', q_len: query.length })
        setFocus('person', p.person, p.person)
        if (p.top_countries[0]) setMapFlyCountry(p.top_countries[0].code)
        close()
    }

    const handleCountryClick = (c: CountryResult) => {
        setFocus('country', c.code, c.name)
        setMapFlyCountry(c.code)
        onCountrySelect(c.code)
        close()
    }

    const handleRegionClick = (r: RegionResult) => {
        const region: RegionFilter = { slug: r.slug, label: r.label, countries: r.countries }
        setRegion(region)
        close()
    }

    const handlePublicAttentionClick = (item: PublicAttentionResult) => {
        if (onPublicAttentionSelect) {
            onPublicAttentionSelect({ ...item, title: item.title.replace(/_/g, ' ') })
            close()
            return
        }
        setQuery(item.title.replace(/_/g, ' '))
        doSearch(item.title.replace(/_/g, ' '))
    }

    const handleSignalMatchClick = (s: SignalMatchResult) => {
        if (s.themes[0]) {
            setTheme(s.themes[0])
            onThemeSelect(s.themes[0], s.country)
        } else if (s.country) {
            handleCountryClick({ code: s.country, name: s.country })
        }
        close()
    }

    const handleFuzzySuggestionClick = (suggestion: FuzzySuggestionResult) => {
        setQuery(suggestion.value)
        doSearch(suggestion.value)
    }

    // Build a custom Narrative Thread from the exact query text. The token
    // `query-thread::<raw>` is resolved by ThemeDetail against /search/thread.
    const handleQueryThreadClick = () => {
        const raw = query.trim()
        if (raw.length < 2) return
        onThemeSelect(`query-thread::${raw}`, parsedQuery.countryCode ?? undefined, parsedQuery.countryDisplay ?? undefined)
        close()
    }

    // The primary answer to a natural query: the cross-thread STORY (research-
    // plan anchors — threads, who-says-what, gaps) rendered in the stream slot.
    const handleOpenStory = () => {
        const raw = query.trim()
        if (raw.length < 3 || !onOpenStory) return
        track('search_result_click', { segment: 'story', q_len: raw.length })
        onOpenStory(raw)
        close()
    }

    // Searching a country name (e.g. "Venezuela") must FIRST offer to open the
    // COUNTRY itself. Previously the parsed country set countryCode, which HID
    // the Countries section (gated on !countryCode) — so a country search had no
    // path to the country brief, only the cross-thread story. This surfaces the
    // country as the primary action (Pedro 2026-07-06).
    const handleGoToCountry = () => {
        if (!parsedQuery.countryCode) return
        track('search_result_click', { segment: 'country_direct', q_len: query.length })
        handleCountryClick({ code: parsedQuery.countryCode, name: parsedQuery.countryDisplay ?? parsedQuery.countryCode })
    }

    const hasResults = hasVisibleSearchResults(results)
    const degradedSegments = degradedSearchSegments(results)
    const emptyVariant = searchEmptyVariant(results, loading)
    // One query → one obvious primary action; everything else demotes.
    const trimmedQuery = query.trim()
    const { intent, isInvestigative } = classifyQuery({
        raw: trimmedQuery,
        countryCode: parsedQuery.countryCode,
        bareCountry: parsedQuery.bareCountry,
    })
    const canStory = !!onOpenStory && trimmedQuery.length >= 3
    const canInvestigate = !!onStartInvestigation && trimmedQuery.length >= 8
    // "Go to <country>" leads a pure-country query; "Open the story" leads a
    // topic/compound query. The other stays available but visually secondary.
    const countryIsPrimary = intent === 'country'
    const storyIsPrimary = (intent === 'topic' || intent === 'compound') && canStory
    const expandedVariants = (results?.query_variants || [])
        .filter(v => v && v !== results?.normalized_query)
        .slice(0, 3)

    const countryBadge = parsedQuery.countryDisplay
        ? <span className="search-country-badge">in {parsedQuery.countryDisplay}</span>
        : null

    return (
        <div className="search-container" onKeyDown={(e) => e.key === 'Escape' && close()}>
            <div className="search-input-wrapper">
                <span className="search-icon"><Search size={14} /></span>
                <input
                    ref={inputRef}
                    type="text"
                    className="search-input"
                    placeholder="Search topics, countries, people... try 'conflicto Colombia' or 'elections Brazil'"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onFocus={() => results && setIsOpen(true)}
                    onKeyDown={(e) => {
                        // Enter = the story (cross-thread narrative), the
                        // natural-search contract. IME-safe.
                        if (e.key === 'Enter' && !e.nativeEvent.isComposing) handleOpenStory()
                    }}
                />
                {loading && <span className="search-loading">·</span>}
                {query && !loading && (
                    <button className="search-clear" onClick={close}>×</button>
                )}
            </div>

            {isOpen && (
                <div className="search-dropdown">
                    {parsedQuery.countryDisplay && (
                        <div className="search-context-banner">
                            Filtering to: <strong>{parsedQuery.countryDisplay}</strong>
                            <span className="search-context-hint"> · results scoped to this country</span>
                        </div>
                    )}

                    {/* PRIMARY ACTION — exactly one leads, chosen by intent.
                        Pure country → Go to <country>; topic/compound → the story. */}
                    {countryIsPrimary && parsedQuery.countryCode && (
                        <button className="search-query-thread-cta search-query-thread-cta--country" onClick={handleGoToCountry}
                            data-tip="Open the country brief — its threads, voice mix (who covers it) and coverage">
                            <span className="search-query-thread-icon"><Flag code={parsedQuery.countryCode} title={parsedQuery.countryDisplay ?? parsedQuery.countryCode} /></span>
                            <span className="search-query-thread-text">
                                Go to <strong>{parsedQuery.countryDisplay}</strong>
                            </span>
                            <span className="search-query-thread-hint">country brief →</span>
                        </button>
                    )}

                    {storyIsPrimary && (
                        <button className="search-query-thread-cta" onClick={handleOpenStory}
                            data-tip="The cross-thread story: matching live threads, who says what, coverage gaps — press Enter">
                            <span className="search-query-thread-icon">◆</span>
                            <span className="search-query-thread-text">
                                Open the story for <strong>“{trimmedQuery}”</strong>
                            </span>
                            <span className="search-query-thread-hint">↵ cross-thread narrative</span>
                        </button>
                    )}

                    {/* SECONDARY — the OTHER action for this query, still reachable
                        but visually demoted so it doesn't compete with the lead. */}
                    {intent === 'compound' && parsedQuery.countryCode && (
                        <button className="search-query-thread-cta search-query-thread-cta--muted" onClick={handleGoToCountry}
                            data-tip="Open the country brief for this place">
                            <span className="search-query-thread-icon"><Flag code={parsedQuery.countryCode} title={parsedQuery.countryDisplay ?? parsedQuery.countryCode} /></span>
                            <span className="search-query-thread-text">
                                Go to <strong>{parsedQuery.countryDisplay}</strong>
                            </span>
                            <span className="search-query-thread-hint">country brief →</span>
                        </button>
                    )}

                    {countryIsPrimary && canStory && (
                        <button className="search-query-thread-cta search-query-thread-cta--muted" onClick={handleOpenStory}
                            data-tip="The cross-thread story for this query — press Enter">
                            <span className="search-query-thread-icon">◆</span>
                            <span className="search-query-thread-text">
                                Open the story for <strong>“{trimmedQuery}”</strong>
                            </span>
                            <span className="search-query-thread-hint">↵ cross-thread narrative</span>
                        </button>
                    )}

                    {/* Investigation inline ONLY when the query clearly reads
                        investigative; otherwise it lives behind "more". */}
                    {canInvestigate && isInvestigative && (
                        <button
                            className="search-query-thread-cta search-query-thread-cta--muted"
                            data-tip="Open a guided research plan in the Workbench"
                            onClick={() => { onStartInvestigation!(trimmedQuery); close() }}
                        >
                            <span className="search-query-thread-icon">🔬</span>
                            <span className="search-query-thread-text">
                                Start investigation for <strong>“{trimmedQuery}”</strong>
                            </span>
                            <span className="search-query-thread-hint">workbench →</span>
                        </button>
                    )}

                    {expandedVariants.length > 0 && (
                        <div className="search-expansion-banner">
                            {!showVariants ? (
                                <button
                                    type="button"
                                    className="search-expansion-toggle"
                                    data-tip={`Atlas also matched related phrasings of this query: ${expandedVariants.join(' · ')}`}
                                    onClick={() => setShowVariants(true)}
                                >
                                    Results include related phrasings ▾
                                </button>
                            ) : (
                                <>
                                    Related phrasings:
                                    {expandedVariants.map(variant => (
                                        <button
                                            key={variant}
                                            className="search-expansion-chip"
                                            data-tip="Search this phrasing instead"
                                            onClick={() => {
                                                setQuery(variant)
                                                doSearch(variant)
                                            }}
                                        >
                                            {variant}
                                        </button>
                                    ))}
                                </>
                            )}
                        </div>
                    )}

                    {results?.fuzzy_suggestions && results.fuzzy_suggestions.length > 0 && (
                        <div className="search-suggestion-banner">
                            Did you mean:
                            {results.fuzzy_suggestions.slice(0, 3).map(suggestion => (
                                <button
                                    key={`${suggestion.type}-${suggestion.value}`}
                                    className="search-suggestion-chip"
                                    onClick={() => handleFuzzySuggestionClick(suggestion)}
                                >
                                    {suggestion.value}
                                </button>
                            ))}
                        </div>
                    )}

                    {/* Partial degrade: some lanes answered, others FAILED —
                        name the failed ones so absence below is never implied. */}
                    {hasResults && degradedSegments.length > 0 && (
                        <div className="search-degraded-banner">
                            ⚠ Couldn't check {describeDegradedSegments(degradedSegments)} — lookup failed, results may be incomplete
                        </div>
                    )}

                    {/* SECONDARY — the raw matches (threads/countries/people…),
                        kept but visually quieter than the primary action. */}
                    <div className="search-results-secondary">
                    {results?.live_threads && results.live_threads.length > 0 && (
                        <div className="search-section">
                            <div className="search-section-label">Live Threads</div>
                            {results.live_threads.map(t => (
                                <div key={t.id} className="search-item search-item--thread" onClick={() => handleLiveThreadClick(t)}>
                                    <span className="search-item-tag thread-tag">{t.is_umbrella ? 'EVENT' : 'THREAD'}</span>
                                    <span className="search-item-name">
                                        {decodeEntities(t.label)}
                                        {/* N15: court failed/partial → compact under-review dot
                                            (dense row; the shared chip's dot variant). */}
                                        <LabelReviewChip labelStatus={t.label_status} variant="dot" />
                                    </span>
                                    <span className="search-item-meta">
                                        {t.total_signals.toLocaleString()} signals
                                        {t.category ? ` · ${t.category}` : ''}
                                        {t.match === 'partial' ? ' · partial match' : ''}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}

                    {results?.region && (
                        <div className="search-section">
                            <div className="search-section-label">Region</div>
                            <div className="search-item search-item--region" onClick={() => handleRegionClick(results.region!)}>
                                <span className="search-item-tag region-tag">{results.region.emoji}</span>
                                <span className="search-item-name">{results.region.label}</span>
                                <span className="search-item-meta">{results.region.countries.length} countries</span>
                            </div>
                        </div>
                    )}

                    {results?.countries && results.countries.length > 0 && !parsedQuery.countryCode && (
                        <div className="search-section">
                            <div className="search-section-label">Countries</div>
                            {results.countries.map(c => (
                                <div key={c.code} className="search-item" onClick={() => handleCountryClick(c)}>
                                    <span className="search-item-tag country-tag">{c.code}</span>
                                    <span className="search-item-name">{c.name}</span>
                                </div>
                            ))}
                        </div>
                    )}

                    {results?.public_attention && results.public_attention.some(item => isPublicAttentionRelevant(item.title)) && (
                        <div className="search-section">
                            <div className="search-section-label">Public Attention</div>
                            {results.public_attention.filter(item => isPublicAttentionRelevant(item.title)).map(item => (
                                <div key={item.title} className="search-item search-item--attention" onClick={() => handlePublicAttentionClick(item)}>
                                    <span className="search-item-tag wiki-tag">WIKI</span>
                                    <span className="search-item-name">{decodeEntities(item.title.replace(/_/g, ' '))}</span>
                                    <span className="search-item-meta">
                                        {item.country_count} countries · {item.views.toLocaleString()} views
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}

                    {results?.signal_matches && results.signal_matches.length > 0 && (
                        <div className="search-section">
                            <div className="search-section-label">Media Signals</div>
                            {results.signal_matches.map(s => (
                                <div key={s.id} className="search-item search-item--signal" onClick={() => handleSignalMatchClick(s)}>
                                    <span className="search-item-tag country-tag">{s.country || 'GLO'}</span>
                                    <span className="search-item-name">{s.headline ? decodeEntities(s.headline) : `Signal from ${s.source}`}</span>
                                    <span className="search-item-meta">
                                        {s.source}
                                        {s.themes[0] ? ` · ${getThemeLabel(s.themes[0])}` : ''}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}

                    {results?.themes && results.themes.filter(t => t.total_signals > 0).length > 0 && (
                        <div className="search-section">
                            <div className="search-section-label">Narrative threads</div>
                            {results.themes.filter(t => t.total_signals > 0).map((t) => (
                                <div key={t.theme} className="search-item" onClick={() => handleThemeClick(t)}>
                                    <span className="search-item-icon">{getThemeIcon(t.theme)}</span>
                                    <span className="search-item-name">{getThemeLabel(t.theme)}</span>
                                    {countryBadge}
                                    <span className="search-item-meta">
                                        {t.total_signals.toLocaleString()} sig
                                        {!parsedQuery.countryCode && t.top_countries.slice(0, 3).map((c, i) => {
                                            return <span key={c.code}>{i === 0 ? ' · ' : ' '}<Flag code={c.code} title={c.name} /> {c.name}</span>
                                        })}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}

                    {results?.persons && results.persons.filter(p => p.total_signals > 0).length > 0 && (
                        <div className="search-section">
                            <div className="search-section-label">People</div>
                            {results.persons.filter(p => p.total_signals > 0).map((p) => (
                                <div key={p.person} className="search-item" onClick={() => handlePersonClick(p)}>
                                    <span className="search-item-tag person-tag">P</span>
                                    <span className="search-item-name" style={{ textTransform: 'capitalize' }}>
                                        {p.person.toLowerCase()}
                                    </span>
                                    <span className="search-item-meta">
                                        {p.total_signals.toLocaleString()} sig
                                        {p.top_countries.slice(0, 3).map((c, i) => {
                                            return <span key={c.code}>{i === 0 ? ' · ' : ' '}<Flag code={c.code} title={c.name} /> {c.name}</span>
                                        })}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}

                    </div>

                    {/* Empty states, kept honest (gold UI eval batch 3): "No
                        results" is a MEASURED absence and only a clean response
                        may claim it. A degraded response is a FAILED lookup —
                        the same distinction /research/plan renders in words. */}
                    {emptyVariant === 'measured_absence' && (
                        <div className="search-empty">No results for "{parsedQuery.topic}"</div>
                    )}
                    {emptyVariant === 'failed_lookup' && (
                        <div className="search-empty search-empty--degraded">
                            <div>
                                ⚠ Couldn't check {describeDegradedSegments(degradedSegments)}.
                                This is a failed lookup, not a measured absence.
                            </div>
                            <button
                                type="button"
                                className="search-degraded-retry"
                                onClick={() => doSearch(query)}
                            >
                                Retry search
                            </button>
                        </div>
                    )}

                    {/* POWER TOOLS behind a subtle "more" — build-a-thread always,
                        investigation unless it already leads inline. Demoted so the
                        dropdown presents one obvious action, not a wall of CTAs. */}
                    {trimmedQuery.length >= 2 && (() => {
                        const showInvestigateInMore = canInvestigate && !isInvestigative
                        return (
                            <div className="search-more">
                                {!showMore ? (
                                    <button className="search-more-toggle" onClick={() => setShowMore(true)}
                                        data-tip="Power tools: build a custom thread, start a Workbench investigation">
                                        More actions ▾
                                    </button>
                                ) : (
                                    <>
                                        <button className="search-query-thread-cta search-query-thread-cta--muted"
                                            onClick={handleQueryThreadClick}
                                            data-tip="Build a custom Narrative Thread from the exact query text">
                                            <span className="search-query-thread-icon">🧵</span>
                                            <span className="search-query-thread-text">
                                                Build a custom thread for <strong>“{trimmedQuery}”</strong>
                                            </span>
                                            <span className="search-query-thread-hint">power tool →</span>
                                        </button>
                                        {showInvestigateInMore && (
                                            <button className="search-query-thread-cta search-query-thread-cta--muted"
                                                onClick={() => { onStartInvestigation!(trimmedQuery); close() }}
                                                data-tip="Open a guided research plan in the Workbench">
                                                <span className="search-query-thread-icon">🔬</span>
                                                <span className="search-query-thread-text">
                                                    Start investigation for <strong>“{trimmedQuery}”</strong>
                                                </span>
                                                <span className="search-query-thread-hint">workbench →</span>
                                            </button>
                                        )}
                                    </>
                                )}
                            </div>
                        )
                    })()}

                </div>
            )}
        </div>
    )
}
