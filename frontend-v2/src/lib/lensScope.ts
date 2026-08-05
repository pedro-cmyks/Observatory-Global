/**
 * The Lens is one anatomy at N scopes. This module owns the scope value, the
 * breadcrumb trail between scopes, and the ONE derivation from console state
 * to a scope.
 *
 * Re-visiting an earlier scope REWINDS the trail instead of appending, so
 * pivoting thread -> country -> back to the same thread cannot grow an
 * unbounded breadcrumb.
 *
 * SINGLE SOURCE OF TRUTH: the trail's head is not set by the doors that open
 * things — it is DERIVED from the console's own focus state. If each door
 * pushed its own scope, the trail would be a second notion of "what am I
 * looking at", free to disagree with the panel actually on screen.
 *
 * That derivation runs through `consoleSlot`, which is THE ladder: App's
 * stream slot calls it to decide which panel to render, and `consoleLensScope`
 * calls it to decide what the Lens names. One function, two callers, so the
 * breadcrumb and the panel cannot pick differently. (The first cut of this
 * module transcribed App's ladder by hand and claimed disagreement was
 * "unrepresentable" — with two copies it was merely well-guarded. Now the
 * copy is gone.)
 */
export type ReachableScopeKind =
  | 'field'
  | 'thread'
  | 'country'
  | 'person'
  // Three more the console can reach that the five-scope sketch did not name.
  // They are here because the alternative — filing them under one of the five
  // — would make the breadcrumb name a thing the panel is not showing.
  // `story` is a research plan over a free query; `attention` is a
  // trends/wiki item; `chokepoint` is a maritime passage.
  | 'story'
  | 'attention'
  | 'chokepoint'

/**
 * `signal` is in the union and has NO producer: an open signal lives in
 * SignalStream's own local state, not the console's, so `consoleSlot` cannot
 * see one and the phone cannot reach the scope. Splitting the union is how
 * that deferral stays visible in the type rather than in a comment someone
 * has to find.
 */
export type LensScopeKind = ReachableScopeKind | 'signal'

export interface LensScope {
  kind: LensScopeKind
  id: string
  label: string
}

export const FIELD_SCOPE: LensScope = { kind: 'field', id: '*', label: 'The world' }

export function scopeKey(s: LensScope): string {
  return `${s.kind}:${s.id}`
}

/**
 * Append, or rewind to an earlier visit of the same scope.
 *
 * A matched scope is REPLACED by `next` rather than kept, so a label that
 * resolves late (a deep-link opens `dynamic-topic-8057` and ThemeDetail names
 * it seconds later) reaches the breadcrumb. Key equality decides identity;
 * the label is only ever display.
 */
export function pushScope(trail: LensScope[], next: LensScope): LensScope[] {
  const base = trail.length ? trail : [FIELD_SCOPE]
  const at = base.findIndex((s) => scopeKey(s) === scopeKey(next))
  if (at >= 0) return [...base.slice(0, at), next]
  return [...base, next]
}

/**
 * Walk the trail back one step.
 *
 * Never called ALONE — popping the trail on its own does not move the console,
 * so the head would sit wrong until the next scope change (it would not be
 * "re-pushed on the next render": the push effect is dep-gated on the derived
 * scope, which did not change). It is called TOGETHER with the console's own
 * `popPanel`, and that pairing is what stops a back-tap from DEEPENING the
 * trail: peeling a thread can reveal a country the trail never visited, which
 * a bare append would add on top of the thread just closed — leaving a
 * breadcrumb pointing at it, one tap from a loop. Shortening first means the
 * revealed scope lands at the same depth instead.
 */
export function popScope(trail: LensScope[]): LensScope[] {
  if (trail.length <= 1) return [FIELD_SCOPE]
  return trail.slice(0, -1)
}

export function scopeTitle(s: LensScope): string {
  return s.label
}

/**
 * Value equality for a whole trail. The trail is re-derived on every render of
 * the console, so without this the context would hand out a fresh array (and
 * re-render every consumer) on renders where nothing about the scope changed.
 * Compares label too — a late-resolving label IS a change worth propagating.
 */
export function trailsEqual(a: LensScope[], b: LensScope[]): boolean {
  if (a.length !== b.length) return false
  return a.every((s, i) => scopeKey(s) === scopeKey(b[i]) && s.label === b[i].label)
}

/**
 * The console's focus state, as the stream slot reads it.
 *
 * `threadId` is ThreadFocusPanel's thread; `themeId` is ThemeDetail's theme.
 * Both are threads to a reader, so both derive a `thread` scope — they differ
 * only in which panel renders them.
 *
 * Presence is decided by the ID being truthy. App used to test the enclosing
 * OBJECT (`!!selectedTheme`), which is a slightly wider predicate: an object
 * carrying an empty id would have rendered ThemeDetail. Now that App reads its
 * slot from here, whatever the predicate is, both callers get the same answer
 * — the asymmetry is gone rather than documented.
 */
export interface ConsoleFocus {
  storyQuery: string | null
  threadId: string | null
  threadLabel: string | null
  themeId: string | null
  themeLabel: string | null
  personName: string | null
  countryCode: string | null
  countryName: string | null
  attentionTitle: string | null
  chokepointId: string | null
  chokepointName: string | null
}

/**
 * What the console's stream slot renders. `thread` is ThreadFocusPanel and
 * `theme` is ThemeDetail — two panels a reader would call the same thing, so
 * they collapse to one Lens scope but stay distinct here, because App has to
 * pick a component.
 */
export type ConsoleSlot =
  | 'blank'
  | 'story'
  | 'person'
  | 'attention'
  | 'thread'
  | 'country'
  | 'theme'
  | 'chokepoint'

/**
 * THE ladder. App's stream slot calls this to choose a panel; consoleLensScope
 * calls it to choose a name. Previously App held one copy and this module held
 * a transcription of it.
 *
 * Two orders are folded in here, and they are genuinely different: the GUARDS
 * (which make most pairs mutually exclusive) and the PICK order (which settles
 * the pairs the guards leave open). `attention` over `thread` is the one place
 * they truly diverge — the guards permit both, and the pick resolves it. Both
 * are pinned by the precedence tests.
 *
 * `liveTab` collapses everything to `blank`: on the phone's Live tab the slot
 * is the firehose whatever is focused. The Lens passes `false` — it must keep
 * naming the scope it will return to while Live is on screen.
 */
export function consoleSlot(f: ConsoleFocus, liveTab: boolean): ConsoleSlot {
  if (liveTab) return 'blank'
  const isStory = !!f.storyQuery
  const isThread = !!f.threadId && !isStory
  const isTheme = !!f.themeId && !isThread && !isStory
  const isPerson = !!f.personName && !isStory && !isThread && !isTheme
  const isCountry = !!f.countryCode && !isPerson && !isTheme && !isThread && !isStory
  const isAttention = !!f.attentionTitle && !isPerson && !isCountry && !isTheme && !isStory
  const isChokepoint = !!f.chokepointId && !isPerson && !isCountry && !isTheme && !isAttention && !isStory

  if (isStory) return 'story'
  if (isPerson) return 'person'
  if (isAttention) return 'attention'
  if (isThread) return 'thread'
  if (isCountry) return 'country'
  if (isTheme) return 'theme'
  if (isChokepoint) return 'chokepoint'
  return 'blank'
}

/** Name the scope the console is showing, off the same ladder that renders it. */
export function consoleLensScope(f: ConsoleFocus): LensScope {
  switch (consoleSlot(f, false)) {
    case 'story': return { kind: 'story', id: f.storyQuery!, label: f.storyQuery! }
    case 'person': return { kind: 'person', id: f.personName!, label: f.personName! }
    case 'attention': return { kind: 'attention', id: f.attentionTitle!, label: f.attentionTitle! }
    case 'thread': return { kind: 'thread', id: f.threadId!, label: f.threadLabel || f.threadId! }
    case 'country': return { kind: 'country', id: f.countryCode!, label: f.countryName || f.countryCode! }
    case 'theme': return { kind: 'thread', id: f.themeId!, label: f.themeLabel || f.themeId! }
    case 'chokepoint': return { kind: 'chokepoint', id: f.chokepointId!, label: f.chokepointName || f.chokepointId! }
    default: return FIELD_SCOPE
  }
}
