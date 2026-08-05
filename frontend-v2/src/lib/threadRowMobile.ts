/**
 * A thread row on a phone leads with its title.
 *
 * The mobile audit measured ~290px per row where the title truncated while five
 * entity chips wrapped over three lines. Chips are context; the title is the
 * story. We cap the chips and state the remainder — a count, never a silent
 * drop.
 *
 * `hiddenCount` here is only honest relative to whatever `entities` array is
 * passed in. If a caller pre-truncates its input before calling this (e.g.
 * NarrativeThreads.tsx's separate, pre-existing desktop 4-cap), it must
 * compute the TRUE remainder itself against the untruncated total — this
 * function has no way to know about a ceiling applied before it ever sees
 * the list.
 */
export const MOBILE_ENTITY_CAP = 2

export interface VisibleEntities {
  shown: string[]
  hiddenCount: number
}

export function visibleEntities(entities: string[], isMobile: boolean): VisibleEntities {
  if (!isMobile) return { shown: entities, hiddenCount: 0 }
  return {
    shown: entities.slice(0, MOBILE_ENTITY_CAP),
    hiddenCount: Math.max(0, entities.length - MOBILE_ENTITY_CAP),
  }
}
