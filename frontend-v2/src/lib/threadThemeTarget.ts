export interface ThreadThemeTargetInput {
  thread_id: string
  label: string
  anchor_topics?: string[]
  top_countries?: string[]
  top_country_names?: string[]
}

export interface ThreadThemeTarget {
  theme: string
  originCountry?: string
  originCountryName?: string
  thread: {
    thread_id: string
    label: string
  }
}

export function resolveThreadThemeTarget(thread: ThreadThemeTargetInput): ThreadThemeTarget | null {
  const threadId = thread.thread_id
  if (threadId.startsWith('emergent-cluster-')) return null

  const theme = threadId.startsWith('dynamic-topic-')
    ? threadId
    : thread.anchor_topics?.[0]

  if (!theme) return null

  const countryCode = thread.top_countries?.length === 1
    ? thread.top_countries[0]
    : undefined
  const countryName = countryCode
    ? (thread.top_country_names?.[0] || countryCode)
    : undefined

  return {
    theme,
    originCountry: countryCode,
    originCountryName: countryName,
    thread: {
      thread_id: thread.thread_id,
      label: thread.label,
    },
  }
}
