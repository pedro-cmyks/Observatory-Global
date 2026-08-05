/**
 * A thread row on a phone leads with its title.
 *
 * The mobile audit measured ~290px per row where the title truncated while five
 * entity chips wrapped over three lines. Chips are context; the title is the
 * story. We cap the chips and state the remainder — a count, never a silent
 * drop.
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
