// L2 Console — the MARKETS dock tab. A different DATA TYPE (levels, movement of
// numbers, EOD series) quarantined in its own container so it never contaminates
// the narrative threads spine (design §7). Descriptive only: the world bellwether
// basket, plus a focused country's OWN instruments — NEVER a correlation, lead-lag,
// "news moved this", or a trade signal. The discovered-relation tier is a
// reserved-but-dark slot gated on #226.
//
// Self-subscribes to focus (like AnomalyPanel): direct country focus → that
// country's own instruments; no focus → the neutral world board (never blank);
// a person/thread focus → the discovered dominant country's own instruments under
// an explicitly reworded re-scope chip. Tiles are inert — NO click jumps to a
// narrative panel (that crossing is exactly what the container prevents).
import { useEffect, useState } from 'react'
import { useFocus } from '../contexts/FocusContext'
import { useFocusRelation } from '../hooks/useFocusRelation'
import { resolveCountryName } from '../lib/countryNames'
import { useMarkets, type MarketInstrument } from '../lib/markets'
import {
  InstrumentTile,
  InstrumentChart,
  InstrumentHonestyChip,
  RelationPendingSlot,
  NotAdviceLine,
} from './InstrumentTile'
import './MarketsPanel.css'

function AsOf({ iso }: { iso: string | null | undefined }) {
  if (!iso) return null
  const d = new Date(iso)
  const label = isNaN(d.getTime()) ? iso : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  return (
    <span className="markets-asof" data-tip="Last close ingested for this basket. Delayed / end-of-day, not intraday.">
      as of {label}
    </span>
  )
}

export function MarketsPanel() {
  const { filter, setCountry } = useFocus()
  const relation = useFocusRelation()
  const [selected, setSelected] = useState<MarketInstrument | null>(null)
  const activeCountry = filter.country
  // #234 idiom (mirrors AnomalyPanel): when a non-country entity is focused, the
  // panel may re-scope to the focus's discovered dominant country — but ONLY under
  // an explicit, reworded chip, and only when a relation actually exists.
  const relationCountry =
    !activeCountry && relation.relationActive && relation.kind !== 'country'
      ? relation.dominantCountry
      : null
  const scopeCountry = activeCountry ?? relationCountry

  // Drop any open drill-chart when the scope changes (the selected symbol may not
  // be in the new set).
  useEffect(() => { setSelected(null) }, [scopeCountry])

  const { data, loading, failed } = useMarkets(scopeCountry)

  // Honest error state — never an empty 0.00 board (design §7: error ≠ empty).
  const degraded = failed || (data?.degraded ?? false)

  if (loading && !data) {
    return (
      <div className="markets-panel">
        <div className="markets-head">
          <InstrumentHonestyChip state="descriptive" />
        </div>
        <p className="markets-note">Loading market levels…</p>
      </div>
    )
  }

  if (degraded) {
    return (
      <div className="markets-panel">
        <div className="markets-head">
          <InstrumentHonestyChip state="descriptive" />
        </div>
        <p className="markets-note markets-note--error">
          Markets unavailable — retrying.
        </p>
        <NotAdviceLine />
      </div>
    )
  }

  const world = data?.world ?? []
  const country = data?.country ?? null
  const showCountry = !!scopeCountry && !!country?.has_own_instruments

  return (
    <div className="markets-panel">
      <div className="markets-head">
        <InstrumentHonestyChip state="descriptive" />
        <AsOf iso={data?.as_of} />
      </div>

      {selected ? (
        /* Drill: a bigger IN-PANEL chart for one instrument — stays in markets. */
        <InstrumentChart inst={selected} onBack={() => setSelected(null)} />
      ) : (
        <>
          {/* World bellwether board — always present, never blank. */}
          <div className="markets-section">
            <h4 className="section-label markets-section-title">World basket</h4>
            {world.length > 0 ? (
              <div className="markets-grid">
                {world.map(inst => (
                  <InstrumentTile key={inst.symbol} inst={inst} onClick={() => setSelected(inst)} />
                ))}
              </div>
            ) : (
              <p className="markets-note">No world instruments available yet.</p>
            )}
          </div>

          {/* A focused country's OWN instruments (the dock may show all roles incl.
              export-commodity — it reads as a global instrument here, not a country
              claim; the Brief country card is the surface that drops it). */}
          {showCountry && country && (
            <div className="markets-section">
              <div className="markets-section-headrow">
                <h4 className="section-label markets-section-title">
                  {resolveCountryName(country.country_code, undefined)} · own instruments
                </h4>
                <button
                  className="markets-focus-link"
                  onClick={() => setCountry(country.country_code)}
                  data-tip="Re-scope the whole console to this country."
                >
                  focus {resolveCountryName(country.country_code, undefined)} →
                </button>
              </div>
              {relationCountry && (
                <p className="markets-rescope" data-tip="Re-scoped to the focus's dominant country by coverage — these are that country's OWN instruments, not a measured link to why it surfaced.">
                  this country's own instruments — not linked to why it surfaced
                </p>
              )}
              <div className="markets-grid">
                {country.instruments.map(inst => (
                  <InstrumentTile key={inst.symbol} inst={inst} onClick={() => setSelected(inst)} />
                ))}
              </div>
            </div>
          )}

          {/* The reserved-but-dark relation slot — the honest absence of the gated tier. */}
          <RelationPendingSlot />
        </>
      )}
      <NotAdviceLine />
    </div>
  )
}
