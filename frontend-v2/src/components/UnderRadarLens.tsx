// L2 Console "Under the Radar" lens — categories getting real signal that
// NOTHING has verified yet. Unlike the L1 Brief's global gap box, this
// RE-SCOPES to the active focus (#234): a focused country scopes directly, a
// focused person/thread scopes to its dominant country via the shared
// focus-relation context. Honest: when no relation resolves, it stays global.
import { useEffect, useState } from 'react'
import { useFocus } from '../contexts/FocusContext'
import { useFocusRelation } from '../hooks/useFocusRelation'
import { resolveCountryName } from '../lib/countryNames'
import {
  type CoverageGapsData,
  coverageGapsUrl,
  maxGapRaw,
  parseCoverageGaps,
} from '../lib/coverageGaps'
import { CoverageGapCard } from './CoverageGapCard'
import './UnderRadarLens.css'

interface Props {
  onOpenTopic: (slug: string) => void
}

export function UnderRadarLens({ onOpenTopic }: Props) {
  const { filter } = useFocus()
  const relation = useFocusRelation()
  const activeCountry = filter.country
  const relationCountry = !activeCountry && relation.relationActive && relation.kind !== 'country'
    ? relation.dominantCountry : null
  const scopeCountry = activeCountry ?? relationCountry

  // Hold the whole parsed payload — `status` is the ONLY thing allowed to decide
  // between "nothing under the radar" and "we could not measure". Never infer
  // that from gaps.length, or a failed request renders a false honest-empty.
  const [data, setData] = useState<CoverageGapsData | null>(null)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    let ignore = false
    setLoaded(false)
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), 12000)
    fetch(coverageGapsUrl(scopeCountry, 24), { signal: ctrl.signal })
      .then(r => (r.ok ? r.json() : null))
      .then(payload => {
        if (!ignore) setData(parseCoverageGaps(payload))
      })
      .catch(() => { if (!ignore) setData(null) })
      .finally(() => { clearTimeout(timer); if (!ignore) setLoaded(true) })
    return () => { ignore = true; clearTimeout(timer); ctrl.abort() }
  }, [scopeCountry])

  const scopeName = scopeCountry ? resolveCountryName(scopeCountry) : null
  const gaps = data?.gaps ?? []
  // A null parse (network failure / foreign contract) is degraded, not empty.
  const status = data?.status ?? 'degraded'
  const denominator = maxGapRaw(gaps)

  return (
    <div className="under-radar-lens">
      <div className="url-scope-bar">
        <span className="url-scope-label">
          {scopeName ? `Gaps in ${scopeName}` : 'Gaps worldwide'}
        </span>
        {relationCountry && (
          <span className="url-scope-chip"
            data-tip={`Re-scoped to the focus's dominant country: ${resolveCountryName(relationCountry)}`}>
            {(relation.value || '').toUpperCase().slice(0, 14)} → {relationCountry}
          </span>
        )}
      </div>

      {gaps.length > 0 ? (
        <>
          <div className="url-gapgrid">
            {gaps.map(g => (
              <CoverageGapCard key={g.slug} gap={g} maxRaw={denominator} onOpen={onOpenTopic} />
            ))}
          </div>
          <p className="url-foot">
            Categories with real signal where nothing cleared the quality gate — attention
            without verified coverage. Leads, not certified evidence.
          </p>
        </>
      ) : (
        <div className="under-radar-empty">
          <p>
            {!loaded
              ? 'Checking what the pipeline sees but has not verified…'
              : status === 'degraded'
                // Say we could not measure. Do NOT claim the field is clear.
                ? 'Coverage gaps could not be measured right now — this is a gap in the reading, not a clear field.'
                : scopeName
                  ? `Nothing under the radar in ${scopeName}: no category reached the ${data?.floor ?? 8}-signal floor with zero verified coverage.`
                  : `Nothing under the radar: no category reached the ${data?.floor ?? 20}-signal floor with zero verified coverage this window.`}
          </p>
        </div>
      )}
    </div>
  )
}
