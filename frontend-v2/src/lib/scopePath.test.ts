import { describe, it, expect } from 'vitest'
import {
  buildScopePath,
  currentScope,
  isCurrentScope,
  isOpaqueStoryId,
  isWorldScope,
  levelsDroppedBy,
  storyTypeLabel,
  SCOPE_ORDER,
} from './scopePath'

/** The app injects `resolveThreadLabel`; tests inject its behaviour, not it. */
const resolver = (id: string, known?: string | null): string => {
  if (known?.trim()) return known
  if (isOpaqueStoryId(id)) return 'Story' // the generic fallback that caused "STORY Story"
  return id.split('--')[0].replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

const build = (input: Parameters<typeof buildScopePath>[0]) =>
  buildScopePath(input, { resolveStoryLabel: resolver })

const labels = (input: Parameters<typeof buildScopePath>[0]) => build(input).map((c) => c.label)
const levels = (input: Parameters<typeof buildScopePath>[0]) => build(input).map((c) => c.level)

describe('buildScopePath — the world is always a scope', () => {
  it('renders the world crumb with nothing focused', () => {
    const path = build({})
    expect(path).toHaveLength(1)
    expect(path[0]).toEqual({ level: 'world', id: '*', typeLabel: null, label: 'World', pending: false })
    expect(isWorldScope(path)).toBe(true)
  })

  it('treats empty strings as unfocused, not as a scope with a blank name', () => {
    expect(levels({ country: '', person: '   ', theme: '' })).toEqual(['world'])
  })

  it('takes the world label from options for a bilingual surface', () => {
    expect(buildScopePath({}, { worldLabel: 'Mundo' })[0].label).toBe('Mundo')
  })
})

describe('buildScopePath — one dimension at a time', () => {
  it('country: prints the resolved name, never the code', () => {
    const path = build({ country: 'CO', countryName: 'Colombia' })
    expect(path.map((c) => c.label)).toEqual(['World', 'Colombia'])
    expect(path[1]).toMatchObject({ level: 'country', id: 'CO', typeLabel: 'Country', pending: false })
  })

  it('country: falls back to the code when no name resolved (never blank)', () => {
    expect(labels({ country: 'ZZ' })).toEqual(['World', 'ZZ'])
  })

  it('person: renders World ▸ person — a person is not filed under a country it has none', () => {
    const path = build({ person: 'gustavo petro' })
    expect(path.map((c) => c.label)).toEqual(['World', 'gustavo petro'])
    expect(path[1].typeLabel).toBe('Person')
  })

  it('story: a dynamic topic with a known label is a Story', () => {
    const path = build({ theme: 'dynamic-topic-8057', storyLabel: 'Ceuta Migrant Crisis' })
    expect(path.map((c) => c.label)).toEqual(['World', 'Ceuta Migrant Crisis'])
    expect(path[1]).toMatchObject({ level: 'story', typeLabel: 'Story', pending: false })
  })

  it('story: an atlas category id is a Theme, and its slug is prettified by the resolver', () => {
    const path = build({ theme: 'election-legitimacy--co' })
    expect(path[1]).toMatchObject({ level: 'story', typeLabel: 'Theme', label: 'Election Legitimacy', pending: false })
  })

  it('signal: the leaf carries its headline', () => {
    const path = build({ signal: { id: '551', label: 'Ceuta border reopens' } })
    expect(path.map((c) => c.level)).toEqual(['world', 'signal'])
    expect(path[1]).toMatchObject({ id: '551', typeLabel: 'Signal', pending: false })
  })
})

describe('buildScopePath — the cold-loading story never stutters', () => {
  it('an opaque id with no label is pending and prints an ellipsis, not "Story"', () => {
    const path = build({ theme: 'dynamic-topic-8057' })
    expect(path[1]).toMatchObject({ typeLabel: 'Story', label: '…', pending: true })
    // The defect this guards: type word + generic fallback rendered "STORY Story".
    expect(path[1].label.toLowerCase()).not.toBe('story')
  })

  it('the same crumb resolves as soon as a label arrives', () => {
    const cold = build({ theme: 'dynamic-topic-8057' })
    const warm = build({ theme: 'dynamic-topic-8057', storyLabel: 'Ceuta Migrant Crisis' })
    expect(cold[1].pending).toBe(true)
    expect(warm[1].pending).toBe(false)
    expect(warm[1].label).toBe('Ceuta Migrant Crisis')
    expect(cold[1].id).toBe(warm[1].id) // same scope, only the name changed
  })

  it('a resolver that echoes the id back is treated as pending, not as a name', () => {
    const path = buildScopePath({ theme: 'dynamic-topic-8057' }, { resolveStoryLabel: (id) => id })
    expect(path[1]).toMatchObject({ label: '…', pending: true })
  })

  it('every generic fallback the resolver can emit is caught, case-insensitively', () => {
    for (const generic of ['Story', 'stories', 'Unknown', 'Narrative Thread']) {
      const path = buildScopePath({ theme: 'dynamic-topic-1' }, { resolveStoryLabel: () => generic })
      expect(path[1].pending, generic).toBe(true)
      expect(path[1].label, generic).toBe('…')
    }
  })

  it('a signal with no headline is pending too', () => {
    expect(build({ signal: { id: '9' } })[1]).toMatchObject({ label: '…', pending: true })
  })

  it('with no resolver injected, a known label still wins and an unknown id is pending', () => {
    expect(buildScopePath({ theme: 'dynamic-topic-1', storyLabel: 'Real Name' })[1].label).toBe('Real Name')
    expect(buildScopePath({ theme: 'dynamic-topic-1' })[1].pending).toBe(true)
  })
})

describe('buildScopePath — compound focus becomes one path', () => {
  it('country + person narrows: the person sits inside the country scope', () => {
    expect(labels({ country: 'CO', countryName: 'Colombia', person: 'petro' }))
      .toEqual(['World', 'Colombia', 'petro'])
  })

  it('country + story', () => {
    expect(levels({ country: 'ES', theme: 'dynamic-topic-8057', storyLabel: 'Ceuta' }))
      .toEqual(['world', 'country', 'story'])
  })

  it('country + person + story: all three dimensions, one path, containment order', () => {
    expect(levels({ country: 'CO', person: 'petro', theme: 'dynamic-topic-1', storyLabel: 'X' }))
      .toEqual(['world', 'country', 'person', 'story'])
  })

  it('the full ladder — country + person + story + signal', () => {
    const path = build({
      country: 'CO', countryName: 'Colombia',
      person: 'petro',
      theme: 'dynamic-topic-1', storyLabel: 'Bogota Protests',
      signal: { id: '77', label: 'Protesters march' },
    })
    expect(path.map((c) => c.level)).toEqual(SCOPE_ORDER)
    expect(path.map((c) => c.label)).toEqual(['World', 'Colombia', 'petro', 'Bogota Protests', 'Protesters march'])
  })

  it('a signal opened with no focus hangs straight off the world', () => {
    expect(levels({ signal: { id: '5', label: 'h' } })).toEqual(['world', 'signal'])
  })

  it('a signal under a person keeps the person between them', () => {
    expect(levels({ person: 'petro', signal: { id: '5', label: 'h' } })).toEqual(['world', 'person', 'signal'])
  })
})

describe('buildScopePath — thread and theme are one story crumb, never two', () => {
  it('thread alone', () => {
    expect(levels({ thread: 'dynamic-topic-4', storyLabel: 'A' })).toEqual(['world', 'story'])
  })

  it('thread and theme set together still yield ONE crumb (thread wins — it is the resetting door)', () => {
    const path = build({ thread: 'dynamic-topic-4', theme: 'dynamic-topic-9', storyLabel: 'A' })
    expect(path.filter((c) => c.level === 'story')).toHaveLength(1)
    expect(path[1].id).toBe('dynamic-topic-4')
  })
})

describe('buildScopePath — invariance to lens and eclipse', () => {
  // The story lens and the eclipse takeover change what the surfaces LOOK like;
  // neither is a scope. The path is derived only from focus, so an identical
  // focus must yield an identical path whatever chrome is up — this test exists
  // so nobody later "improves" the path by feeding chrome state into it.
  it('the path has no lens/eclipse input: the same focus yields the same path', () => {
    const focus = { country: 'ES', theme: 'dynamic-topic-8057', storyLabel: 'Ceuta' }
    expect(build(focus)).toEqual(build({ ...focus }))
  })

  it('a lens-anchored story is the same crumb as the same story without the lens', () => {
    const withLens = build({ thread: 'dynamic-topic-8057', storyLabel: 'Ceuta' })
    const without = build({ theme: 'dynamic-topic-8057', storyLabel: 'Ceuta' })
    expect(withLens[1].label).toBe(without[1].label)
    expect(withLens[1].typeLabel).toBe(without[1].typeLabel)
  })
})

describe('navigation semantics', () => {
  const path = build({
    country: 'CO', countryName: 'Colombia',
    person: 'petro',
    theme: 'dynamic-topic-1', storyLabel: 'Bogota Protests',
    signal: { id: '77', label: 'Protesters march' },
  })

  it('clicking World drops everything', () => {
    expect(levelsDroppedBy(path, 0)).toEqual(['country', 'person', 'story', 'signal'])
  })

  it('clicking a middle crumb drops only what is to its right', () => {
    expect(levelsDroppedBy(path, 1)).toEqual(['person', 'story', 'signal'])
    expect(levelsDroppedBy(path, 2)).toEqual(['story', 'signal'])
    expect(levelsDroppedBy(path, 3)).toEqual(['signal'])
  })

  it('clicking the crumb you are standing in drops nothing', () => {
    expect(levelsDroppedBy(path, path.length - 1)).toEqual([])
    expect(isCurrentScope(path, path.length - 1)).toBe(true)
    expect(isCurrentScope(path, 0)).toBe(false)
  })

  it('an out-of-range index is inert rather than throwing', () => {
    expect(levelsDroppedBy(path, -1)).toEqual([])
    expect(levelsDroppedBy(path, 99)).toEqual([])
  })

  it('currentScope is the deepest crumb', () => {
    expect(currentScope(path).level).toBe('signal')
    expect(currentScope(build({})).level).toBe('world')
  })
})

describe('type labels', () => {
  it('a dynamic topic is a Story; an atlas slug is a Theme', () => {
    expect(storyTypeLabel('dynamic-topic-8057')).toBe('Story')
    expect(storyTypeLabel('emergent-cluster-3')).toBe('Story')
    expect(storyTypeLabel('election-legitimacy--co')).toBe('Theme')
    expect(storyTypeLabel('KILL')).toBe('Theme')
  })

  it('opaque ids are recognised through a country suffix', () => {
    expect(isOpaqueStoryId('dynamic-topic-8057')).toBe(true)
    expect(isOpaqueStoryId('cluster-12--co')).toBe(true)
    expect(isOpaqueStoryId('election-legitimacy--co')).toBe(false)
  })
})
