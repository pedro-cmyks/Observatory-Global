// #236 Task 9 — the mobile search sheet.
//
// THE PROBLEM THIS SOLVES (Task 7, measured): elementFromPoint over the
// desktop command-bar's search input, with a thread read open, returns
// ThemeDetail's overlay — `position: fixed; inset: 0; z-index: 9000` at
// <=768px covers the command bar entirely. Search is the single most useful
// thing to reach mid-read (you found something in the text, you want to look
// it up) and it was the one surface a read made unreachable. This component
// is reachable from anywhere: the trigger sits at a fixed viewport corner
// with a z-index above the read, and the sheet itself opens as a modal over
// whatever was on screen.
//
// THE SCOPE THAT WAS CUT (read before touching this file): the plan's first
// draft had each result carry its measured constellation neighbours. That is
// CANCELLED — Task 8 measured the same sibling lane this would have reused
// and found 30/50 top-5 rows an unrelated story presented as kin, on a field
// that is 61.25% blob, with no client-side way to tell a fused anchor from a
// clean one. This sheet renders search RESULTS. It does not call the
// siblings endpoint and it does not render neighbours — see lensSections.ts's
// `connected` for the one section that already carries this refusal, and
// leave it there.
//
// WHY TOP-LEFT, AND WHY IT IS TWO POSITIONS NOT ONE. ThemeDetail's own
// pin/share/export/close cluster occupies top-RIGHT on every mobile read
// (ThemeDetail.tsx:639, `top:16px; right:16px` inside its panel); EntityPanel
// and CountryBrief both right-align their close button in a
// `justify-content: space-between` header. Bottom of the screen was ruled out
// on its own evidence: the tab bar (z 9500), the floating focus chip (z 9550,
// centered, up to 86vw wide) and FrameSheet (z 9400, full-width) already
// contest that space among themselves.
//
// The first cut of this file asserted top-left was clear because a grep for
// ArrowLeft/ChevronLeft across components/*.tsx returned nothing. That is a
// lexical check and it proved only that no component uses those two
// identifiers — it never asked what is actually PAINTED there. Two things
// were, and a grep cannot see either: the brand wordmark ("Atlas", a real
// `navigate('/')` link, App.tsx:1685 — not an icon name, so no identifier
// grep finds it) at field/live scope, and the Lens's OWN breadcrumb, which
// renders the literal glyph `←` rather than an ArrowLeft/ChevronLeft import
// (LensPanel.tsx:293-298) at covering-read scope. A review caught this with
// `getBoundingClientRect` (brand {x:8,y:6,w:65,h:26} vs the FAB's original
// {x:10,y:10,w:40,h:40} — near-total overlap) and `elementFromPoint` (both
// the brand's centre and the FAB's own centre resolved to `.search-sheet-fab`
// before the fix). The lesson, applied here rather than just noted: an
// assertion that a screen region is empty is a GEOMETRIC claim, and only a
// geometric check — hide the element and look, or `elementFromPoint` — can
// settle it. A grep returning nothing is evidence about grep, not about the
// screen.
//
// Re-measured properly (SearchSheet.css carries the numbers): field and live
// scope share the plain command bar, which has a genuine gap — the
// clipboard/moon/more icon row is right-aligned starting at x:242, leaving
// x:0-242 empty at y:40-84 — below the brand, above the search input row.
// Covering-read scope replaces that entire area with the Lens's own chrome
// promoted to two FULL-WIDTH fixed rows (the breadcrumb back button is
// `flex:1 1 auto`, so it is not just the "←" glyph but the whole 375px-wide
// row; the sections toggle below it is `width:100%` too) — there is no
// horizontal gap to hide in there, so the covering-read position clears the
// full 88px band vertically instead. Both positions, and the exact geometry
// behind each, are documented at the CSS rules themselves
// (SearchSheet.css:6-20 and :42-60) rather than re-derived here.
//
// WHY THE SHEET IS A TRUE TOP LAYER (z 9700 — above the tab bar's 9500, the
// focus chip's 9550 and the Lens's own fixed chrome at 9600; see
// SearchSheet.css for the number). The first cut sat this UNDER the tab
// bar/FrameSheet/focus chip on purpose, reasoning that a reader should be
// able to jump to Live/Brief without closing search first — the same
// convention ThemeDetail, LensPanel's read pane and BriefNewspaper all
// follow. Opened in the browser at field scope, that reasoning did not
// survive contact: LensPanel.css's closed `where it lives / connected` bar
// carries `position: relative; z-index: 9460` UNCONDITIONALLY (only its
// FIXED variant is gated to a covering read), so at 9300 it painted straight
// through this sheet's own body — "WHERE IT LIVES  CONNECTED" sitting
// mid-screen over the honest-empty reason text. A search modal being
// selectively transparent to unrelated chrome is a worse trap than the one
// the lower z-index was trying to avoid; closing the sheet costs one tap on
// its own × either way. `--mobile-bottom-reserve` stays on the scroll body
// regardless (SearchSheet.css) — it also covers the bottom safe-area inset,
// which applies whether the tab bar is visible on top or not.
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { track } from '../lib/telemetry'
import { getThemeLabel } from '../lib/themeLabels'
import { Search } from '../lib/icons'
import {
  buildSearchSection, type SearchPhase, type SearchRow, type SearchRowKind,
} from '../lib/searchSheet'
import './SearchSheet.css'

export interface SearchSheetDoors {
  /** The console's own thread opener (App.tsx `handleThemeSelect`) — NOT a
   *  bespoke call, so a thread tapped here pivots the Lens exactly the way
   *  every other thread-opening door does (the effects at App.tsx:1245 and
   *  :1259 read the resulting focus state and push the Lens scope; nothing
   *  here calls focusLens or setConsoleTab directly — MobileNavContext's own
   *  doc comment is explicit that focusLens has ONE caller, the console's own
   *  derivation effect, and this sheet is not it). */
  onThemeSelect: (theme: string, countryCode?: string, countryName?: string) => void
  /** The console's own country opener (App.tsx `handleCountryClick`, wrapped
   *  the same way the desktop SearchBar's onCountrySelect prop is). */
  onCountrySelect: (code: string) => void
  /** FocusContext's person setter, inlined at every other person-opening door
   *  in App.tsx (there is no dedicated handlePersonClick to call instead —
   *  `setFocus('person', name, name)` recurs verbatim at ~4 call sites). */
  onPersonSelect: (name: string) => void
}

const KIND_LABEL: Record<SearchRowKind, string> = {
  thread: 'Stories', country: 'Countries', person: 'People', signal: 'Signals',
}

function groupByKind(rows: SearchRow[]): [SearchRowKind, SearchRow[]][] {
  const order: SearchRowKind[] = ['thread', 'country', 'person', 'signal']
  return order
    .map((k): [SearchRowKind, SearchRow[]] => [k, rows.filter((r) => r.kind === k)])
    .filter(([, group]) => group.length > 0)
}

function rowMeta(row: SearchRow): string | null {
  if (row.kind === 'thread') {
    const parts = [`${(row.totalSignals ?? 0).toLocaleString()} signals`]
    if (row.category) parts.push(row.category)
    return parts.join(' · ') + (row.match === 'partial' ? ' · partial match' : '')
  }
  if (row.kind === 'person') return `${(row.totalSignals ?? 0).toLocaleString()} signals`
  if (row.kind === 'signal') return row.source ?? null
  return null
}

function SearchSheetModal({ onClose, onThemeSelect, onCountrySelect, onPersonSelect }: SearchSheetDoors & { onClose: () => void }) {
  const [query, setQuery] = useState('')
  // What was actually searched — distinct from `query`, which keeps changing
  // as the reader types. "No results for …" must name the query that was
  // MEASURED, not whatever is sitting in the input a keystroke later.
  const [submittedQuery, setSubmittedQuery] = useState('')
  const [phase, setPhase] = useState<SearchPhase>({ kind: 'idle' })
  const inputRef = useRef<HTMLInputElement>(null)
  // Guards a mashed-submit race the same way SearchBar's searchSeqRef does:
  // only the most recent request may write its outcome.
  const reqIdRef = useRef(0)

  useEffect(() => { inputRef.current?.focus() }, [])

  // A full-screen sheet over content that itself scrolls (the read
  // underneath) — lock the body so a drag inside the sheet cannot bleed
  // through to the page behind it. Restored on close/unmount, never left on.
  useEffect(() => {
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [])

  const runSearch = async (raw: string) => {
    const trimmed = raw.trim()
    setSubmittedQuery(trimmed)
    if (trimmed.length < 2) { setPhase({ kind: 'too_short' }); return }
    const seq = ++reqIdRef.current
    setPhase({ kind: 'loading' })
    track('search_query', { q_len: trimmed.length, via: 'mobile_sheet' })
    try {
      const res = await fetch(`/api/v2/search/unified?q=${encodeURIComponent(trimmed)}&hours=168`)
      if (seq !== reqIdRef.current) return // superseded by a later submit
      if (!res.ok) { setPhase({ kind: 'http_error', status: res.status }); return }
      // A 200 with an unparseable body is reduced to `null` here rather than
      // thrown — buildSearchSection's own guard turns a non-object body into
      // the same honest "could not be read" degrade a malformed 200 gets.
      const json = await res.json().catch(() => null)
      if (seq !== reqIdRef.current) return
      setPhase({ kind: 'ok', json })
    } catch {
      if (seq !== reqIdRef.current) return
      setPhase({ kind: 'network_error' })
    }
  }

  const handleSubmit = (e: FormEvent) => { e.preventDefault(); runSearch(query) }

  // SEARCH ON SUBMIT, NOT AS-YOU-TYPE. `/api/v2/search/unified` is per-IP
  // rate-limited (the "paid" bucket: 20 requests / 300s — the desktop
  // SearchBar's own 300ms-debounced typeahead already burns this budget
  // alone; a second as-you-type consumer on the SAME budget would exhaust it
  // roughly twice as fast, and this was measured directly while building
  // this file — a handful of manual dev opens 429'd well inside the budget).
  // One deliberate action per query also matches how the sheet is entered: a
  // reader opened it to look ONE thing up, not to browse a live-filtering
  // list. The 429 case below is a first-class state, not an afterthought,
  // because it is the one this decision makes likely to be hit in dev.
  const section = buildSearchSection(submittedQuery, phase, { labelForTheme: getThemeLabel })

  const handleRowTap = (row: SearchRow) => {
    track('search_result_click', { segment: row.kind, via: 'mobile_sheet' })
    if (row.kind === 'thread') onThemeSelect(row.id)
    else if (row.kind === 'country') onCountrySelect(row.id)
    else if (row.kind === 'person') onPersonSelect(row.label)
    else if (row.kind === 'signal') {
      // Mirrors SearchBar's handleSignalMatchClick: a resolved thread wins
      // over a bare country. parseSearchRows already drops a signal with
      // neither, so this else-branch is reachable only via a country.
      if (row.themeId) onThemeSelect(row.themeId, row.countryCode ?? undefined)
      else if (row.countryCode) onCountrySelect(row.countryCode)
    }
    onClose()
  }

  const groups = groupByKind(section.rows)

  return (
    <div className="search-sheet" role="dialog" aria-modal="true" aria-label="Search Atlas">
      <div className="search-sheet-header">
        <form className="search-sheet-form" onSubmit={handleSubmit}>
          <span className="search-sheet-icon" aria-hidden="true"><Search size={15} /></span>
          <input
            ref={inputRef}
            type="text"
            inputMode="search"
            enterKeyHint="search"
            className="search-sheet-input"
            placeholder="Stories, countries, people…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" className="search-sheet-go" disabled={query.trim().length < 2}>
            Search
          </button>
        </form>
        <button type="button" className="search-sheet-close" onClick={onClose} aria-label="Close search">
          ✕
        </button>
      </div>

      <div className="search-sheet-body">
        {section.state === 'ok' ? (
          <>
            {section.partialFailure && (
              <p className="search-sheet-partial">⚠ {section.partialFailure}</p>
            )}
            {groups.map(([kind, rows]) => (
              <section key={kind} className="search-sheet-section">
                <h3 className="search-sheet-section-label">
                  {KIND_LABEL[kind]} <span className="search-sheet-section-count">{rows.length}</span>
                </h3>
                <ul className="search-sheet-rows">
                  {rows.map((row) => (
                    <li key={`${row.kind}-${row.id}`}>
                      <button type="button" className="search-sheet-row" onClick={() => handleRowTap(row)}>
                        <span className="search-sheet-row-label">{row.label}</span>
                        {rowMeta(row) && <span className="search-sheet-row-meta">{rowMeta(row)}</span>}
                      </button>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </>
        ) : (
          // Rule inherited from lensSections.ts: an empty/degraded/loading
          // result renders its REASON, never a blank sheet — and the reason
          // for "nothing matched" reads nothing like the reason for "the
          // search could not be reached" (see buildSearchSection's REASON
          // table: 'empty' vs 'degraded' are worded, not merely tagged,
          // differently).
          <p className={`search-sheet-reason${section.state === 'degraded' ? ' search-sheet-reason--degraded' : ''}`}>
            {section.reason}
          </p>
        )}
      </div>
    </div>
  )
}

/**
 * Self-contained, like FrameSheet: owns its own open/closed state so App.tsx
 * gains one mount point rather than another slice of local state. Closed =
 * the floating trigger; open = the modal. The modal is a SEPARATE component
 * (`SearchSheetModal`) rather than a branch inside this one specifically so
 * its hooks (the focus effect, the body-scroll lock, the query/phase state)
 * only exist while open — a conditional return before calling them would
 * violate the rules of hooks the moment `open` flips.
 */
export function SearchSheet(doors: SearchSheetDoors) {
  const [open, setOpen] = useState(false)

  if (!open) {
    return (
      <button
        type="button"
        className="search-sheet-fab"
        onClick={() => setOpen(true)}
        data-tip="Search Atlas"
        aria-label="Search"
      >
        <Search size={18} />
      </button>
    )
  }

  return <SearchSheetModal {...doors} onClose={() => setOpen(false)} />
}
