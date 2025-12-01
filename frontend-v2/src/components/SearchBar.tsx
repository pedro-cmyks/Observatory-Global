import { useState, useEffect, useCallback } from 'react'
import { getThemeLabel } from '../lib/themeLabels'
import './SearchBar.css'

interface SearchResult {
    themes: { theme: string; country: string; count: number }[]
    sources: { source: string; country: string; count: number }[]
    countries: { code: string; name: string }[]
}

interface SearchBarProps {
    onThemeSelect: (theme: string, country?: string) => void
    onCountrySelect: (code: string) => void
}

export function SearchBar({ onThemeSelect, onCountrySelect }: SearchBarProps) {
    const [query, setQuery] = useState('')
    const [results, setResults] = useState<SearchResult | null>(null)
    const [isOpen, setIsOpen] = useState(false)
    const [loading, setLoading] = useState(false)

    const search = useCallback(async (q: string) => {
        if (q.length < 2) {
            setResults(null)
            return
        }

        setLoading(true)
        try {
            const res = await fetch(`http://localhost:8000/api/v2/search?q=${encodeURIComponent(q)}&hours=168`)
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
        onThemeSelect(theme, country)
        setIsOpen(false)
        setQuery('')
    }

    const handleCountryClick = (code: string) => {
        onCountrySelect(code)
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
                                    onClick={() => handleCountryClick(c.code)}
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
                                >
                                    <span className="search-item-icon">🔗</span>
                                    <span>{s.source}</span>
                                    <span className="search-item-meta">{s.count} signals</span>
                                </div>
                            ))}
                        </div>
                    )}

                    {results.themes.length === 0 && results.countries.length === 0 && results.sources.length === 0 && (
                        <div className="search-empty">No results found</div>
                    )}
                </div>
            )}
        </div>
    )
}
