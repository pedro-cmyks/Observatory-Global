import { useState, useEffect, useRef, useCallback } from 'react'
import { Search } from 'lucide-react'
import './CompareSearchModal.css'

interface TopCountry { code: string; name: string; count: number }
interface PersonResult { person: string; total_signals: number; top_countries: TopCountry[] }

interface Props {
    onSelect: (name: string) => void
    onClose: () => void
}

function formatCount(n: number): string {
    if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
    return String(n)
}

export function CompareSearchModal({ onSelect, onClose }: Props) {
    const [query, setQuery] = useState('')
    const [results, setResults] = useState<PersonResult[]>([])
    const [loading, setLoading] = useState(false)
    const inputRef = useRef<HTMLInputElement>(null)
    const containerRef = useRef<HTMLDivElement>(null)

    useEffect(() => { inputRef.current?.focus() }, [])

    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
                onClose()
            }
        }
        document.addEventListener('mousedown', handler)
        return () => document.removeEventListener('mousedown', handler)
    }, [onClose])

    const search = useCallback(async (q: string) => {
        if (q.length < 2) { setResults([]); return }
        setLoading(true)
        try {
            const res = await fetch(`/api/v2/search/unified?q=${encodeURIComponent(q)}&hours=168`)
            if (res.ok) {
                const data = await res.json()
                setResults((data.persons ?? []).slice(0, 8))
            }
        } catch {
            // silent
        } finally {
            setLoading(false)
        }
    }, [])

    useEffect(() => {
        const t = setTimeout(() => search(query), 300)
        return () => clearTimeout(t)
    }, [query, search])

    return (
        <div className="csm-container" ref={containerRef}>
            <div className="csm-input-row">
                <Search size={13} className="csm-icon" />
                <input
                    ref={inputRef}
                    className="csm-input"
                    placeholder="Search person to compare…"
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    onKeyDown={e => e.key === 'Escape' && onClose()}
                />
                {loading && <span className="csm-spinner" />}
            </div>

            {results.length > 0 && (
                <ul className="csm-results">
                    {results.map(p => (
                        <li
                            key={p.person}
                            className="csm-result-row"
                            onClick={() => { onSelect(p.person); onClose() }}
                        >
                            <span className="csm-name">{p.person}</span>
                            <span className="csm-meta">
                                {formatCount(p.total_signals)} signals
                                {p.top_countries[0] && (
                                    <> · {p.top_countries[0].name}</>
                                )}
                            </span>
                        </li>
                    ))}
                </ul>
            )}

            {query.length >= 2 && !loading && results.length === 0 && (
                <div className="csm-empty">No results for "{query}"</div>
            )}
        </div>
    )
}
