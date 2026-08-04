import React from 'react'
import type { EvidenceRouteStep } from '../lib/evidenceRoute'
import './EvidenceRoute.css'

// #173 — Evidence Route breadcrumb. Pure presentational component: it receives the
// pre-built steps (see lib/evidenceRoute.ts) and renders a compact chip trail in the
// CountryBrief header. Each chip is clickable to scroll to the panel it names.
// Honesty: an absent count shows "—", never a fabricated number.

interface EvidenceRouteProps {
  steps: EvidenceRouteStep[]
  /** Scroll/expand the panel a chip names. Given the step's targetId. */
  onStepClick?: (targetId: string) => void
}

// Context-head steps (the entity the route starts from) carry no count by
// design — they must not render the honest-absence "—" that a MISSING count
// gets on the funnel steps.
const HEAD_KEYS = new Set(['country', 'topic', 'person', 'signal'])

export const EvidenceRoute: React.FC<EvidenceRouteProps> = ({ steps, onStepClick }) => {
  if (steps.length === 0) return null
  return (
    <nav className="evidence-route" aria-label="Evidence route">
      {steps.map((step, i) => (
        <React.Fragment key={step.key}>
          {i > 0 && <span className="evidence-route-arrow" aria-hidden="true">→</span>}
          <button
            type="button"
            className="evidence-route-chip"
            onClick={onStepClick ? () => onStepClick(step.targetId) : undefined}
            data-tip={`Jump to ${step.label}`}
          >
            <span className="evidence-route-label">{step.label}</span>
            {step.count !== null && (
              <span className="evidence-route-count">{step.count.toLocaleString()}</span>
            )}
            {step.count === null && !HEAD_KEYS.has(step.key) && (
              <span className="evidence-route-count evidence-route-count--absent">—</span>
            )}
            {step.detail && (
              <span className="evidence-route-detail">{step.detail}</span>
            )}
          </button>
        </React.Fragment>
      ))}
    </nav>
  )
}

export default EvidenceRoute
