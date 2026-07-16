// S3 (time-as-dimension, 2026-07-05): click a country while the globe is
// SCRUBBED to a past day → that day's receipts. Two honest tiers from
// /api/v2/evidence/day: 'hot' (live window) and 'archive' (frozen
// distinct-source sample from the external archive — labeled as a sample,
// never presented as exhaustive coverage).
import { useEffect, useState } from 'react'
import { resolveCountryName } from '../lib/countryNames'
import { track } from '../lib/telemetry'
import './DayEvidencePanel.css'

interface DayEvidenceItem {
    headline: string
    source?: string | null
    url?: string | null
    country_code?: string | null
    timestamp?: string | null
    sentiment?: number | null
}

interface DayEvidenceResponse {
    contract: string
    day: string
    country: string | null
    tier: 'hot' | 'archive' | null
    items: DayEvidenceItem[]
    reason?: string | null
    note?: string | null
}

export function DayEvidencePanel({ day, country, onClose, onOpenLive }: {
    day: string
    country: string
    onClose: () => void
    onOpenLive: () => void
}) {
    const [data, setData] = useState<DayEvidenceResponse | null>(null)
    const [error, setError] = useState(false)

    useEffect(() => {
        let alive = true
        setData(null)
        setError(false)
        track('scrub_evidence_open', { tier_requested: 'auto' })
        fetch(`/api/v2/evidence/day?day=${day}&country=${country}&limit=12`)
            .then(r => r.ok ? r.json() : Promise.reject(r.status))
            .then(d => { if (alive) setData(d) })
            .catch(() => { if (alive) setError(true) })
        return () => { alive = false }
    }, [day, country])

    const name = resolveCountryName(country, country)
    const dateLabel = new Date(day + 'T00:00:00Z')
        // timeZone UTC: `day` is a UTC archive day — local rendering shifted
        // it a day west of the scrubber label (caught 2026-07-15).
        .toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', timeZone: 'UTC' })

    return (
        <div className="day-evidence">
            <div className="day-evidence-head">
                <div>
                    <div className="day-evidence-kicker">DAY EVIDENCE · {dateLabel}</div>
                    <div className="day-evidence-title">{name}</div>
                </div>
                <button className="day-evidence-close" onClick={onClose} aria-label="Close">×</button>
            </div>

            {data?.tier === 'archive' && (
                <div className="day-evidence-tier" data-tip={data.note ?? undefined}>
                    FROM THE ARCHIVE — distinct-source sample, not exhaustive coverage
                </div>
            )}
            {data?.tier === 'hot' && (
                <div className="day-evidence-tier day-evidence-tier--hot">
                    LIVE WINDOW — direct signal sample for this day
                </div>
            )}

            {!data && !error && <div className="day-evidence-status">Loading that day's receipts…</div>}
            {error && <div className="day-evidence-status">Evidence service unavailable right now.</div>}

            {data && data.items.length === 0 && (
                <div className="day-evidence-status">
                    No {data.tier === 'archive' ? 'archived sample' : 'signals'} for {name} on this day — honest empty, not filler.
                </div>
            )}

            <ul className="day-evidence-list">
                {(data?.items ?? []).map((it, i) => (
                    <li key={i}>
                        {it.url
                            ? <a href={it.url} target="_blank" rel="noopener noreferrer">{it.headline}</a>
                            : <span>{it.headline}</span>}
                        {it.source && <span className="day-evidence-src"> — {it.source}</span>}
                    </li>
                ))}
            </ul>

            <button className="day-evidence-live" onClick={onOpenLive}>
                Open {name} live (today) →
            </button>
        </div>
    )
}
