import { useEffect, useRef, useState, type ReactNode } from 'react'
import { fieldVisible, type MobileSurface } from '../lib/mobileNav'
import { scopeTitle, type LensScope, type LensScopeKind } from '../lib/lensScope'
import {
  buildSections, nodesQueryFor, readNodesResponse, SECTION_LABELS,
  type CountryRow, type LaneStatus,
} from '../lib/lensSections'
import { resolveCountryName } from '../lib/countryNames'
import './LensPanel.css'

/** How many country rows the sheet shows before it stops. */
const WHERE_IT_LIVES_CAP = 12

/**
 * What `connected` can honestly report, per scope.
 *
 * EVERY scope returns a NON-`ok` status today, which is the finding rather than
 * a placeholder — see the section comment on <LensSectionSheet/>. `field` is
 * `no_anchor` because nothing is focused, so there is no subject to measure
 * neighbours against; every other scope is `unavailable` because the neighbour
 * lane this section would draw from has not cleared its own gate.
 */
function connectedLane(kind: LensScopeKind): LaneStatus {
  return kind === 'field' ? 'no_anchor' : 'unavailable'
}

export interface LensPanelProps {
  /** Which of the console's three phone surfaces is showing. */
  surface: MobileSurface
  /** Where the Lens has been; the last entry is what it shows now. */
  trail: LensScope[]
  /** Walk back one scope. Wired to the console's own back, not a private one. */
  onBack: () => void
  /**
   * Re-scope the Lens to a country. Must be the console's OWN country opener:
   * the Lens scope is derived from App's focus state, not from the shared
   * filter, so calling `setCountry` from FocusContext here would re-scope the
   * map while the breadcrumb and the read went on naming the old scope.
   *
   * Code only — the opener resolves the display name itself, so passing the
   * one the section happens to be showing would introduce a second source for
   * a name the console already owns.
   */
  onOpenCountry: (code: string) => void
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
 * Sections 3 and 4 of the Lens — `where it lives` and `connected` — as a bar
 * that opens into a sheet.
 *
 * WHY A BAR AND NOT A THIRD BLOCK IN THE SCROLL. The design puts these sections
 * below the scope's read, and on the phone that position does not exist: the
 * thread read (ThemeDetail) is `position: fixed; inset: 0` at <=768px
 * (ThemeDetail.css:1277), and the country and person reads render their
 * `--inline` variants, `position: absolute; inset: 0` filling their panel
 * (CountryBrief.css:13, EntityPanel.css:21). A sibling rendered "below" any of
 * them is behind it, or below the fold of a panel it does not scroll with. So
 * the sections take the one strip that is theirs — directly under the scope
 * chrome, composed into the same `--lens-*` variables the read's inset is
 * already built from — and open
 * over the read when tapped. It is the top rather than the bottom because both
 * bottom-anchored slots are occupied: the tab bar (z 9500) and FrameSheet
 * (fixed, `bottom: 56px + safe-area`, z 9400).
 *
 * WHY `connected` IS EMPTY AT EVERY SCOPE. Not an unfinished wire — a refusal
 * with a measurement behind it. The one live neighbour ranker,
 * `GET /api/v2/story/{id}/siblings`, was hand-judged at 30 of 50 top-5 rows
 * being an unrelated story presented as kin on random active anchors, a rate
 * inherited from the cosine walk over a field that is 61.25% blob; its own
 * pre-registered gate held NAV-LOSS 6/6 and the story lens ships dark
 * (STORY_LENS_AUTO = false) because of it. The client also cannot tell a fused
 * anchor from a clean one: `anchor.is_blob` is only populated on the umbrella
 * path and is `false` meaning "not evaluated" everywhere else. A phone row has
 * no room for that caveat, so the section states its absence instead of
 * ranking. The honest neighbour relation that DOES exist — the rarity-weighted
 * distinctive-entity + shared-primary-country siblings — lives inside
 * NarrativeThreads over its own fetched pool; surfacing it here means lifting
 * that rule into a shared module rather than copying it, which is its own task.
 */
function LensSectionSheet({ scope, onOpenCountry }: {
  scope: LensScope
  onOpenCountry: (code: string) => void
}) {
  const [open, setOpen] = useState(false)
  // The sheet is fixed, so it needs an absolute `top` — and the bar it hangs
  // off is fixed only when a covering read is up (see LensPanel.css). In flow
  // it sits wherever the chrome above it ends, which the stylesheet cannot
  // know: composing the top from --lens-* put the sheet at 88px while the bar
  // was at 191px, and the sheet then covered its own toggle with no way back.
  // Measured at open time, when the bar is at its resting position and the
  // sheet has not yet displaced anything.
  const barRef = useRef<HTMLDivElement>(null)
  const [sheetTop, setSheetTop] = useState<number | null>(null)

  const toggle = () => {
    if (!open && barRef.current) setSheetTop(barRef.current.getBoundingClientRect().bottom)
    setOpen((v) => !v)
  }

  // `null` until this scope has been measured — distinct from `[]`, which is a
  // measured zero. Only the second may say "no country resolved".
  const [rows, setRows] = useState<CountryRow[] | null>(null)
  const [lane, setLane] = useState<LaneStatus>('loading')
  const query = nodesQueryFor(scope)

  // WHY THIS FETCHES INSTEAD OF READING useFocusData(). The shared context is
  // the obvious source and it is the wrong one: it PRESERVES the previous
  // scope's nodes when a scoped fetch returns empty (stale-while-revalidate,
  // so the command bar never flashes 0 — FocusDataContext.tsx:194), and it
  // preserves `meta` alongside them on the same branch (:201), so no value it
  // exposes distinguishes "measured for this scope" from "left over from the
  // last one". Measured, not reasoned: with a thread open, the section listed
  // `United States 21,149` — the global field — under that thread's name.
  // Fetching against this scope's own key is what makes the answer this
  // scope's. Lazy, so a section nobody opens costs a phone nothing.
  useEffect(() => {
    if (!open) return
    if (query === null) { setRows([]); setLane('unavailable'); return }
    const ac = new AbortController()
    setRows(null)
    setLane('loading')
    fetch(query, { signal: ac.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((j) => {
        // readNodesResponse, not an inline `.map`, because this endpoint
        // signals failure INSIDE a 200 body and the discriminator is subtle
        // enough to deserve tests: see its doc comment. The name resolver goes
        // in because the endpoint does not name every code it returns
        // (measured: a thread's footprint came back with a bare `YE`), and it
        // prefers the API's own name wherever there is one.
        const { rows: next, lane: nextLane } = readNodesResponse(j, {
          resolveName: resolveCountryName,
          cap: WHERE_IT_LIVES_CAP,
        })
        setRows(next)
        setLane(nextLane)
      })
      .catch((e) => {
        if ((e as Error)?.name === 'AbortError') return
        // A lane that failed is degraded, never an empty one. The alternative
        // renders a broken query as "no country resolved" — the same
        // timeout-as-absence defect this codebase already shipped once.
        setRows([])
        setLane('db_error')
      })
    return () => ac.abort()
  }, [open, query])

  const sections = buildSections(
    { countries: rows ?? [], connected: [], attention: [] },
    { whereItLives: lane, connected: connectedLane(scope.kind) },
  )
  const { whereItLives, connected } = sections

  return (
    <>
      <div className="lens-sections-bar" ref={barRef}>
        <button
          type="button"
          className="lens-sections-toggle"
          onClick={toggle}
          aria-expanded={open}
        >
          {/* Names only, no counts. The sections are measured when opened, so
              a tally on the closed bar would have to invent one — and "0" or
              "—" before asking is exactly the absence-claim this whole surface
              exists to avoid. */}
          <span className="lens-sections-tally">{SECTION_LABELS.whereItLives}</span>
          <span className="lens-sections-tally">{SECTION_LABELS.connected}</span>
          <span className="lens-sections-caret" aria-hidden="true">{open ? '▾' : '▸'}</span>
        </button>
      </div>

      {open && (
        <div
          className="lens-sections-sheet"
          role="group"
          aria-label="Lens sections"
          style={sheetTop != null ? { top: sheetTop } : undefined}
        >
          <section className="lens-section">
            <h3 className="lens-section-label">{SECTION_LABELS.whereItLives}</h3>
            {whereItLives.state === 'ok' ? (
              <ul className="lens-section-rows">
                {whereItLives.rows.map((c) => (
                  <li key={c.code}>
                    <button
                      type="button"
                      className="lens-section-row"
                      onClick={() => { setOpen(false); onOpenCountry(c.code) }}
                    >
                      <span className="lens-row-name">{c.name}</span>
                      <span className="lens-row-count">{c.count.toLocaleString()}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              // Rule 1: an empty section renders its reason. A section that
              // shows nothing and says nothing reads the same as a broken one.
              <p className="lens-section-reason">{whereItLives.reason}</p>
            )}
          </section>

          <section className="lens-section">
            <h3 className="lens-section-label">{SECTION_LABELS.connected}</h3>
            {connected.state === 'ok' ? (
              <ul className="lens-section-rows">
                {connected.rows.map((r) => (
                  <li key={r.id}>
                    <div className="lens-section-row lens-section-row--static">
                      <span className="lens-row-name">{r.label}</span>
                      {/* Rule 2: the basis rides with the row, always. It wraps
                          rather than truncating — a receipt you cannot read is
                          not a receipt. */}
                      <span className="lens-row-receipt">↔ {r.receipt}</span>
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="lens-section-reason">{connected.reason}</p>
            )}
            {connected.withheld ? (
              <p className="lens-section-reason">
                {connected.withheld} neighbour{connected.withheld === 1 ? '' : 's'} withheld for carrying no receipt.
              </p>
            ) : null}
          </section>
        </div>
      )}
    </>
  )
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
 * selection. Task 8's sections do hang off the kind, but as DATA rather than
 * as a slot: <LensSectionSheet/> reads `scope.kind` to decide what each
 * section can honestly report, and renders itself.
 *
 * KEEP-ALIVE. Both slots stay mounted and toggle visibility, exactly as the
 * shell did before the Lens existed (#236 Task 6): remounting measured worse
 * — 0.7-1.5s of blank panel and re-fired requests on every tap. `display:
 * contents` means the wrapper generates no box, so each panel lays out as if
 * it were still a direct child of the shell.
 */
export function LensPanel({ surface, trail, onBack, onOpenCountry, field, read }: LensPanelProps) {
  const showsField = fieldVisible(surface)
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
              <span aria-hidden="true">←</span>
              <span className="lens-breadcrumb-label">{scopeTitle(previous)}</span>
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
      {/* Same condition as the chrome: Live is the unfocused firehose and wears
          no scope furniture, so it gets no sections either. */}
      {showsChrome && scope && (
        <LensSectionSheet scope={scope} onOpenCountry={onOpenCountry} />
      )}
      <div key="lens-field" style={{ display: showsField ? 'contents' : 'none' }}>{field}</div>
      <div key="lens-read" style={{ display: showsField ? 'none' : 'contents' }}>{read}</div>
    </>
  )
}
