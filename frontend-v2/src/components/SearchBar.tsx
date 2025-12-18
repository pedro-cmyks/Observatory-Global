import { useState, useEffect, useCallback } from 'react'
import { getThemeLabel } from '../lib/themeLabels'
import { useFocus } from '../contexts/FocusContext'
import './SearchBar.css'

interface SearchResult {
    themes: { theme: string; country: string; count: number }[]
    sources: { source: string; country: string; count: number }[]
    countries: { code: string; name: string }[]
    persons: { person: string; country: string; count: number }[]
}

interface SearchBarProps {
    onThemeSelect: (theme: string, country?: string) => void
    onCountrySelect: (code: string) => void
    onSourceSelect: (source: string) => void
}

export function SearchBar({ onThemeSelect, onCountrySelect, onSourceSelect }: SearchBarProps) {
    const [query, setQuery] = useState('')
    const [results, setResults] = useState<SearchResult | null>(null)
    const [isOpen, setIsOpen] = useState(false)
    const [loading, setLoading] = useState(false)
    const { setFocus } = useFocus()

    const search = useCallback(async (q: string) => {
        if (q.length < 2) {
            setResults(null)
            return
        }

        setLoading(true)
        try {
            const res = await fetch(`/api/v2/search?q=${encodeURIComponent(q)}&hours=168`)
            const data = await res.json()
            setResults(data)
            setIsOpen(true)
        } catch (error) {
            console.error('Search failed:', error)
        }
        setLoading(false)
    }, [])

    // Debounced search
    useEffect(() => {
        const timer = setTimeout(() => {
            if (query) search(query)
        }, 300)
        return () => clearTimeout(timer)
    }, [query, search])

    const handleThemeClick = (theme: string, country?: string) => {
        setFocus('theme', theme, getThemeLabel(theme))
        onThemeSelect(theme, country)
        setIsOpen(false)
        setQuery('')
    }

    const handleCountryClick = (code: string, name: string) => {
        setFocus('country', code, name)
        onCountrySelect(code)
        setIsOpen(false)
        setQuery('')
    }

    const handlePersonClick = (person: string, country?: string) => {
        setFocus('person', person, person)
        // For now, persons trigger theme-like behavior
        console.log(`Selected person: ${person} in ${country || 'any country'}`)
        setIsOpen(false)
        setQuery('')
    }

    return (
        <div className="search-container">
            <div className="search-input-wrapper">
                <span className="search-icon">🔍</span>
                <input
                    type="text"
                    className="search-input"
                    placeholder="Search themes, countries, sources..."
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onFocus={() => results && setIsOpen(true)}
                />
                {loading && <span className="search-loading">...</span>}
            </div>

            {isOpen && results && (
                <div className="search-dropdown">
                    {results.countries.length > 0 && (
                        <div className="search-section">
                            <h4>Countries</h4>
                            {results.countries.map(c => (
                                <div
                                    key={c.code}
                                    className="search-item"
                                    onClick={() => handleCountryClick(c.code, c.name)}
                                >
                                    <span className="search-item-icon">🌍</span>
                                    <span>{c.name}</span>
                                    <span className="search-item-code">{c.code}</span>
                                </div>
                            ))}
                        </div>
                    )}

                    {results.themes.length > 0 && (
                        <div className="search-section">
                            <h4>Themes</h4>
                            {results.themes.slice(0, 8).map((t, i) => (
                                <div
                                    key={`${t.theme}-${t.country}-${i}`}
                                    className="search-item"
                                    onClick={() => handleThemeClick(t.theme, t.country)}
                                >
                                    <span className="search-item-icon">📰</span>
                                    <span>{getThemeLabel(t.theme)}</span>
                                    <span className="search-item-meta">{t.country} • {t.count}</span>
                                </div>
                            ))}
                        </div>
                    )}

                    {results.sources.length > 0 && (
                        <div className="search-section">
                            <h4>Sources</h4>
                            {results.sources.slice(0, 5).map((s, i) => (
                                <div
                                    key={`${s.source}-${i}`}
                                    className="search-item"
                                    onClick={() => {
                                        setFocus('source', s.source, s.source)
                                        onSourceSelect(s.source)
                                        setIsOpen(false)
                                        setQuery('')
                                    }}
                                >
                                    <span className="search-item-icon">🔗</span>
                                    <span>{s.source}</span>
                                    <span className="search-item-meta">{s.count} signals</span>
                                </div>
                            ))}
                        </div>
                    )}

                    {results.persons && results.persons.length > 0 && (
                        <div className="search-section">
                            <h4>People</h4>
                            {results.persons.slice(0, 5).map((p, i) => (
                                <div
                                    key={`${p.person}-${i}`}
                                    className="search-item"
                                    onClick={() => handlePersonClick(p.person, p.country)}
                                >
                                    <span className="search-item-icon">👤</span>
                                    <span style={{ textTransform: 'capitalize' }}>{p.person.toLowerCase()}</span>
                                    <span className="search-item-meta">{p.country} • {p.count}</span>
                                </div>
                            ))}
                        </div>
                    )}

                    {results.themes.length === 0 && results.countries.length === 0 && results.sources.length === 0 && (!results.persons || results.persons.length === 0) && (
                        <div className="search-empty">No results found</div>
                    )}
                </div>
            )}
        </div>
    )
}
