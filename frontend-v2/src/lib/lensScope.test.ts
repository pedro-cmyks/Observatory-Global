import { describe, it, expect } from 'vitest'
import {
  FIELD_SCOPE,
  pushScope,
  popScope,
  resetScope,
  scopeTitle,
  scopeKey,
  trailsEqual,
  consoleLensScope,
  consoleSlot,
  type ConsoleFocus,
} from './lensScope'

const thread = { kind: 'thread' as const, id: 'dynamic-topic-8057', label: 'Hamas Disarmament Deal' }
const country = { kind: 'country' as const, id: 'IL', label: 'Israel' }

describe('pushScope', () => {
  it('starts from the field', () => {
    expect(pushScope([], thread)).toEqual([FIELD_SCOPE, thread])
  })
  it('appends onto an existing trail', () => {
    expect(pushScope([FIELD_SCOPE, thread], country)).toEqual([FIELD_SCOPE, thread, country])
  })
  it('does not stack the same scope twice in a row', () => {
    expect(pushScope([FIELD_SCOPE, thread], thread)).toEqual([FIELD_SCOPE, thread])
  })
  it('rewinds instead of looping when you revisit an earlier scope', () => {
    expect(pushScope([FIELD_SCOPE, thread, country], thread)).toEqual([FIELD_SCOPE, thread])
  })
  it('refreshes the label when the same scope arrives better named', () => {
    // A deep-link cold open pushes the opaque id first; ThemeDetail resolves
    // the real label seconds later. Same key, better label — the breadcrumb
    // must not keep showing `dynamic-topic-8057` forever.
    const opaque = { kind: 'thread' as const, id: 'dynamic-topic-8057', label: 'dynamic-topic-8057' }
    expect(pushScope([FIELD_SCOPE, opaque], thread)).toEqual([FIELD_SCOPE, thread])
  })
})

describe('popScope', () => {
  it('walks back one step', () => {
    expect(popScope([FIELD_SCOPE, thread, country])).toEqual([FIELD_SCOPE, thread])
  })
  it('never pops past the field', () => {
    expect(popScope([FIELD_SCOPE])).toEqual([FIELD_SCOPE])
    expect(popScope([])).toEqual([FIELD_SCOPE])
  })
})

describe('resetScope', () => {
  it('empties any trail back to the field', () => {
    expect(resetScope([FIELD_SCOPE, thread, country])).toEqual([FIELD_SCOPE])
    expect(resetScope([FIELD_SCOPE, thread])).toEqual([FIELD_SCOPE])
    expect(resetScope([])).toEqual([FIELD_SCOPE])
  })
  it('returns the same array when already at the bare field', () => {
    // The context guards identity on this so a no-op reset does not churn
    // every Lens consumer.
    const at = [FIELD_SCOPE]
    expect(resetScope(at)).toBe(at)
  })
  it('leaves the pivoted-to scope one honest step from the field', () => {
    // The whole point. A `where it lives` country row CLOSES the thread it was
    // measured from, so Back has nothing to peel the country back to except
    // the field. Reset-then-push says so; a plain append onto [field, thread]
    // would name the thread in the breadcrumb and still land on the field.
    const pivoted = pushScope(resetScope([FIELD_SCOPE, thread]), country)
    expect(pivoted).toEqual([FIELD_SCOPE, country])
    expect(pivoted[pivoted.length - 2]).toEqual(FIELD_SCOPE)
    expect(popScope(pivoted)).toEqual([FIELD_SCOPE])
  })
})

describe('scopeTitle', () => {
  it('names the field honestly', () => {
    expect(scopeTitle(FIELD_SCOPE)).toBe('The world')
  })
  it('uses the label for a focused thing', () => {
    expect(scopeTitle(thread)).toBe('Hamas Disarmament Deal')
    expect(scopeTitle(country)).toBe('Israel')
  })
})

describe('scopeKey', () => {
  it('is stable and unique per scope', () => {
    expect(scopeKey(thread)).toBe('thread:dynamic-topic-8057')
    expect(scopeKey(FIELD_SCOPE)).toBe('field:*')
  })
  it('separates two scopes that share an id but not a kind', () => {
    expect(scopeKey({ kind: 'country', id: 'IL', label: 'Israel' }))
      .not.toBe(scopeKey({ kind: 'person', id: 'IL', label: 'IL' }))
  })
})

describe('trailsEqual', () => {
  // The trail is re-derived on every App render, so a value-equal trail MUST
  // compare equal or the context churns a new array forever.
  it('is true for a value-equal trail built from fresh objects', () => {
    const a = [FIELD_SCOPE, { ...thread }]
    const b = [FIELD_SCOPE, { ...thread }]
    expect(trailsEqual(a, b)).toBe(true)
  })
  it('is false when the label changed under the same key', () => {
    const a = [FIELD_SCOPE, thread]
    const b = [FIELD_SCOPE, { ...thread, label: 'dynamic-topic-8057' }]
    expect(trailsEqual(a, b)).toBe(false)
  })
  it('is false at different depths', () => {
    expect(trailsEqual([FIELD_SCOPE], [FIELD_SCOPE, thread])).toBe(false)
  })
})

const BLANK: ConsoleFocus = {
  storyQuery: null,
  threadId: null,
  threadLabel: null,
  themeId: null,
  themeLabel: null,
  personName: null,
  countryCode: null,
  countryName: null,
  attentionTitle: null,
  chokepointId: null,
  chokepointName: null,
}

describe('consoleLensScope', () => {
  it('is the field when nothing is focused', () => {
    expect(consoleLensScope(BLANK)).toEqual(FIELD_SCOPE)
  })
  it('reads an open theme as a thread scope', () => {
    expect(consoleLensScope({ ...BLANK, themeId: 'dynamic-topic-8057', themeLabel: 'Hamas Disarmament Deal' }))
      .toEqual(thread)
  })
  it('reads a country', () => {
    expect(consoleLensScope({ ...BLANK, countryCode: 'IL', countryName: 'Israel' })).toEqual(country)
  })
  it('reads a person', () => {
    expect(consoleLensScope({ ...BLANK, personName: 'netanyahu' }))
      .toEqual({ kind: 'person', id: 'netanyahu', label: 'netanyahu' })
  })
  // The precedence below is not a preference — it MIRRORS the stream slot's
  // own ladder in App.tsx. If the scope disagreed with the panel, the Lens
  // would name one thing and render another.
  it('lets an open theme outrank a standing country focus', () => {
    expect(consoleLensScope({
      ...BLANK,
      themeId: 'dynamic-topic-8057', themeLabel: 'Hamas Disarmament Deal',
      countryCode: 'IL', countryName: 'Israel',
    })).toEqual(thread)
  })
  it('lets a story query outrank everything', () => {
    expect(consoleLensScope({
      ...BLANK, storyQuery: 'water crisis iran', themeId: 'dynamic-topic-8057', personName: 'trump',
    })).toEqual({ kind: 'story', id: 'water crisis iran', label: 'water crisis iran' })
  })
  it('lets a person outrank a country', () => {
    expect(consoleLensScope({ ...BLANK, personName: 'trump', countryCode: 'IL', countryName: 'Israel' }))
      .toEqual({ kind: 'person', id: 'trump', label: 'trump' })
  })
  it('falls back to the id when a label has not resolved yet', () => {
    expect(consoleLensScope({ ...BLANK, themeId: 'dynamic-topic-8057', themeLabel: null }))
      .toEqual({ kind: 'thread', id: 'dynamic-topic-8057', label: 'dynamic-topic-8057' })
  })
})

/**
 * consoleSlot is THE ladder — App's stream slot picks its panel from it and
 * consoleLensScope picks its name from it. These pin every ordering, not only
 * the obvious ones: a case left untested is a case either caller can silently
 * flip.
 */
describe('consoleSlot precedence', () => {
  const S = (f: Partial<ConsoleFocus>) => consoleSlot({ ...BLANK, ...f }, false)

  it('is blank when nothing is focused', () => {
    expect(S({})).toBe('blank')
  })
  it('collapses to blank on the Live tab whatever is focused', () => {
    expect(consoleSlot({ ...BLANK, themeId: 't', storyQuery: 'q', personName: 'p' }, true)).toBe('blank')
  })
  it('a story outranks everything', () => {
    expect(S({ storyQuery: 'q', themeId: 't', threadId: 'th', personName: 'p', countryCode: 'IL', attentionTitle: 'a', chokepointId: 'c' })).toBe('story')
  })
  // The compound-focus rule (App.tsx: "show the thread"). A standing person
  // focus stays a scope chip; it must NOT take the panel from an open read.
  it('an open theme outranks a standing person focus', () => {
    expect(S({ themeId: 't', personName: 'trump' })).toBe('theme')
  })
  it('an open thread outranks a standing person focus', () => {
    expect(S({ threadId: 'th', personName: 'trump' })).toBe('thread')
  })
  it('a person takes the panel only when no thread or theme is open', () => {
    expect(S({ personName: 'trump' })).toBe('person')
    expect(S({ personName: 'trump', countryCode: 'IL' })).toBe('person')
  })
  // THE divergence: the guards let attention and thread both be true, and the
  // pick order — not the guards — settles it. This is the single reason the
  // ladder has to carry two orders at all.
  it('an attention item outranks an open thread', () => {
    expect(S({ attentionTitle: 'a', threadId: 'th' })).toBe('attention')
  })
  it('but a theme outranks an attention item', () => {
    expect(S({ attentionTitle: 'a', themeId: 't' })).toBe('theme')
  })
  it('a country outranks an attention item', () => {
    expect(S({ attentionTitle: 'a', countryCode: 'IL' })).toBe('country')
  })
  it('a thread outranks a theme', () => {
    expect(S({ threadId: 'th', themeId: 't' })).toBe('thread')
  })
  it('a thread outranks a country', () => {
    expect(S({ threadId: 'th', countryCode: 'IL' })).toBe('thread')
  })
  it('a chokepoint loses to every other focus and wins only alone', () => {
    expect(S({ chokepointId: 'hormuz' })).toBe('chokepoint')
    for (const other of [
      { personName: 'p' }, { countryCode: 'IL' }, { themeId: 't' },
      { attentionTitle: 'a' }, { storyQuery: 'q' },
    ]) {
      expect(S({ chokepointId: 'hormuz', ...other })).not.toBe('chokepoint')
    }
  })
  it('a thread still outranks a chokepoint', () => {
    expect(S({ chokepointId: 'hormuz', threadId: 'th' })).toBe('thread')
  })
})
