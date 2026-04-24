import { useState, useEffect, useCallback, useRef } from 'react'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import { useFocus } from '../contexts/FocusContext'
import { Search } from 'lucide-react'
import './SearchBar.css'

interface TopCountry {
    code: string
    name: string
    count: number
}

interface ThemeResult {
    theme: string
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

interface SearchResult {
    themes: ThemeResult[]
    persons: PersonResult[]
    countries: CountryResult[]
}

interface SearchBarProps {
    onThemeSelect: (theme: string, countryCode?: string, countryName?: string) => void
    onCountrySelect: (code: string) => void
}

export function SearchBar({ onThemeSelect, onCountrySelect }: SearchBarProps) {
    const [query, setQuery] = useState('')
    const [results, setResults] = useState<SearchResult | null>(null)
    const [isOpen, setIsOpen] = useState(false)
    const [loading, setLoading] = useState(false)
    const inputRef = useRef<HTMLInputElement>(null)
    const { setFocus, setMapFlyCountry } = useFocus()

    const doSearch = useCallback(async (q: string) => {
        if (q.length < 2) {
            setResults(null)
            setIsOpen(false)
            return
        }
        setLoading(true)
        try {
            const res = await fetch(`/api/v2/search?q=${encodeURIComponent(q)}&hours=168`)
            if (res.ok) {
                const data = await res.json()
                setResults(data)
                setIsOpen(true)
            }
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
    }

    const handleThemeClick = (t: ThemeResult) => {
        const top = t.top_countries[0]
        setFocus('theme', t.theme, getThemeLabel(t.theme))
        onThemeSelect(t.theme)
        if (top) setMapFlyCountry(top.code)
        close()
    }

    const handlePersonClick = (p: PersonResult) => {
        const top = p.top_countries[0]
        setFocus('person', p.person, p.person)
        if (top) setMapFlyCountry(top.code)
        // EntityPanel opens via focus.type === 'person' in App.tsx — no CountryBrief
        close()
    }

    const handleCountryClick = (c: CountryResult) => {
        setFocus('country', c.code, c.name)
        setMapFlyCountry(c.code)
        onCountrySelect(c.code)
        close()
    }

    const hasResults = results && (
        results.themes.length > 0 ||
        results.persons.length > 0 ||
        results.countries.length > 0
    )

    return (
        <div className="search-container" onKeyDown={(e) => e.key === 'Escape' && close()}>
            <div className="search-input-wrapper">
                <span className="search-icon"><Search size={14} /></span>
                <input
                    ref={inputRef}
                    type="text"
                    className="search-input"
                    placeholder="Search topics, countries, people..."
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
                    {results?.countries && results.countries.length > 0 && (
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

                    {results?.themes && results.themes.length > 0 && (
                        <div className="search-section">
                            <div className="search-section-label">Themes</div>
                            {results.themes.map((t) => (
                                <div key={t.theme} className="search-item" onClick={() => handleThemeClick(t)}>
                                    <span className="search-item-icon">{getThemeIcon(t.theme)}</span>
                                    <span className="search-item-name">{getThemeLabel(t.theme)}</span>
                                    <span className="search-item-meta">
                                        {t.total_signals.toLocaleString()} sig
                                        {t.top_countries[0] && ` · ${t.top_countries[0].code}`}
                                        {t.top_countries[1] && ` ${t.top_countries[1].code}`}
                                        {t.top_countries[2] && ` ${t.top_countries[2].code}`}
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
                                        {p.top_countries[0] && ` · ${p.top_countries[0].code}`}
                                    </span>
                                </div>
                            ))}
                        </div>
                    )}

                    {!hasResults && !loading && (
                        <div className="search-empty">No results for "{query}"</div>
                    )}
                </div>
            )}
        </div>
    )
}
