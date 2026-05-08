const PUBLIC_ATTENTION_WIKI_DAYS = 7

export function getPublicAttentionTopUrl(limit: number): string {
  return `/api/v2/wiki/top?days=${PUBLIC_ATTENTION_WIKI_DAYS}&limit=${limit}`
}
