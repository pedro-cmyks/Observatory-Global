// Signal-stream tab model — pure. (Eclipse spec §6.4, Phase 4.)
//
// Outside the Eclipse Lens the stream keeps its two category groups exactly as
// they were. Inside the lens (mode === 'ambient') the categories collapse to
// ECLIPSE / SHADOW / ALL and the stream stops being a theme filter: it becomes
// a TOPIC scope, resolved server-side through `/api/v2/signals?topic=` (a
// signal row carries no topic linkage, so eclipse/shadow cannot be decided in
// the client — that is why this phase was gated on the backend filter).
//
// The default inside the lens is SHADOW, not ECLIPSE: the whole point of the
// lens is that the eclipsing story is already everywhere. Landing on Shadow is
// the reframe.
import type { EclipseData } from './attentionEclipse'

/** Category tabs — the pre-eclipse behaviour, unchanged. */
export const STREAM_PRIMARY_TABS = ['all', 'critical', 'elevated', 'notable'] as const
export const STREAM_SECONDARY_TABS = ['conflict', 'disaster', 'trend', 'person', 'maritime'] as const

/** Lens tabs. 'all' is deliberately shared with the category set: the escape
 *  hatch out of the scope is the SAME tab that means "everything" normally. */
export const ECLIPSE_TABS = ['eclipse', 'shadow', 'all'] as const

export type StreamCategoryTab =
  | (typeof STREAM_PRIMARY_TABS)[number]
  | (typeof STREAM_SECONDARY_TABS)[number]
export type StreamEclipseTab = (typeof ECLIPSE_TABS)[number]
export type StreamTab = StreamCategoryTab | StreamEclipseTab

export const STREAM_DEFAULT_TAB: StreamCategoryTab = 'notable'
export const ECLIPSE_DEFAULT_TAB: StreamEclipseTab = 'shadow'

/** Mirrors the backend cap (`_TOPIC_FILTER_MAX` in routers/signals.py). Ids past
 *  it are dropped by the server anyway; truncating here keeps the URL honest
 *  about what was actually asked for. */
export const TOPIC_PARAM_MAX = 12

export interface StreamTabModel {
  /** true = the Eclipse Lens is engaged and the tab bar is the lens's. */
  eclipse: boolean
  /** First tab group (the only group in lens mode). */
  primary: readonly StreamTab[]
  /** Second tab group, after the separator. Empty in lens mode. */
  secondary: readonly StreamTab[]
  /** The tab to land on when this model becomes active. */
  defaultTab: StreamTab
}

const CATEGORY_MODEL: StreamTabModel = {
  eclipse: false,
  primary: STREAM_PRIMARY_TABS,
  secondary: STREAM_SECONDARY_TABS,
  defaultTab: STREAM_DEFAULT_TAB,
}

const ECLIPSE_MODEL: StreamTabModel = {
  eclipse: true,
  primary: ECLIPSE_TABS,
  secondary: [],
  defaultTab: ECLIPSE_DEFAULT_TAB,
}

/** Which tab bar the stream renders. `eclipseActive` is the caller's
 *  `mode === 'ambient' && data != null` — the lens must never claim a scope it
 *  has no topic ids for. */
export function streamTabModel(eclipseActive: boolean): StreamTabModel {
  return eclipseActive ? ECLIPSE_MODEL : CATEGORY_MODEL
}

/** Keep the selected tab valid across a mode flip: a category tab is
 *  meaningless inside the lens and vice versa, so fall back to the model's
 *  default rather than silently rendering an unselected bar. */
export function resolveStreamTab(current: StreamTab, model: StreamTabModel): StreamTab {
  if (model.primary.includes(current) || model.secondary.includes(current)) return current
  return model.defaultTab
}

/** The `topic=` value for a tab, or null when the tab is not topic-scoped
 *  (every category tab, plus the lens's ALL escape hatch).
 *
 *  Returns null — never an empty string — when the scope would be empty: the
 *  server reads an empty `topic=` as "asked for a scope, nothing valid" and
 *  answers with zero signals, which is right for garbage but wrong for a
 *  dominant that simply has no topic_id. In that case there is no scope to
 *  apply and the honest fallback is the unscoped stream. */
export function eclipseTopicParam(
  tab: StreamTab,
  data: EclipseData | null | undefined,
  cap: number = TOPIC_PARAM_MAX,
): string | null {
  if (!data) return null
  const ids: string[] = []
  if (tab === 'eclipse') {
    const dom = data.dominant?.topic_id
    if (dom) ids.push(dom)
  } else if (tab === 'shadow') {
    for (const item of data.selected ?? []) {
      if (item?.topic_id && !ids.includes(item.topic_id)) ids.push(item.topic_id)
    }
  } else {
    return null
  }
  if (ids.length === 0) return null
  return ids.slice(0, Math.max(0, cap)).join(',')
}

/** Row tint class for a topic-scoped tab — reuses the `ecl-` vocabulary the
 *  threads panel already established (red = the eclipse, cyan = its shadow). */
export function streamRowEclipseClass(tab: StreamTab): string {
  if (tab === 'eclipse') return 'ecl-row-eclipse'
  if (tab === 'shadow') return 'ecl-row-shadow'
  return ''
}

/** Human label for the tab bar. */
export function streamTabLabel(tab: StreamTab): string {
  return tab.toUpperCase()
}
