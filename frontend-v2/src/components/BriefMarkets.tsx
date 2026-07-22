// L1 Brief — the descriptive markets overlay. TWO distinct placements, because the
// data belongs to two different scopes (Pedro 2026-07-21):
//   • BriefWorldMarketsBand  — GLOBAL bellwethers (oil/gold/S&P/dollar/vol). A
//     full-width franja at the TOP of the edition. These are NOT the country's data,
//     so the band never swaps when a country is focused.
//   • BriefCountryMarketsCard — the FOCUSED country's OWN instruments (currency +
//     index + champions; export-commodity dropped — the causal trap, design §7).
//     Rendered DOWN in the country edition, with the rest of that country's data.
//     No world fallback: a country with no tracked instrument renders nothing.
//
// A DIFFERENT DATA TYPE from the sealed narrative edition: the sealed
// PublicationPackage has NO markets field by design (design §7). Markets ride the LIVE
// path only, with their OWN as-of stamp + a "LIVE OVERLAY — not part of the sealed
// edition" divider. Descriptive only — level + trend, NEVER a correlation, lead-lag,
// "news moved this", or a trade signal. Dead/undeployed endpoint → silent absence.
import { useMarkets } from '../lib/markets'
import { resolveCountryName } from '../lib/countryNames'
import { InstrumentTile, InstrumentHonestyChip, NotAdviceLine } from './InstrumentTile'
import type { MarketInstrument } from '../lib/markets'
import './BriefMarkets.css'

const SEAL_FOOTER = 'Markets update live; today’s stories are sealed as of 02:30.'

function LiveOverlayDivider({ asOf }: { asOf: string | null | undefined }) {
  let stamp: string | null = null
  if (asOf) {
    const d = new Date(asOf)
    stamp = isNaN(d.getTime()) ? asOf : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  }
  return (
    <div className="brief-markets-divider">
      <span className="brief-markets-live">Live overlay — not part of the sealed edition</span>
      {stamp && <span className="brief-markets-asof">last close {stamp}</span>}
    </div>
  )
}

// Shared inner layout (head + tiles + footer), used by both placements.
function MarketsInner({
  title, tip, instruments, asOf, degraded, notAdvice,
}: {
  title: string
  tip: string
  instruments: MarketInstrument[]
  asOf: string | null | undefined
  degraded: boolean
  notAdvice?: boolean
}) {
  return (
    <div className="brief-markets-band-inner">
      <div className="brief-markets-head">
        <h3 className="brief-markets-title" data-tip={tip}>{title}</h3>
        <InstrumentHonestyChip state="descriptive" />
        <LiveOverlayDivider asOf={asOf} />
      </div>
      {degraded ? (
        <p className="brief-markets-note brief-markets-note--error">Markets unavailable — retrying.</p>
      ) : (
        <div className="brief-markets-row">
          {instruments.map(inst => <InstrumentTile key={inst.symbol} inst={inst} />)}
        </div>
      )}
      <div className="brief-markets-footline">
        {notAdvice && <NotAdviceLine />}
        <p className="brief-markets-foot">{SEAL_FOOTER}</p>
      </div>
    </div>
  )
}

/** Full-width GLOBAL bellwether franja at the top of the edition. Never country-scoped. */
export function BriefWorldMarketsBand() {
  const { data, loading, failed } = useMarkets(null)
  if (loading && !data) return null
  // A hard fetch failure (undeployed backend / network / timeout) must NOT vanish
  // the band silently — that silent-absence hid the "markets disappeared" symptom.
  // Mirror MarketsPanel: treat `failed` as degraded and render the honest note.
  const degraded = failed || (data?.degraded ?? false)
  const world = data?.world ?? []
  if (!degraded && world.length === 0) return null
  return (
    <section className="brief-markets-band" aria-label="World markets — descriptive overlay">
      <MarketsInner
        title="World markets"
        tip="World bellwether instruments — descriptive levels and 30-day trend at the last close. NOT a claim that today's news moved them."
        instruments={world}
        asOf={data?.as_of}
        degraded={degraded}
      />
    </section>
  )
}

/** The focused country's OWN instruments, in the country edition body. Renders nothing
 *  when the country has no tracked instrument (honest absence — never world fallback,
 *  never a fabricated tick). */
export function BriefCountryMarketsCard({ countryCode }: { countryCode: string }) {
  const { data, loading, failed } = useMarkets(countryCode)
  if (loading && !data) return null
  // failed → honest degraded note, not a silent vanish (wedge; see world band above).
  const degraded = failed || (data?.degraded ?? false)
  const instruments = (data?.country?.instruments ?? []).filter(i => i.role !== 'export-commodity')
  if (!degraded && instruments.length === 0) return null
  return (
    <section className="brief-markets-card" aria-label="Country markets — descriptive overlay">
      <MarketsInner
        title={`${resolveCountryName(countryCode, undefined)} markets`}
        tip="This country's own instruments by definition — its currency and main index. Descriptive; NOT a claim that its news moved these."
        instruments={instruments}
        asOf={data?.as_of}
        degraded={degraded}
        notAdvice
      />
    </section>
  )
}
