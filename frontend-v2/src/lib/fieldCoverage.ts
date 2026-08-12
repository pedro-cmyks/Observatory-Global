// What the field readout is allowed to claim.
//
// Cold-user probe 2026-08-12 §7: *"A product whose entire pitch is 'measured'
// cannot afford two answers to 'how many signals did Germany have.'"* The
// console header answered "175 countries · 100,587 signals" from the map
// payload while the dock and the Brief answered "218 · 109,632" from the same
// table. The header was not wrong about the map -- it was reporting the map's
// drawing ability as if it were the world.
//
// /api/v2/nodes now discloses both: what it COUNTED and what it could MAP.
// The header prints the counted base (agreeing with the dock and the Brief) and
// names the undrawn remainder instead of quietly absorbing it.

export interface FieldCoverage {
  basis?: string
  label?: string
  note?: string
  counted_countries?: number
  counted_signals?: number
  mapped_countries?: number
  mapped_signals?: number
  unmapped_countries?: number
  unmapped_signals?: number
}

export interface FieldCoverageReadout {
  countries: number
  signals: number
  /** "218 countries · 109,632 signals" */
  label: string
  tip: string
}

interface NodeLike {
  signalCount?: number | null
}

function sumNodes(nodes: readonly NodeLike[]): number {
  return nodes.reduce((sum, n) => sum + (n.signalCount || 0), 0)
}

export function fieldCoverageReadout(
  coverage: FieldCoverage | null | undefined,
  nodes: readonly NodeLike[],
): FieldCoverageReadout {
  const counted = coverage?.counted_countries
  const countedSignals = coverage?.counted_signals

  // A coverage object without counted totals tells us nothing we can print --
  // fall back to what is on screen and SAY that is what we are counting,
  // rather than dressing a rendered subset as a global total.
  if (typeof counted !== 'number' || typeof countedSignals !== 'number') {
    const signals = sumNodes(nodes)
    return {
      countries: nodes.length,
      signals,
      label: `${nodes.length} countries · ${signals.toLocaleString()} signals`,
      tip:
        'Counted over the countries currently drawn on the map. The field endpoint did not report its full base for this window.',
    }
  }

  const unmappedCountries = coverage?.unmapped_countries ?? 0
  const unmappedSignals = coverage?.unmapped_signals ?? 0
  const basisLabel = coverage?.label ?? 'measured field'

  let tip = `${countedSignals.toLocaleString()} signals across ${counted} countries in the last 24 hours, counted over the ${basisLabel}.`
  if (unmappedCountries > 0) {
    tip += ` ${unmappedCountries} of them (${unmappedSignals.toLocaleString()} signals) have no map coordinates and are not drawn — the total still includes them.`
  }

  return {
    countries: counted,
    signals: countedSignals,
    label: `${counted} countries · ${countedSignals.toLocaleString()} signals`,
    tip,
  }
}
