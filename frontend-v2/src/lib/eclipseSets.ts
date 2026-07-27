import type { EclipseData } from './attentionEclipse'

export const ECLIPSE_COLOR = 'var(--eclipse-red, #e23a1a)'
export const SHADOW_COLOR = 'var(--eclipse-cyan, #2aa7ad)'

export interface EclipseSets {
  eclipseTopics: Set<string>
  shadowTopics: Set<string>
  eclipseCountries: Set<string>
  shadowCountries: Set<string>
}

/** neighborIds = the dominant topic's universe neighbours (caller supplies them via
 * the existing edge walk). The dominant's footprint countries win over shadow
 * countries when both claim the same code. */
export function buildEclipseSets(d: EclipseData | null | undefined, neighborIds: string[] = []): EclipseSets {
  const eclipseTopics = new Set<string>()
  const shadowTopics = new Set<string>()
  const eclipseCountries = new Set<string>()
  const shadowCountries = new Set<string>()
  const domId = d?.dominant?.topic_id
  if (domId) eclipseTopics.add(domId)
  for (const id of neighborIds) eclipseTopics.add(id)
  for (const cc of d?.dominant?.countries ?? []) eclipseCountries.add(cc)
  for (const item of d?.selected ?? []) {
    shadowTopics.add(item.topic_id)
    for (const cc of item.countries ?? []) shadowCountries.add(cc)
  }
  for (const cc of eclipseCountries) shadowCountries.delete(cc)
  return { eclipseTopics, shadowTopics, eclipseCountries, shadowCountries }
}

export function eclipseTopicColor(topicId: string, s: EclipseSets): string | null {
  if (s.eclipseTopics.has(topicId)) return ECLIPSE_COLOR
  if (s.shadowTopics.has(topicId)) return SHADOW_COLOR
  return null
}

export function countryLens(cc: string, s: EclipseSets): 'eclipse' | 'shadow' | null {
  if (s.eclipseCountries.has(cc)) return 'eclipse'
  if (s.shadowCountries.has(cc)) return 'shadow'
  return null
}

export function threadEclipseRole(anchorTopics: string[] | undefined, threadId: string,
                                  s: EclipseSets): 'eclipse' | 'shadow' | null {
  const ids = [threadId, ...(anchorTopics ?? [])]
  if (ids.some(id => s.eclipseTopics.has(id))) return 'eclipse'
  if (ids.some(id => s.shadowTopics.has(id))) return 'shadow'
  return null
}
