import { useEffect, useRef, useState, type ReactNode } from 'react'
import { fieldVisible, type MobileSurface } from '../lib/mobileNav'
import { scopeKey, scopeTitle, type LensScope } from '../lib/lensScope'
import {
  buildSections, connectedLane, nodesQueryFor, readNodesResponse,
  SECTION_LABELS, SHEET_SECTION_NAMES, SOURCES_SECTION_LABEL, whereItLivesLane,
  type ConnectedRow, type CountryRow, type LaneStatus,
} from '../lib/lensSections'
import { readThreadPool, threadPoolQuery, type PoolThread } from '../lib/narrativeThreadLimits'
import { buildThreadRelation } from '../lib/threadRelation'
import { resolveCountryName } from '../lib/countryNames'
import './LensPanel.css'

/** How many country rows the sheet shows before it stops. */
const WHERE_IT_LIVES_CAP = 12

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
  /**
   * Re-scope the Lens to another thread — a `connected` row. The console's own
   * thread opener, for the same reason as `onOpenCountry`. The label travels so
   * the breadcrumb names the story immediately instead of showing a raw
   * `dynamic-topic-N` until the read resolves it.
   */
  onOpenThread: (id: string, label?: string) => void
  /**
   * The console's country filter, if any. Passed rather than read from
   * FocusContext so the Lens keeps deriving everything it shows from props —
   * and because the sections need the same pool the thread list fetched, which
   * is scoped by this.
   */
  countryScope?: string | null
  /** The ranked field — what the Lens shows when nothing is focused. */
  field: ReactNode
  /**
   * The read: the console's focus machine. It renders the opened thread,
   * country, person, attention item or chokepoint — and, when nothing is
   * open, the Live firehose. One node, because it is ONE mounted panel that
   * both the Lens and Live surfaces show; see the note on `slots` below.
   */
  read: ReactNode
  /**
   * Section 5 of the Lens — the intel organ: geo alerts, conflict events,
   * theme spikes, the ATTENTION ECLIPSE row, and public attention (wiki /
   * trends / forum). `<AnomalyPanel/>`, which re-scopes ITSELF off the shared
   * focus relation, so it needs no scope prop from here.
   *
   * A node rather than a component, for the same reason `read` is one: its
   * doors (open a country, open an attention item, search) all live in App,
   * and threading five callbacks through the Lens to reach them would put a
   * second copy of App's navigation contract in a component whose whole job
   * is naming what is on screen. It is only ever CREATED here — React does
   * not mount an element until it is rendered, and this one renders only
   * inside the opened sheet.
   */
  attention: ReactNode
  /**
   * The sheet's sixth section — `<SourceIntegrityPanel/>`, which likewise
   * scopes itself off the shared filter. See SOURCES_SECTION_LABEL for why it
   * is named separately rather than folded into `attention`.
   */
  sources: ReactNode
}

/**
 * The Lens's lower sections — `where it lives`, `connected`, `attention` and
 * `sources` — as a bar that opens into a sheet.
 *
 * WHERE THE INTEL ORGAN LIVES, AND WHY HERE. Council R4 N29: the Brief|Lens|
 * Live shell retired the Pulse tab and nothing took its place, so Public
 * Attention, the AnomalyPanel (including the ATTENTION ECLIPSE row) and Source
 * Integrity had ZERO mobile surface — a DOM scan across all three tabs
 * returned 0 for `.anomaly-panel-container` and `.source-panel-container`.
 * They come back HERE, as sections of this sheet, rather than as a fourth tab,
 * because that is what the arc's own design says they are: the mobile IA spec
 * (docs/superpowers/specs/2026-08-04-mobile-native-ia-design.md §3) lists the
 * absorption "Pulse tab → §5 `attention`, always scoped" in the same table
 * that sends the Map tab to §3 and the Universe to §4 — the two sections
 * already in this sheet. Two more pieces of evidence that this was the
 * intended home and only the last wire was missing: `lensSections.ts` already
 * defines the `attention` section with a full set of states and copy, and
 * BOTH panels already carry a `#236` phone stylesheet (AnomalyPanel.css:345,
 * SourceIntegrityPanel.css:202) written for a surface that then stopped
 * existing. A fourth tab would also have to be paid for structurally: the
 * shell keeps exactly TWO mounted console panes and `MobileSurface` has three
 * values covering them, and the arc deliberately spent a commit teaching the
 * tour to stop saying four tabs.
 *
 * WHY THE REAL PANELS AND NOT ROWS BUILT FROM `buildSections`. Same reason the
 * Lens mounts ThemeDetail and CountryBrief for the read instead of
 * re-rendering their receipts: those panels already own the honest empty and
 * degraded states for their own lanes ("No anomalies", "Wikipedia data
 * unavailable", "No source data available"), and they already re-scope
 * themselves — AnomalyPanel off `useFocusRelation`, SourceIntegrityPanel off
 * the shared filter — so the organ follows the Lens's scope with no scope
 * prop. A hand-built copy would be a second transcription of both, free to
 * drift, and it is the drift between two copies of a lane's copy and its
 * behaviour that `lensSections.ts` exists to prevent. The pure `attention`
 * model stays in that module for a caller that renders ROWS; this one renders
 * the panel.
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
 * already built from — and open over the read when tapped. It is the top
 * rather than the bottom because both bottom-anchored slots are occupied: the
 * tab bar (z 9500) and FrameSheet (fixed, `bottom: 56px + safe-area`, z 9400).
 *
 * WHICH NEIGHBOUR RELATION `connected` SHOWS, AND WHICH IT REFUSES TO. It shows
 * the #234 sibling relation (lib/threadRelation) — a shared country in the open
 * thread's PRIMARY geography, or a shared actor that few threads in the pool
 * carry — because every one of its receipts is checkable: the basis is a
 * country or a name the reader can see on both rows. It does NOT show the
 * ranked walk behind `GET /api/v2/story/{thread_id}/siblings`, which was
 * hand-judged at 30 of 50 top-5 rows being an unrelated story presented as kin
 * on random active anchors, over a field that is 61.25% blob; that lens ships
 * dark (STORY_LENS_AUTO = false) on its own pre-registered gate, and the client
 * cannot even tell a fused anchor from a clean one (the handler leaves
 * `anchor_is_blob` at `False` off the umbrella path, story.py:475-477, where
 * `False` means "not evaluated"). A phone row has no room for that caveat.
 * Weaker and checkable beats stronger and unfalsifiable.
 *
 * That refusal is a choice about which lane to CALL, so it is not a state the
 * reader is ever shown. `connected` never says "neighbours were withheld": at a
 * thread it renders what the relation measured, and at every other scope it
 * says nothing was attempted — see `connectedLane`, which is also the single
 * place that decides which scope measures.
 *
 * THREAD SCOPE ONLY. #234 relates a thread to other THREADS, so that is the one
 * scope where it can answer; the rest say so rather than borrowing the shape.
 */
function LensSectionSheet({ scope, countryScope, onOpenCountry, onOpenThread, attention, sources }: {
  scope: LensScope
  /** The console's country filter — see `poolQuery` below for why it matters. */
  countryScope?: string | null
  onOpenCountry: (code: string) => void
  onOpenThread: (id: string, label?: string) => void
  attention: ReactNode
  sources: ReactNode
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
  // A scope that answers WITHOUT the endpoint settles here: `country`, whose
  // footprint is itself, and the kinds the endpoint has no key for. Null means
  // "go and measure it".
  const preset = whereItLivesLane(scope)
  const query = preset === null ? nodesQueryFor(scope) : null

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
    if (query === null) { setRows([]); setLane(preset ?? 'unavailable'); return }
    // Do not re-ask a question already answered WELL for this scope. The
    // endpoint is measurably flaky (five identical calls: four failures, one
    // success), so re-opening the sheet used to be a fresh chance to fail and
    // replace good rows with an error. A failed or empty lane is NOT cached —
    // re-opening is how the reader retries. Scope changes reset this by
    // remounting; see the `key` where this is rendered.
    if (lane === 'ok' && rows && rows.length > 0) return
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
  // eslint-disable-next-line react-hooks/exhaustive-deps -- `lane`/`rows` are
  // READ by the already-answered guard above, not inputs to it: listing them
  // would re-run this effect on the very writes it makes.
  }, [open, query, preset])

  // --- the neighbourhood lane ------------------------------------------------

  // The scope `connectedLane` declines to settle is the one with a relation to
  // measure. Derived from that answer rather than re-testing `scope.kind` here,
  // so "which scope measures" has exactly one definition.
  const settledConnected = connectedLane(scope.kind)
  const measuresConnected = settledConnected === null

  // `null` until measured, exactly as `rows` above.
  const [pool, setPool] = useState<PoolThread[] | null>(null)
  const [poolLane, setPoolLane] = useState<LaneStatus>('loading')
  // The SAME pool the console's thread list ranks over — same hours, same
  // limit, same country scoping. Not a detail: the relation weights an actor by
  // how many threads in the pool carry it, so a differently-scoped pool would
  // honestly produce a different receipt for the same pair, and the phone's two
  // surfaces would then disagree about why two stories are neighbours.
  const poolQuery = threadPoolQuery(countryScope)

  useEffect(() => {
    if (!open || !measuresConnected) return
    const ac = new AbortController()
    setPool(null)
    setPoolLane('loading')
    fetch(poolQuery, { signal: ac.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((j) => {
        const next = readThreadPool(j)
        // `null` is an unreadable body, which is a failure — never an empty
        // pool. The section says degraded, not "no neighbour cleared the bar".
        if (next === null) { setPool([]); setPoolLane('db_error'); return }
        setPool(next)
        setPoolLane('ok')
      })
      .catch((e) => {
        if ((e as Error)?.name === 'AbortError') return
        // No retry, unlike the thread list's. That one retries because its
        // failure mode is SILENT — a stale global list left standing under a
        // "Scoped to X" strip, with nothing on screen saying so. This lane has
        // no stale rows to leave standing and it states the failure out loud,
        // so a second immediate request would buy a reader who can already see
        // what happened nothing, and closing and reopening the sheet asks again.
        setPool([])
        setPoolLane('db_error')
      })
    return () => ac.abort()
  }, [open, measuresConnected, poolQuery])

  // The rule itself is lib/threadRelation's, shared with NarrativeThreads —
  // one function, not a second transcription of the cap and the top-2.
  //
  // UNCAPPED, unlike `where it lives` above. That list is a long tail this
  // scope merely touches, so a cap trims noise; this one is bounded by the
  // pool already (at most pool size − 1, and measured at 2-7 in practice), and
  // every row in it cleared a stated basis. Dropping some would be silent
  // filtering of measured neighbours — the thing `withheld` exists to prevent.
  const relation = buildThreadRelation(pool ?? [], measuresConnected ? scope.id : null, { resolveCountryName })
  const connectedRows: ConnectedRow[] = relation.related.map((r) => ({
    id: r.thread.thread_id,
    label: r.thread.label,
    receipt: r.receipt,
    kind: 'thread',
  }))
  // A measured pool that does not contain the open thread measured NOTHING
  // about it — a different statement from "we compared and found none", which
  // is what an `ok` lane with zero rows says. Reachable by deep link, and by
  // any thread that has since fallen out of the ranked field.
  const connectedStatus: LaneStatus = settledConnected
    ?? (poolLane === 'ok' && !relation.anchor ? 'no_subject' : poolLane)

  // Only the two ROW-BUILT sections are destructured. buildSections also
  // returns `attention`, and this surface fills that section by mounting
  // <AnomalyPanel/> instead (see the header note) — so the pure model's
  // attention rows are unused here and the empty payload below is honest
  // rather than lazy.
  //
  // The superseded reason is worth recording because it was WRONG in exactly
  // the way N29 describes: this section used to be skipped on the grounds that
  // "public attention is already carried inside each scope's own panel —
  // AnomalyPanel re-scopes itself". True on the desktop, where the dock mounts
  // it. On the phone the dock is not mounted at all, so the argument justified
  // an absence by pointing at a panel that was not there.
  const { whereItLives, connected } = buildSections(
    { countries: rows ?? [], connected: connectedRows, attention: [] },
    { whereItLives: lane, connected: connectedStatus },
  )

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
              exists to avoid.
              Mapped from the shared list rather than written out, so a section
              added to the sheet cannot go unannounced on the bar that is the
              only way in. */}
          {SHEET_SECTION_NAMES.map((name) => (
            <span key={name} className="lens-sections-name">{name}</span>
          ))}
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
            <h3 className="section-label lens-section-label">{SECTION_LABELS.whereItLives}</h3>
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
            <h3 className="section-label lens-section-label">{SECTION_LABELS.connected}</h3>
            {connected.state === 'ok' ? (
              <ul className="lens-section-rows">
                {connected.rows.map((r) => (
                  <li key={r.id}>
                    <button
                      type="button"
                      className="lens-section-row lens-section-row--stacked"
                      onClick={() => { setOpen(false); onOpenThread(r.id, r.label) }}
                    >
                      <span className="lens-row-name">{r.label}</span>
                      {/* Rule 2: the basis rides with the row, always. It wraps
                          rather than truncating — a receipt you cannot read is
                          not a receipt. */}
                      <span className="lens-row-receipt">↔ {r.receipt}</span>
                    </button>
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

          {/* Sections 5 and 6 — the intel organ, mounted rather than rebuilt.
              Both panels scope THEMSELVES, so neither takes a scope prop; both
              are only constructed here because the sheet is `open`, which is
              what keeps a section nobody opens free on a phone.

              No `onClose` is threaded into either. Every door they carry —
              a geo alert, a conflict, a theme spike, a wiki/trend/forum row —
              changes the console's focus, which changes this sheet's `key`
              (scopeKey, at the render site below) and remounts it closed. One
              mechanism, already load-bearing for the two sections above, and a
              second one would only be free to disagree with it. */}
          <section className="lens-section">
            <h3 className="section-label lens-section-label">{SECTION_LABELS.attention}</h3>
            <div className="lens-section-panel">{attention}</div>
          </section>

          <section className="lens-section">
            <h3 className="section-label lens-section-label">{SOURCES_SECTION_LABEL}</h3>
            <div className="lens-section-panel">{sources}</div>
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
export function LensPanel({
  surface, trail, onBack, onOpenCountry, onOpenThread, countryScope, field, read,
  attention, sources,
}: LensPanelProps) {
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
          no scope furniture, so it gets no sections either.
          KEYED ON THE SCOPE so a pivot REMOUNTS the sheet. Its measured
          `sheetTop`, its rows and its lane all belong to one scope; carrying
          them across a pivot shows the previous scope's answer under the new
          scope's name — the exact confound this section was rebuilt to avoid,
          arriving by a different door. */}
      {showsChrome && scope && (
        <LensSectionSheet
          key={scopeKey(scope)}
          scope={scope}
          countryScope={countryScope}
          onOpenCountry={onOpenCountry}
          onOpenThread={onOpenThread}
          attention={attention}
          sources={sources}
        />
      )}
      <div key="lens-field" style={{ display: showsField ? 'contents' : 'none' }}>{field}</div>
      <div key="lens-read" style={{ display: showsField ? 'none' : 'contents' }}>{read}</div>
    </>
  )
}
