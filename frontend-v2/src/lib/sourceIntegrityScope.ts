import { resolveCountryName } from './countryNames'
import { getThemeLabel } from './themeLabels'

export interface SourceIntegrityScopeInput {
  country?: string | null
  theme?: string | null
  person?: string | null
  entity?: string | null
  viewingLabel?: string | null
}

export interface SourceIntegrityScopeLabel {
  heading: string
  sublabel: string | null
  scoped: boolean
}

export function buildSourceIntegrityScopeLabel(input: SourceIntegrityScopeInput): SourceIntegrityScopeLabel {
  if (input.country) {
    return {
      heading: resolveCountryName(input.country),
      sublabel: 'Scoped to active country',
      scoped: true,
    }
  }
  if (input.theme) {
    return {
      heading: getThemeLabel(input.theme),
      sublabel: 'Scoped to active thread/topic',
      scoped: true,
    }
  }
  const person = input.person || input.entity
  if (person) {
    return {
      heading: person,
      sublabel: 'Scoped to active person',
      scoped: true,
    }
  }
  if (input.viewingLabel) {
    return {
      heading: 'Global background',
      sublabel: `Viewing ${input.viewingLabel}`,
      scoped: false,
    }
  }
  return {
    heading: 'Global aggregate',
    sublabel: null,
    scoped: false,
  }
}
