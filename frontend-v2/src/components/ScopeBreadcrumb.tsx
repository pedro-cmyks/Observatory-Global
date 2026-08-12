import type { ScopeCrumb } from '../lib/scopePath'
import { isCurrentScope } from '../lib/scopePath'
import './ScopeBreadcrumb.css'

/**
 * The scope path, rendered.
 *
 * Replaces FocusIndicator. That component printed the same dimensions as a set
 * of chips, each with a 14px ✕, plus an 18px ✕ for "clear all" at the far right
 * of the band — and R4's cold reader never found either. The exit is now the
 * first crumb: a word, always present, always in the same place, that says what
 * it does. (The `data-tour="focus-clear"` hook moves onto it so the country
 * walkthrough still has something true to point at.)
 *
 * TWO VARIANTS, ONE COMPONENT. `band` is the desktop in-flow strip under the
 * command bar; `lens` is the phone's, inside the Lens chrome. They differ only
 * in CSS: the same crumbs, the same handler, the same order — because the whole
 * point of the folder model is that the reader learns ONE grammar.
 */
export interface ScopeBreadcrumbProps {
  path: ScopeCrumb[]
  /** Navigate to that level. Never called for the crumb the reader is standing in. */
  onNavigate: (crumb: ScopeCrumb, index: number) => void
  variant?: 'band' | 'lens'
}

export function ScopeBreadcrumb({ path, onNavigate, variant = 'band' }: ScopeBreadcrumbProps) {
  if (path.length === 0) return null

  return (
    <nav
      className={`scope-breadcrumb scope-breadcrumb--${variant}`}
      aria-label="Scope path"
    >
      <span className="scope-dot" aria-hidden="true" />
      <ol className="scope-crumbs">
        {path.map((crumb, i) => {
          const current = isCurrentScope(path, i)
          const label = (
            <>
              {crumb.typeLabel && <span className="scope-meta">{crumb.typeLabel}</span>}
              <span className={`scope-value${crumb.pending ? ' scope-value--pending' : ''}`}>
                {crumb.label}
              </span>
            </>
          )
          return (
            <li className="scope-crumb" key={`${crumb.level}:${crumb.id}`}>
              {i > 0 && <span className="scope-sep" aria-hidden="true">▸</span>}
              {current ? (
                // The scope you are in is a statement, not a door. Rendering it
                // as a button would offer a click that does nothing.
                <span className="scope-crumb-current" aria-current="page">{label}</span>
              ) : (
                <button
                  type="button"
                  className="scope-crumb-link"
                  onClick={() => onNavigate(crumb, i)}
                  data-tour={crumb.level === 'world' ? 'focus-clear' : undefined}
                  data-tip={
                    crumb.level === 'world'
                      ? 'Back to the whole world — clears every scope'
                      : `Back up to ${crumb.pending ? 'this ' + (crumb.typeLabel ?? 'scope').toLowerCase() : crumb.label}`
                  }
                  aria-label={
                    crumb.level === 'world'
                      ? 'Back to the whole world'
                      : `Back up to ${crumb.typeLabel ?? ''} ${crumb.pending ? '' : crumb.label}`.trim()
                  }
                >
                  {label}
                </button>
              )}
            </li>
          )
        })}
      </ol>
      {/* Only the band has room, and only a narrowed scope has anything to say:
          at world scope nothing has been re-scoped, so claiming it would be
          noise. Same sentence the focus band carried — every surface really
          does follow the scope (#234), and the reader should be told once. */}
      {variant === 'band' && path.length > 1 && (
        <span className="scope-note">map · stories · stream · universe re-scoped</span>
      )}
    </nav>
  )
}
