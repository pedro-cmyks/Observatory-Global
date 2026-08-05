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
 * things — it is DERIVED from the console's own focus state by
 * `consoleLensScope`. That is deliberate. If each door pushed its own scope,
 * the trail would be a second notion of "what am I looking at", free to
 * disagree with the panel actually on screen. Derivation makes disagreement
 * unrepresentable: the panel and the breadcrumb read the same state.
 */
export type LensScopeKind =
  // The five scopes the Lens design names.
  | 'field'
  | 'thread'
  | 'country'
  | 'person'
  | 'signal'
  // Three more the console can actually reach. They are here because the
  // alternative — filing them under one of the five — would make the
  // breadcrumb name a thing the panel is not showing. `story` is a research
  // plan over a free query; `attention` is a trends/wiki item; `chokepoint`
  // is a maritime passage. See consoleLensScope for how each is reached.
  | 'story'
  | 'attention'
  | 'chokepoint'

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
 * Part of this module's API and tested, but NOT how the app goes back today:
 * because the head is derived, popping the trail alone would be re-pushed on
 * the next render. The Lens's back button drives the console's own `popPanel`
 * and the trail follows. Kept because the rewind is the trail's own
 * definition, and Task 8 may need it once a scope owns state of its own.
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
 * Derive the scope the console is CURRENTLY showing.
 *
 * COUPLING, named so it is not discovered the hard way: the guards and the
 * pick order below mirror the stream slot's ladder in App.tsx (the
 * `isStory`/`isThread`/... booleans and the JSX chain that consumes them,
 * which are NOT in the same order — the guards make most pairs mutually
 * exclusive and the JSX settles the rest). Change one without the other and
 * the Lens names one thing while rendering another. Both are exercised by
 * the precedence tests in lensScope.test.ts.
 *
 * There is deliberately no `signal` branch: an open signal lives in
 * SignalStream's own local state, not the console's, so the phone cannot
 * reach a signal scope yet. That is a gap, not an oversight — see the Lens
 * report for Task 7.
 */
export function consoleLensScope(f: ConsoleFocus): LensScope {
  const isStory = !!f.storyQuery
  const isThread = !!f.threadId && !isStory
  const isTheme = !!f.themeId && !isThread && !isStory
  const isPerson = !!f.personName && !isStory && !isThread && !isTheme
  const isCountry = !!f.countryCode && !isPerson && !isTheme && !isThread && !isStory
  const isAttention = !!f.attentionTitle && !isPerson && !isCountry && !isTheme && !isStory
  const isChokepoint = !!f.chokepointId && !isPerson && !isCountry && !isTheme && !isAttention && !isStory

  // Pick order = the JSX chain's order, not the declaration order above.
  if (isStory) return { kind: 'story', id: f.storyQuery!, label: f.storyQuery! }
  if (isPerson) return { kind: 'person', id: f.personName!, label: f.personName! }
  if (isAttention) return { kind: 'attention', id: f.attentionTitle!, label: f.attentionTitle! }
  if (isThread) return { kind: 'thread', id: f.threadId!, label: f.threadLabel || f.threadId! }
  if (isCountry) return { kind: 'country', id: f.countryCode!, label: f.countryName || f.countryCode! }
  if (isTheme) return { kind: 'thread', id: f.themeId!, label: f.themeLabel || f.themeId! }
  if (isChokepoint) return { kind: 'chokepoint', id: f.chokepointId!, label: f.chokepointName || f.chokepointId! }
  return FIELD_SCOPE
}
