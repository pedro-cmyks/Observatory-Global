interface PublicAttentionScopeInput {
  title: string
  hours: number
  countryCode?: string | null
  countryName?: string | null
}

interface PublicAttentionScopeLabel {
  label: string
  detail: string
}

export function buildPublicAttentionScopeLabel(input: PublicAttentionScopeInput): PublicAttentionScopeLabel {
  const country = input.countryName || input.countryCode
  if (country) {
    return {
      label: `Country origin: ${country}`,
      detail: `Opened from ${country}. Media matches below are still global unless a country is selected.`,
    }
  }

  return {
    label: 'Global media match',
    detail: `Comparing people-side attention for ${input.title} against global media signals in the last ${input.hours}h.`,
  }
}
