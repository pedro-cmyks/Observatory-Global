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
