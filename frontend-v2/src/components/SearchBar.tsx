import { useState, useEffect, useCallback, useRef } from 'react'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import { useFocus } from '../contexts/FocusContext'
import type { ConceptFilter, RegionFilter } from '../contexts/FocusContext'
import { Search } from 'lucide-react'
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
      return { topic: topic.length >= 2 ? topic : q, countryCode: code, countryDisplay: display }
    }
  }
  return { topic: q, countryCode: null, countryDisplay: null }
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

interface SearchResult {
    themes: ThemeResult[]
    persons: PersonResult[]
    countries: CountryResult[]
    concepts?: ConceptResult[]
    concept_suggestions?: { slug: string; label: string; description: string }[]
    region?: RegionResult | null
}

interface SearchBarProps {
    onThemeSelect: (theme: string, countryCode?: string, countryName?: string) => void
    onCountrySelect: (code: string) => void
}

export function SearchBar({ onThemeSelect, onCountrySelect }: SearchBarProps) {
    const [query, setQuery] = useState('')
    const [results, setResults] = useState<SearchResult | null>(null)
    const [parsedQuery, setParsedQuery] = useState<ParsedQuery>({ topic: '', countryCode: null, countryDisplay: null })
    const [isOpen, setIsOpen] = useState(false)
    const [loading, setLoading] = useState(false)
    const inputRef = useRef<HTMLInputElement>(null)
    const { setFocus, setMapFlyCountry, setCountry, setTheme, setConcept, setRegion } = useFocus()

    const doSearch = useCallback(async (q: string) => {
        if (q.length < 2) {
            setResults(null)
            setIsOpen(false)
            setParsedQuery({ topic: q, countryCode: null, countryDisplay: null })
            return
        }
        const parsed = parseCompoundQuery(q)
        setParsedQuery(parsed)
        const searchQ = parsed.topic.length >= 2 ? parsed.topic : q
        setLoading(true)
        try {
            const res = await fetch(`/api/v2/search/unified?q=${encodeURIComponent(searchQ)}&hours=168`)
            if (res.ok) {
                setResults(await res.json())
            } else {
                // Fallback to basic search if unified endpoint not available yet
                const fallback = await fetch(`/api/v2/search?q=${encodeURIComponent(searchQ)}&hours=168`)
                setResults(fallback.ok ? await fallback.json() : { themes: [], persons: [], countries: [] })
            }
            setIsOpen(true)
        } catch {
            // silent
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        const t = setTimeout(() => { if (query) doSearch(query) }, 300)
        return () => clearTimeout(t)
    }, [query, doSearch])

    const close = () => {
        setIsOpen(false)
        setQuery('')
        setResults(null)
        setParsedQuery({ topic: '', countryCode: null, countryDisplay: null })
    }

    const handleThemeClick = (t: ThemeResult) => {
        if (parsedQuery.countryCode) {
            setCountry(parsedQuery.countryCode)
            setTheme(t.theme)
            setMapFlyCountry(parsedQuery.countryCode)
        } else {
            setFocus('theme', t.theme, getThemeLabel(t.theme))
            if (t.top_countries[0]) setMapFlyCountry(t.top_countries[0].code)
        }
        onThemeSelect(t.theme)
        close()
    }

    const handlePersonClick = (p: PersonResult) => {
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

    const handleConceptClick = (c: ConceptResult) => {
        const concept: ConceptFilter = { slug: c.slug, themes: c.themes, label: c.label }
        if (parsedQuery.countryCode) {
            setCountry(parsedQuery.countryCode)
            setConcept(concept)
            setMapFlyCountry(parsedQuery.countryCode)
        } else {
            setConcept(concept)
        }
        if (c.themes[0]) onThemeSelect(c.themes[0])
        close()
    }

    const handleRegionClick = (r: RegionResult) => {
        const region: RegionFilter = { slug: r.slug, label: r.label, countries: r.countries }
        setRegion(region)
        close()
    }

    const hasResults = results && (
        results.themes.length > 0 ||
        results.persons.length > 0 ||
        results.countries.length > 0 ||
        (results.concepts?.length ?? 0) > 0 ||
        results.region != null
    )

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
                    placeholder="Search topics, countries, people... try 'elections Colombia'"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onFocus={() => results && setIsOpen(true)}
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

                    {results?.concepts && results.concepts.length > 0 && (
                        <div className="search-section">
                            <div className="search-section-label">Concepts</div>
                            {results.concepts.map(c => (
                                <div key={c.slug} className="search-item search-item--concept" onClick={() => handleConceptClick(c)}>
                                    <span className="search-item-tag concept-tag">CON</span>
                                    <span className="search-item-name">{c.label}</span>
                                    {countryBadge}
                                    <span className="search-item-meta search-item-meta--desc">{c.description.slice(0, 60)}…</span>
                                </div>
                            ))}
                        </div>
                    )}

                    {results?.themes && results.themes.length > 0 && (
                        <div className="search-section">
                            <div className="search-section-label">Themes</div>
                            {results.themes.map((t) => (
                                <div key={t.theme} className="search-item" onClick={() => handleThemeClick(t)}>
                                    <span className="search-item-icon">{getThemeIcon(t.theme)}</span>
                                    <span className="search-item-name">{getThemeLabel(t.theme)}</span>
                                    {countryBadge}
                                    <span className="search-item-meta">
                                        {t.total_signals.toLocaleString()} sig
                                        {!parsedQuery.countryCode && t.top_countries.slice(0, 3).map((c, i) => {
                                            const flag = c.code.length === 2
                                                ? String.fromCodePoint(...c.code.toUpperCase().split('').map(ch => 0x1F1E6 + ch.charCodeAt(0) - 65))
                                                : '🌐'
                                            return <span key={c.code}>{i === 0 ? ' · ' : ' '}{flag} {c.name}</span>
                                        })}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}

                    {results?.persons && results.persons.length > 0 && (
                        <div className="search-section">
                            <div className="search-section-label">People</div>
                            {results.persons.map((p) => (
                                <div key={p.person} className="search-item" onClick={() => handlePersonClick(p)}>
                                    <span className="search-item-tag person-tag">P</span>
                                    <span className="search-item-name" style={{ textTransform: 'capitalize' }}>
                                        {p.person.toLowerCase()}
                                    </span>
                                    <span className="search-item-meta">
                                        {p.total_signals.toLocaleString()} sig
                                        {p.top_countries.slice(0, 3).map((c, i) => {
                                            const flag = c.code.length === 2
                                                ? String.fromCodePoint(...c.code.toUpperCase().split('').map(ch => 0x1F1E6 + ch.charCodeAt(0) - 65))
                                                : '🌐'
                                            return <span key={c.code}>{i === 0 ? ' · ' : ' '}{flag} {c.name}</span>
                                        })}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}

                    {!hasResults && !loading && (
                        <div className="search-empty">No results for "{parsedQuery.topic}"</div>
                    )}
                </div>
            )}
        </div>
    )
}
