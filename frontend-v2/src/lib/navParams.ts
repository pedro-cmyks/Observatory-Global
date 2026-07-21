export interface BriefParamState {
  country?: string | null
  theme?: string | null
  themeLabel?: string | null
  storyQuery?: string | null
}

export function buildBriefParams(state: BriefParamState): string {
  const p = new URLSearchParams()
  if (state.country) p.set('country', state.country)
  if (state.theme) p.set('theme', state.theme)
  if (state.theme && state.themeLabel) p.set('label', state.themeLabel)
  if (state.storyQuery) p.set('q', state.storyQuery)
  return p.toString()
}

export interface ConsoleDeepLink {
  q: string | null
  theme: string | null
  label: string | null
  country: string | null
  attention: string | null
}

export function parseConsoleDeepLink(search: string): ConsoleDeepLink {
  const p = new URLSearchParams(search)
  return {
    q: p.get('q'),
    theme: p.get('theme'),
    label: p.get('label'),
    country: p.get('country'),
    attention: p.get('attention'),
  }
}

/** Merge the owned focus dims (theme/country/person) into an existing query
 *  string WITHOUT dropping any other params (q/label/attention/entry — the
 *  carry-context params). Empty focus dims are removed; everything else is
 *  preserved. Returns the serialized query string. */
export function mergeFocusIntoParams(
  currentSearch: string,
  focus: { theme?: string | null; country?: string | null; person?: string | null },
): string {
  const p = new URLSearchParams(currentSearch)
  focus.theme ? p.set('theme', focus.theme) : p.delete('theme')
  focus.country ? p.set('country', focus.country) : p.delete('country')
  focus.person ? p.set('person', focus.person) : p.delete('person')
  return p.toString()
}
