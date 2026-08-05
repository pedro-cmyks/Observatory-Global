import type { ReactNode } from 'react'
import type { MobileSurface } from '../lib/mobileNav'
import { scopeTitle, type LensScope } from '../lib/lensScope'
import './LensPanel.css'

export interface LensPanelProps {
  /** Which of the console's three phone surfaces is showing. */
  surface: MobileSurface
  /** Where the Lens has been; the last entry is what it shows now. */
  trail: LensScope[]
  /** Walk back one scope. Wired to the console's own back, not a private one. */
  onBack: () => void
  /** The ranked field — what the Lens shows when nothing is focused. */
  field: ReactNode
  /**
   * The read: the console's focus machine. It renders the opened thread,
   * country, person, attention item or chokepoint — and, when nothing is
   * open, the Live firehose. One node, because it is ONE mounted panel that
   * both the Lens and Live surfaces show; see the note on `slots` below.
   */
  read: ReactNode
}

/**
 * The Lens: one surface that re-scopes to whatever you are looking at.
 *
 * WHY TWO SLOTS AND NOT A RENDERER PER SCOPE KIND. The Lens design names five
 * scopes, and the natural API is `Record<LensScopeKind, ReactNode>` — one
 * rendered element per kind. It cannot be that here, for a reason that is
 * structural rather than stylistic: four of those kinds (thread, country,
 * person, and the two extra console scopes) are served by a SINGLE mounted
 * panel — the console's focus machine — and that same panel is also the Live
 * surface. A Record keyed by kind would either mount that panel once per key
 * (four SignalStreams polling) or quietly designate one key as the real one.
 * So the slots are the two things that are actually mounted, and the scope
 * KIND drives naming (breadcrumb, heading, announcement) rather than
 * selection. When Task 8 gives a scope its own sections, they hang off the
 * kind at that point.
 *
 * KEEP-ALIVE. Both slots stay mounted and toggle visibility, exactly as the
 * shell did before the Lens existed (#236 Task 6): remounting measured worse
 * — 0.7-1.5s of blank panel and re-fired requests on every tap. `display:
 * contents` means the wrapper generates no box, so each panel lays out as if
 * it were still a direct child of the shell.
 */
export function LensPanel({ surface, trail, onBack, field, read }: LensPanelProps) {
  const showsField = surface === 'lens-field'
  // Live is not a Lens surface: it is the unfocused firehose, and it wears no
  // scope chrome. The read slot is visible under both, which is exactly why
  // the chrome is a sibling of the slots and not a wrapper around them.
  const showsChrome = surface !== 'live'
  const scope = trail[trail.length - 1]
  const previous = trail.length > 1 ? trail[trail.length - 2] : null

  return (
    <>
      {showsChrome && scope && (
        <div className="lens-chrome">
          {previous && (
            <button
              type="button"
              className="lens-breadcrumb"
              onClick={onBack}
              data-tip="Back to the scope you came from"
            >
              <span aria-hidden="true">←</span> {scopeTitle(previous)}
            </button>
          )}
          {/* A real heading for the surface, carrying the FULL scope title —
              the panel header below it truncates to fit the phone, this does
              not. Visually hidden because the panel already shows the name;
              duplicating it on screen would cost a line of a small screen for
              nothing. */}
          <h2 className="lens-scope-heading">{scopeTitle(scope)}</h2>
        </div>
      )}
      <div key="lens-field" style={{ display: showsField ? 'contents' : 'none' }}>{field}</div>
      <div key="lens-read" style={{ display: showsField ? 'none' : 'contents' }}>{read}</div>
    </>
  )
}
