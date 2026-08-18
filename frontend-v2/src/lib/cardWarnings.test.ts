import { describe, expect, it } from 'vitest'
import {
  buildCardWarningIndex,
  GRAB_BAG_GAP_PREFIX,
  isMixedGeography,
  normalizeWarningLabel,
  sealedCourtTrust,
  SPINE_GRAB_BAG_REASON,
} from './cardWarnings'

describe('normalizeWarningLabel', () => {
  it('collapses whitespace and case, trims', () => {
    expect(normalizeWarningLabel('  Wildfires in  France and Spain \n')).toBe(
      'wildfires in france and spain',
    )
  })
  it('null/undefined → empty string', () => {
    expect(normalizeWarningLabel(null)).toBe('')
    expect(normalizeWarningLabel(undefined)).toBe('')
  })
})

describe('buildCardWarningIndex', () => {
  it('reads grab-bag labels out of package.gaps, ignoring other reason codes', () => {
    const index = buildCardWarningIndex({
      packageGaps: [
        'no_dated_receipts',
        `${GRAB_BAG_GAP_PREFIX}Wildfires in France and Spain`,
        'inferred_relations_require_method_caveats',
      ],
    })
    expect(index.grabBagLabels.has('wildfires in france and spain')).toBe(true)
    expect(index.grabBagLabels.size).toBe(1)
    expect(index.grabBagThreadIds.size).toBe(0)
  })

  it('an empty label after the prefix is not indexed', () => {
    const index = buildCardWarningIndex({ packageGaps: [`${GRAB_BAG_GAP_PREFIX}  `] })
    expect(index.grabBagLabels.size).toBe(0)
  })

  it('indexes spine-demoted story nodes by thread id AND label', () => {
    const index = buildCardWarningIndex({
      storyNodes: [
        { threadId: 'dynamic-topic-9', label: 'Ceuta Migrant Crisis', spineLayoutReason: SPINE_GRAB_BAG_REASON },
        { threadId: 'dynamic-topic-2', label: 'Clean Story', spineLayoutReason: 'spine_supporting' },
      ],
    })
    expect(index.grabBagThreadIds.has('dynamic-topic-9')).toBe(true)
    expect(index.grabBagThreadIds.has('dynamic-topic-2')).toBe(false)
    expect(index.grabBagLabels.has('ceuta migrant crisis')).toBe(true)
    expect(index.grabBagLabels.has('clean story')).toBe(false)
  })

  it('null/absent inputs build an empty index', () => {
    const index = buildCardWarningIndex({ packageGaps: null, storyNodes: null })
    expect(index.grabBagThreadIds.size).toBe(0)
    expect(index.grabBagLabels.size).toBe(0)
  })
})

describe('isMixedGeography', () => {
  const index = buildCardWarningIndex({
    packageGaps: [`${GRAB_BAG_GAP_PREFIX}Wildfires in France and Spain`],
    storyNodes: [
      { threadId: 'dynamic-topic-9', label: 'Ceuta Migrant Crisis', spineLayoutReason: SPINE_GRAB_BAG_REASON },
    ],
  })

  it('matches by thread id', () => {
    expect(isMixedGeography({ thread_id: 'dynamic-topic-9', label: 'Renamed Row' }, index)).toBe(true)
  })

  it('matches by exact normalized label', () => {
    expect(isMixedGeography(
      { thread_id: 'dynamic-topic-77', label: 'Wildfires in  FRANCE and Spain' },
      index,
    )).toBe(true)
  })

  it('an unmarked row stays unmarked', () => {
    expect(isMixedGeography({ thread_id: 'dynamic-topic-1', label: 'Other Story' }, index)).toBe(false)
  })

  it('an empty label never matches', () => {
    expect(isMixedGeography({ thread_id: undefined, label: '' }, index)).toBe(false)
  })
})

describe('sealedCourtTrust', () => {
  const live = [
    {
      thread_id: 'dynamic-topic-5',
      label: 'Ceuta Migrant Crisis',
      label_status: 'failed',
      label_proposed: 'Earthquake casualties in Colombia',
      avg_confidence: 0.41,
      confidence_measured: true,
      court_withheld: false,
    },
    {
      thread_id: 'dynamic-topic-6',
      label: 'Trade Major Drone Strikes',
      label_status: 'entailed',
    },
  ]

  it('carries the verdict when thread id AND label both match', () => {
    const trust = sealedCourtTrust({ thread_id: 'dynamic-topic-5', label: 'Ceuta  Migrant crisis' }, live)
    expect(trust).toEqual({
      label_status: 'failed',
      label_proposed: 'Earthquake casualties in Colombia',
      avg_confidence: 0.41,
      confidence_measured: true,
      court_withheld: false,
    })
  })

  it('same thread id but a different label → nothing (the verdict is about another sentence)', () => {
    // The Marcus case: sealed lead "Russian Attacks on Kyiv", live label
    // "Trade Major Drone Strikes" — the live verdict must NOT transfer.
    expect(sealedCourtTrust({ thread_id: 'dynamic-topic-6', label: 'Russian Attacks on Kyiv' }, live)).toBeNull()
  })

  it('same label on a different thread id → nothing', () => {
    expect(sealedCourtTrust({ thread_id: 'dynamic-topic-99', label: 'Ceuta Migrant Crisis' }, live)).toBeNull()
  })

  it('missing identity on the sealed row → nothing', () => {
    expect(sealedCourtTrust({ thread_id: null, label: 'Ceuta Migrant Crisis' }, live)).toBeNull()
    expect(sealedCourtTrust({ thread_id: 'dynamic-topic-5', label: '' }, live)).toBeNull()
  })

  it('defaults are normalized (no measured confidence claimed when absent)', () => {
    const trust = sealedCourtTrust({ thread_id: 'dynamic-topic-6', label: 'Trade Major Drone Strikes' }, live)
    expect(trust).toEqual({
      label_status: 'entailed',
      label_proposed: null,
      avg_confidence: null,
      confidence_measured: false,
      court_withheld: false,
    })
  })
})
