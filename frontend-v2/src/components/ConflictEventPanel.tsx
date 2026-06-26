import { useEffect, useState } from 'react'
import { resolveCountryName } from '../lib/countryNames'
import './ConflictEventPanel.css'

/**
 * T3.3 P-FOCUS: when a conflict event is clicked, the EVENT is the subject —
 * "this event, in <country>" — not the country swallowing it. Shows the event
 * identity (type / actors / place / date) and, as CONTEXT below, the living
 * narrative threads in that country. Additive: the map still flies there, but
 * we lead with the event.
 */
export interface ConflictEventFocus {
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
}

interface Props {
    event: ConflictEventFocus
    onClose: () => void
    onThemeSelect?: (threadId: string) => void
    onCountrySelect?: (code: string) => void
    timeRangeHours: number
}

function fmtDate(iso: string): string {
    try {
        return new Date(iso).toLocaleString(undefined, {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
        })
    } catch { return iso }
}

export function ConflictEventPanel({ event, onClose, onThemeSelect, onCountrySelect, timeRangeHours }: Props) {
    const [threads, setThreads] = useState<ContextThread[]>([])
    const countryName = event.country ? resolveCountryName(event.country) : ''

    useEffect(() => {
        if (!event.country) { setThreads([]); return }
        let ignore = false
        fetch(`/api/v2/threads?hours=${timeRangeHours}&limit=6&country_code=${event.country}`)
            .then(r => (r.ok ? r.json() : null))
            .then(d => { if (!ignore) setThreads(d?.threads ?? []) })
            .catch(() => { if (!ignore) setThreads([]) })
        return () => { ignore = true }
    }, [event.country, timeRangeHours])

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
                    {event.country ? (
                        <button className="cep-country-link" onClick={() => onCountrySelect?.(event.country)}>
                            {countryName}
                        </button>
                    ) : 'an unknown country'}
                    {threads.length > 0 ? ' — narrative threads there:' : ''}
                </div>
                {threads.length > 0 ? (
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
                ) : (
                    <div className="cep-empty">No narrative threads cleared the gate here in this window.</div>
                )}
            </div>
        </div>
    )
}
