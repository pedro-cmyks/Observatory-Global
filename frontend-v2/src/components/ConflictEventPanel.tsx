import { useEffect, useState } from 'react'
import { resolveCountryName } from '../lib/countryNames'
import { conflictCountryCode } from '../lib/conflictEvents'
import './ConflictEventPanel.css'

/**
 * T3.3 P-FOCUS: when a conflict event is clicked, the EVENT is the subject —
 * "this event, in <country>" — not the country swallowing it. Shows the event
 * identity (type / actors / place / date) and, as CONTEXT below, the living
 * narrative threads in that country. Additive: the map still flies there, but
 * we lead with the event.
 */
export interface ConflictEventFocus {
    eventId?: string
    type: string
    country: string
    place: string
    actor1: string
    actor2: string
    date: string
    fatalities: number
    mentions: number
    lat: number | null
    lon: number | null
}

interface ContextThread {
    thread_id: string
    label: string
    signal_count: number
    basis?: 'linked' | 'geo_time'
}

interface Props {
    event: ConflictEventFocus
    onClose: () => void
    onThemeSelect?: (threadId: string) => void
    onCountrySelect?: (code: string) => void
    timeRangeHours: number
}

function renderThreadList(threads: ContextThread[], onThemeSelect?: (id: string) => void) {
    return (
        <div className="cep-threads">
            {threads.slice(0, 5).map(t => (
                <button
                    key={t.thread_id}
                    className="cep-thread"
                    onClick={() => onThemeSelect?.(t.thread_id)}
                    data-tip={`Open "${t.label}"`}
                >
                    <span className="cep-thread-label">{t.label}</span>
                    <span className="cep-thread-count">
                        {t.signal_count > 999 ? `${(t.signal_count / 1000).toFixed(1)}k` : t.signal_count}
                    </span>
                </button>
            ))}
        </div>
    )
}

function fmtDate(iso: string): string {
    try {
        return new Date(iso).toLocaleString(undefined, {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
        })
    } catch { return iso }
}

export function ConflictEventPanel({ event, onClose, onThemeSelect, onCountrySelect, timeRangeHours }: Props) {
    // #232: two tiers, each with an honest basis. `linked` = threads directly
    // bound to THIS event (shared source article); `geo` = other threads active
    // in the event's country over the window (geographic context, not an event
    // join). Kept separate so the panel never presents "same country" as
    // "about this event".
    const [linked, setLinked] = useState<ContextThread[]>([])
    const [geo, setGeo] = useState<ContextThread[]>([])
    // Normalize to a 2-letter code: GDELT markers carry one, ACLED carries a
    // full name — the endpoint and country focus both need the code.
    const countryCode = conflictCountryCode({ location: { country: event.country } })
    const countryName = event.country ? resolveCountryName(countryCode || event.country) : ''

    useEffect(() => {
        if (!countryCode && !event.eventId) { setLinked([]); setGeo([]); return }
        let ignore = false
        const params = new URLSearchParams({ hours: String(timeRangeHours), limit: '6' })
        if (event.eventId) params.set('event_id', event.eventId)
        if (countryCode) params.set('country_code', countryCode)
        fetch(`/api/v2/conflict-event/threads?${params.toString()}`)
            .then(r => (r.ok ? r.json() : null))
            .then(d => {
                if (ignore) return
                setLinked(d?.linked ?? [])
                setGeo(d?.geo_time ?? [])
            })
            .catch(() => { if (!ignore) { setLinked([]); setGeo([]) } })
        return () => { ignore = true }
    }, [countryCode, event.eventId, timeRangeHours])

    const actors = [event.actor1, event.actor2].filter(Boolean).join(' → ')

    return (
        <div className="conflict-event-panel">
            <div className="cep-header">
                <span className="cep-kicker">CONFLICT EVENT</span>
                <button className="cep-close" onClick={onClose} aria-label="Close">×</button>
            </div>

            <h2 className="cep-title">{event.type || 'Conflict event'}</h2>
            {actors && <div className="cep-actors">{actors}</div>}

            <div className="cep-meta">
                {event.place && <span className="cep-place">{event.place}</span>}
                {event.date && <span className="cep-date">{fmtDate(event.date)}</span>}
            </div>
            <div className="cep-stats">
                <span className={event.fatalities > 0 ? 'cep-fatal' : ''}>
                    {event.fatalities} fatalities
                </span>
                <span>{event.mentions} mentions</span>
            </div>

            {/* Country as CONTEXT, not the subject (P-FOCUS). */}
            <div className="cep-context">
                <div className="cep-context-label">
                    This event lives in{' '}
                    {countryCode ? (
                        <button className="cep-country-link" onClick={() => onCountrySelect?.(countryCode)}
                            data-tip={`Focus ${countryName} — map, threads and dock re-scope to it`}>
                            {countryName}
                        </button>
                    ) : (event.country || 'an unknown country')}
                </div>

                {/* Tier 1 — direct event->thread binding (shared source article). */}
                {linked.length > 0 && (
                    <div className="cep-tier">
                        <div className="cep-tier-label" data-tip="Threads that carry the article reporting this event">
                            LINKED COVERAGE
                        </div>
                        {renderThreadList(linked, onThemeSelect)}
                    </div>
                )}

                {/* Tier 2 — geographic context (labeled, never as "about this event"). */}
                {geo.length > 0 && (
                    <div className="cep-tier">
                        <div className="cep-tier-label" data-tip="Other narrative threads active in this country during the window — geographic context, not a direct link to this event">
                            {linked.length > 0 ? `ALSO ACTIVE IN ${(countryName || 'THIS COUNTRY').toUpperCase()}` : `ACTIVE IN ${(countryName || 'THIS COUNTRY').toUpperCase()}`}
                        </div>
                        {renderThreadList(geo, onThemeSelect)}
                    </div>
                )}

                {linked.length === 0 && geo.length === 0 && (
                    <div className="cep-empty">
                        No narrative thread is joined to this event yet, and no active
                        thread in {countryName || 'this country'} covers the window.
                    </div>
                )}
            </div>
        </div>
    )
}
