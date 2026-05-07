export interface StreamQueueItem {
  type: string
  id: number | string
  timestamp: string
}

function itemKey(item: StreamQueueItem): string {
  return `${item.type}-${item.id}`
}

export function splitInitialStreamBatch<T extends StreamQueueItem>(
  items: T[],
  visibleCount: number,
): { visible: T[]; queue: T[] } {
  return {
    visible: items.slice(0, visibleCount),
    queue: items.slice(visibleCount),
  }
}

export function mergeStreamItems<T extends StreamQueueItem>(
  incoming: T[],
  current: T[],
  limit: number,
): T[] {
  const seen = new Set<string>()
  const merged: T[] = []

  for (const item of [...incoming, ...current]) {
    const key = itemKey(item)
    if (seen.has(key)) continue
    seen.add(key)
    merged.push(item)
    if (merged.length >= limit) break
  }

  return merged
}
