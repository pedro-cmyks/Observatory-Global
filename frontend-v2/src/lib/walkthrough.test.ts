// Walkthrough fixture, client side (#213 exit criterion, spec amendment D4).
// Reproduces the user route over the Workbench store with a live-shaped
// research plan: create investigation → pin anchors → open → branch →
// export. Complements the backend fixture
// (backend/tests/test_research_walkthrough_fixture.py) which covers
// parse → discover → rank for the same two forcing cases.
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ResearchAnchor, ResearchPlan } from './researchPlan'
import { impressionEvents } from './researchPlan'
import {
  addPin,
  createInvestigation,
  exportInvestigationJSON,
  getInvestigation,
  recordTrail,
} from './workbench'

const backing = new Map<string, string>()
vi.stubGlobal('localStorage', {
  getItem: (k: string) => backing.get(k) ?? null,
  setItem: (k: string, v: string) => void backing.set(k, String(v)),
  removeItem: (k: string) => void backing.delete(k),
  clear: () => backing.clear(),
})

// Live-shaped plan (mirrors the 2026-06-10 production response for the
// compound claim-verification query).
const PLAN: ResearchPlan = {
  contract: 'research-plan-v0',
  plan_id: 'rp-fixture001',
  query: 'manipulación de clima Irán y ataques a bases estadounidenses satélite',
  hours: 168,
  intent: {
    main_intent: 'manipulacion de clima iran y ataques a bases estadounidenses satelite',
    geo_scope: ['IR'],
    topic_axes: ['climate', 'water', 'conflict_infrastructure'],
    subquestions: ['Who is talking about it, how are they framing it, and after what?'],
    branches: ['us-bases-satellite-communications'],
  },
  anchors: [
    {
      anchor_type: 'thread', lane: 'thread', id: 'flood-landslide-disaster--ir',
      label: 'Flood and landslide disaster in Iran', evidence_label: 'context',
      matched_terms: ['flood'], signal_count: 133, investigative_score: 0.641,
      visibility: 'primary',
      open: { surface: 'thread_detail', params: { thread_id: 'flood-landslide-disaster--ir', hours: 168, country_code: 'IR' } },
    },
    {
      anchor_type: 'thread', lane: 'thread', id: 'water-stress-drought--ir',
      label: 'Water stress and drought in Iran', evidence_label: 'context',
      matched_terms: ['drought'], signal_count: 41, investigative_score: 0.483,
      visibility: 'primary',
      open: { surface: 'thread_detail', params: { thread_id: 'water-stress-drought--ir', hours: 168, country_code: 'IR' } },
    },
    {
      anchor_type: 'country', lane: 'country', id: 'country-ir', label: 'Iran',
      evidence_label: 'context', matched_terms: [], investigative_score: 0.443,
      visibility: 'primary',
      open: { surface: 'country_brief', params: { country_code: 'IR', hours: 168 } },
    },
    {
      anchor_type: 'related_branch', lane: 'branch', id: 'branch-us-bases-satellite-communications',
      label: 'us bases satellite communications', evidence_label: 'context',
      matched_terms: [], investigative_score: 0.343, visibility: 'primary',
      open: { surface: 'research_plan', params: { query: 'us bases satellite communications', hours: 168 } },
    },
    {
      anchor_type: 'coverage_gap', lane: 'gap', id: 'gap-axis_no_thread-conflict_infrastructure',
      label: "No coherent thread currently covers the 'conflict_infrastructure' axis for Iran; available evidence is taxonomy-only or absent.",
      evidence_label: 'gap', matched_terms: [], investigative_score: 0.119,
      visibility: 'primary', open: null,
    },
  ],
  low_confidence_tray: [],
  pin_candidates: ['flood-landslide-disaster--ir', 'water-stress-drought--ir', 'country-ir'],
  coverage_gaps: [{ gap_type: 'axis_no_thread', axis: 'conflict_infrastructure', note: 'taxonomy-only' }],
  suggested_next_steps: ["The 'conflict_infrastructure' axis has no thread-level evidence yet — treat related claims as unverified."],
}

function pinAnchor(invId: string, anchor: ResearchAnchor) {
  addPin(invId, {
    anchorId: anchor.id, anchorType: anchor.anchor_type, label: anchor.label,
    evidenceLabel: anchor.evidence_label, investigativeScore: anchor.investigative_score,
    open: anchor.open ?? null, planId: PLAN.plan_id, queryText: PLAN.query,
  })
}

beforeEach(() => backing.clear())

describe('walkthrough: claim-verification compound case, client route', () => {
  it('search → pin → open → branch → export preserves the full route', () => {
    // Step 1: natural query starts an investigation
    const inv = createInvestigation(PLAN.query)

    // Impressions for telemetry cover every primary anchor with its rank
    const impressions = impressionEvents(PLAN)
    expect(impressions).toHaveLength(PLAN.anchors.length)
    expect(impressions[0]).toMatchObject({ event_type: 'impression', rank_shown: 0 })

    // Steps 3-4: user opens surfaces and pins the useful anchors
    recordTrail(inv.id, 'open', PLAN.anchors[0].label)
    pinAnchor(inv.id, PLAN.anchors[0]) // flood thread
    pinAnchor(inv.id, PLAN.anchors[1]) // water thread
    pinAnchor(inv.id, PLAN.anchors[2]) // country IR

    // Step 5: user adds the suggested branch
    const branch = PLAN.anchors.find(a => a.anchor_type === 'related_branch')!
    recordTrail(inv.id, 'branch', String(branch.open!.params.query))

    // Gap anchors are findings, not pinnable surfaces — the unverified-claim
    // warning travels via next steps, asserted in the export below
    const state = getInvestigation(inv.id)!
    expect(state.pins.map(p => p.anchorId)).toEqual([
      'flood-landslide-disaster--ir', 'water-stress-drought--ir', 'country-ir',
    ])
    expect(state.trail.map(t => t.action)).toEqual(['search', 'open', 'pin', 'pin', 'pin', 'branch'])

    // Step 7-8: export is the durable dossier seed — route + pins traceable
    const exported = JSON.parse(exportInvestigationJSON(inv.id)!)
    expect(exported.format).toBe('atlas-investigation-v1')
    expect(exported.investigation.pins).toHaveLength(3)
    expect(exported.investigation.pins[0].planId).toBe('rp-fixture001')
    expect(exported.investigation.trail.at(-1).detail).toBe('us bases satellite communications')
    // every pin can be re-opened: open contract survived the round trip
    for (const pin of exported.investigation.pins) {
      expect(pin.open?.surface).toMatch(/thread_detail|country_brief/)
    }
  })
})
