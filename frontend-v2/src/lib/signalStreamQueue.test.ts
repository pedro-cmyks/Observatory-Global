import { describe, expect, it } from 'vitest'
import {
  mergeStreamItems,
  splitInitialStreamBatch,
  type StreamQueueItem,
} from './signalStreamQueue'

function item(id: number, minutesAgo: number): StreamQueueItem {
  return {
    type: 'signal',
    id,
    timestamp: new Date(Date.now() - minutesAgo * 60_000).toISOString(),
  }
}

describe('signalStreamQueue', () => {
  it('keeps a visible initial set and buffers the rest for live drip', () => {
    const batch = Array.from({ length: 20 }, (_, index) => item(index + 1, index))

    const { visible, queue } = splitInitialStreamBatch(batch, 8)

    expect(visible.map(i => i.id)).toEqual([1, 2, 3, 4, 5, 6, 7, 8])
    expect(queue.map(i => i.id)).toEqual([9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
  })

  it('deduplicates while preserving visual arrival order', () => {
    const merged = mergeStreamItems([item(4, 0), item(2, 1)], [item(1, 3), item(2, 2), item(3, 1)], 10)

    expect(merged.map(i => i.id)).toEqual([4, 2, 1, 3])
  })
})
