// Pure focus-transition reducer. Encodes the FocusContext setter table with the
// compound-focus edits: country/theme no longer clear person; person no longer
// clears country/theme/themeLabel. thread and region are exclusive full resets;
// concept keeps country/region and nulls thread/entity/person/themeLabel.
// ConceptFilter/RegionFilter are opaque here (typed as unknown) — the reducer
// only ever nulls or passes them through, never inspects them.

export interface FocusDims {
  thread: string | null
  country: string | null
  theme: string | null
  entity: string | null
  person: string | null
  themeLabel: string | null
  concept: unknown | null
  region: unknown | null
}

export const EMPTY_DIMS: FocusDims = {
  thread: null, country: null, theme: null, entity: null,
  person: null, themeLabel: null, concept: null, region: null,
}

export type FocusAction =
  | { dim: 'country'; value: string | null }
  | { dim: 'theme'; value: string | null; label?: string | null }
  | { dim: 'person'; value: string | null }
  | { dim: 'entity'; value: string | null }
  | { dim: 'thread'; value: string | null; label?: string | null }
  | { dim: 'concept'; value: unknown | null }
  | { dim: 'region'; value: unknown | null }
  | { dim: 'clear' }

export function nextFocusDims(prev: FocusDims, action: FocusAction): FocusDims {
  switch (action.dim) {
    case 'clear':
      return { ...EMPTY_DIMS }
    case 'country':
      return { ...prev, country: action.value, thread: null }
    case 'theme':
      return {
        ...prev,
        theme: action.value,
        thread: null,
        themeLabel: action.value ? (action.label ?? (prev.theme === action.value ? prev.themeLabel : null)) : null,
      }
    case 'person':
      return {
        ...prev,
        person: action.value,
        entity: action.value,
        thread: null,
      }
    case 'entity':
      return {
        ...prev,
        entity: action.value,
        person: prev.person && prev.person === prev.entity && prev.person !== action.value ? null : prev.person,
        thread: null,
      }
    case 'thread':
      return {
        ...EMPTY_DIMS,
        thread: action.value,
        // themeLabel doubles as the thread's label (no separate threadLabel field in GlobalFilter)
        themeLabel: action.value ? (action.label ?? null) : null,
      }
    case 'concept':
      return { ...prev, concept: action.value, thread: null, entity: null, person: null, themeLabel: null }
    case 'region':
      return { ...EMPTY_DIMS, region: action.value }
    default:
      return prev
  }
}
