import { useEffect, useMemo, useState } from 'react'
import { ExternalLink } from 'lucide-react'
import { getThemeLabel } from '../lib/themeLabels'
import { resolveCountryName } from '../lib/countryNames'
import { timeRangeToHours, type TimeRange } from '../lib/timeRanges'
import './PublicAttentionPanel.css'

interface PublicAttentionSelection {
    title: string
    views?: number
    country_count?: number
}

interface SignalMatchResult {
    id: number
    timestamp: string
    country: string
    source: string
    headline: string | null
    themes: string[]
}

interface ThemeResult {
    theme: string
    total_signals: number
}

interface SearchResult {
    public_attention?: Array<{ title: string; views: number; country_count: number }>
    signal_matches?: SignalMatchResult[]
    themes?: ThemeResult[]
}

interface WikiSummary {
    title?: string
    description?: string
    extract?: string
    content_urls?: { desktop?: { page?: string } }
}

interface PublicAttentionPanelProps {
    item: PublicAttentionSelection
    timeRange: TimeRange
    onClose: () => void
    onThemeSelect?: (theme: string) => void
    onCountrySelect?: (code: string) => void
}

function cleanTitle(title: string): string {
    return title.replace(/_/g, ' ').trim()
}

function formatCount(n?: number): string {
    if (!n) return '0'
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}m`
    if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
    return String(n)
}

function timeAgo(iso: string): string {
    const ms = Date.now() - new Date(iso).getTime()
    if (!Number.isFinite(ms) || ms < 0) return 'now'
    const minutes = Math.floor(ms / 60000)
    if (minutes < 60) return `${minutes}m`
    const hours = Math.floor(minutes / 60)
    return `${hours}h`
}

export function PublicAttentionPanel({ item, timeRange, onClose, onThemeSelect, onCountrySelect }: PublicAttentionPanelProps) {
    const title = cleanTitle(item.title)
    const hours = timeRangeToHours(timeRange)
    const requestKey = `${title}:${hours}`
    const [panelData, setPanelData] = useState<{
        key: string
        searchData: SearchResult | null
        wikiSummary: WikiSummary | null
    } | null>(null)

    useEffect(() => {
        const controller = new AbortController()

        const searchUrl = `/api/v2/search/unified?q=${encodeURIComponent(title)}&hours=${hours}`
        const wikiTitle = encodeURIComponent(item.title.replace(/ /g, '_'))
        const wikiUrl = `https://en.wikipedia.org/api/rest_v1/page/summary/${wikiTitle}`

        Promise.allSettled([
            fetch(searchUrl, { signal: controller.signal }).then(r => r.ok ? r.json() : null),
            fetch(wikiUrl, { signal: controller.signal }).then(r => r.ok ? r.json() : null)
        ])
            .then(([searchResult, wikiResult]) => {
                setPanelData({
                    key: requestKey,
                    searchData: searchResult.status === 'fulfilled' ? searchResult.value : null,
                    wikiSummary: wikiResult.status === 'fulfilled' ? wikiResult.value : null
                })
            })
            .catch(() => {})

        return () => controller.abort()
    }, [title, item.title, hours, requestKey])

    const loading = panelData?.key !== requestKey
    const searchData = loading ? null : panelData?.searchData ?? null
    const wikiSummary = loading ? null : panelData?.wikiSummary ?? null

    const attention = useMemo(() => {
        const fromSearch = searchData?.public_attention?.find(a => cleanTitle(a.title).toLowerCase() === title.toLowerCase())
        return {
            views: fromSearch?.views ?? item.views,
            countryCount: fromSearch?.country_count ?? item.country_count
        }
    }, [item.country_count, item.views, searchData?.public_attention, title])

    const signalMatches = useMemo(() => searchData?.signal_matches ?? [], [searchData?.signal_matches])

    const countries = useMemo(() => {
        const counts = new Map<string, number>()
        signalMatches.forEach(signal => {
            if (!signal.country) return
            counts.set(signal.country, (counts.get(signal.country) ?? 0) + 1)
        })
        return Array.from(counts.entries())
            .map(([code, count]) => ({ code, count, name: resolveCountryName(code) }))
            .sort((a, b) => b.count - a.count)
            .slice(0, 8)
    }, [signalMatches])

    const themes = useMemo(() => {
        const counts = new Map<string, number>()
        signalMatches.forEach(signal => {
            signal.themes?.forEach(theme => counts.set(theme, (counts.get(theme) ?? 0) + 1))
        })
        searchData?.themes?.forEach(theme => {
            if (theme.total_signals > 0) counts.set(theme.theme, Math.max(counts.get(theme.theme) ?? 0, theme.total_signals))
        })
        return Array.from(counts.entries())
            .map(([theme, count]) => ({ theme, count }))
            .sort((a, b) => b.count - a.count)
            .slice(0, 10)
    }, [searchData?.themes, signalMatches])

    const connectionNote = countries.length > 1 && themes.length > 0
        ? `${countries.slice(0, 3).map(c => c.name).join(', ')} are connected here because their recent signals mention "${title}" while also sharing themes like ${themes.slice(0, 3).map(t => getThemeLabel(t.theme)).join(', ')}.`
        : signalMatches.length > 0
            ? `Atlas found recent media signals that mention "${title}" and mapped their source countries, themes, and headlines.`
            : `Atlas found public attention for "${title}" but no matching media signals in the selected time window yet.`

    return (
        <div className="public-attention-panel">
            <div className="pap-header">
                <div>
                    <div className="pap-kicker">PUBLIC ATTENTION</div>
                    <h2>{title}</h2>
                </div>
                <button className="pap-close" onClick={onClose} data-tip="Close public attention panel">x</button>
            </div>

            <div className="pap-metrics">
                <div>
                    <span className="pap-metric-value">{formatCount(attention.views)}</span>
                    <span className="pap-metric-label">wiki views</span>
                </div>
                <div>
                    <span className="pap-metric-value">{attention.countryCount ?? countries.length}</span>
                    <span className="pap-metric-label">countries</span>
                </div>
                <div>
                    <span className="pap-metric-value">{signalMatches.length}</span>
                    <span className="pap-metric-label">media signals</span>
                </div>
            </div>

            {loading && (
                <div className="pap-loading">
                    {Array.from({ length: 6 }).map((_, i) => <span key={i} />)}
                </div>
            )}

            {!loading && (
                <div className="pap-body">
                    <section className="pap-section pap-summary">
                        <div className="pap-section-label">What is it?</div>
                        {wikiSummary?.extract ? (
                            <>
                                {wikiSummary.description && <div className="pap-description">{wikiSummary.description}</div>}
                                <p>{wikiSummary.extract}</p>
                                {wikiSummary.content_urls?.desktop?.page && (
                                    <a className="pap-source-link" href={wikiSummary.content_urls.desktop.page} target="_blank" rel="noopener noreferrer">
                                        Wikipedia <ExternalLink size={12} />
                                    </a>
                                )}
                            </>
                        ) : (
                            <p>Atlas is tracking this as a public-attention topic. No Wikipedia summary was available from the client request.</p>
                        )}
                    </section>

                    <section className="pap-section">
                        <div className="pap-section-label">Countries talking about it</div>
                        {countries.length > 0 ? (
                            <div className="pap-country-list">
                                {countries.map(country => (
                                    <button key={country.code} className="pap-country-row" onClick={() => onCountrySelect?.(country.code)}>
                                        <span>{country.name}</span>
                                        <strong>{country.count}</strong>
                                    </button>
                                ))}
                            </div>
                        ) : (
                            <div className="pap-empty">No country-level media matches in this window.</div>
                        )}
                    </section>

                    <section className="pap-section">
                        <div className="pap-section-label">Why these signals connect</div>
                        <p className="pap-connection-note">{connectionNote}</p>
                        {themes.length > 0 && (
                            <div className="pap-theme-list">
                                {themes.map(theme => (
                                    <button key={theme.theme} className="pap-theme-chip" onClick={() => onThemeSelect?.(theme.theme)}>
                                        {getThemeLabel(theme.theme)}
                                        <span>{formatCount(theme.count)}</span>
                                    </button>
                                ))}
                            </div>
                        )}
                    </section>

                    <section className="pap-section">
                        <div className="pap-section-label">What they are saying</div>
                        {signalMatches.length > 0 ? (
                            <div className="pap-signal-list">
                                {signalMatches.slice(0, 10).map(signal => (
                                    <div key={signal.id} className="pap-signal-row">
                                        <div className="pap-signal-meta">
                                            <span>{signal.country || 'GLO'}</span>
                                            <span>{signal.source}</span>
                                            <span>{timeAgo(signal.timestamp)}</span>
                                        </div>
                                        <div className="pap-signal-headline">{signal.headline || 'Untitled signal'}</div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="pap-empty">No recent media headlines matched this item.</div>
                        )}
                    </section>
                </div>
            )}
        </div>
    )
}
