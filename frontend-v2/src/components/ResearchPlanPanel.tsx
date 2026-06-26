// Research plan panel (Phase 2 entry surface for #213).
//
// Renders a ranked anchor menu from POST /api/v2/research/plan: openable
// anchors with evidence labels, coverage gaps shown as findings, the
// low-confidence tray (inspectable, never hidden), and suggested next steps.
// Pin actions write to the active Workbench investigation; impressions/
// opens/pins emit relevance telemetry (#218).
import { useEffect, useRef, useState } from 'react';
import {
  fetchResearchPlan,
  impressionEvents,
  sendPinEvents,
  type ResearchAnchor,
  type ResearchPlan,
} from '../lib/researchPlan';
import {
  addPin,
  getActiveInvestigationId,
  getInvestigation,
  recordTrail,
  removePin,
} from '../lib/workbench';
import './ResearchPlanPanel.css';

interface ResearchPlanPanelProps {
  query: string;
  hours: number;
  countryCode?: string | null;
  onOpenThread?: (threadId: string, label: string) => void;
  onOpenCountry?: (countryCode: string) => void;
  onBranchQuery?: (query: string) => void;
  onPinsChanged?: () => void;
}

const EVIDENCE_BADGE: Record<string, { text: string; cls: string }> = {
  direct_evidence: { text: 'DIRECT', cls: 'rp-badge--direct' },
  context: { text: 'CONTEXT', cls: 'rp-badge--context' },
  weak_support: { text: 'WEAK', cls: 'rp-badge--weak' },
  gap: { text: 'GAP', cls: 'rp-badge--gap' },
};

export default function ResearchPlanPanel({
  query, hours, countryCode, onOpenThread, onOpenCountry, onBranchQuery, onPinsChanged,
}: ResearchPlanPanelProps) {
  const [plan, setPlan] = useState<ResearchPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [showTray, setShowTray] = useState(false);
  const [pinnedIds, setPinnedIds] = useState<Set<string>>(new Set());
  const impressionsSent = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);
    fetchResearchPlan(query, { hours, countryCode })
      .then(p => {
        if (cancelled) return;
        setPlan(p);
        setLoading(false);
        const invId = getActiveInvestigationId();
        if (invId) {
          const inv = getInvestigation(invId);
          setPinnedIds(new Set(inv?.pins.map(x => x.anchorId) ?? []));
        }
        if (p.plan_id && impressionsSent.current !== p.plan_id) {
          impressionsSent.current = p.plan_id;
          sendPinEvents(p.plan_id, impressionEvents(p), {
            investigationId: invId, queryText: query,
          });
        }
      })
      .catch(() => {
        if (!cancelled) { setError(true); setLoading(false); }
      });
    return () => { cancelled = true; };
  }, [query, hours, countryCode]);

  function emit(anchor: ResearchAnchor, eventType: 'open' | 'pin' | 'unpin', rank?: number) {
    if (plan?.plan_id) {
      sendPinEvents(plan.plan_id, [{
        anchor_id: anchor.id,
        event_type: eventType,
        anchor_type: anchor.anchor_type,
        rank_shown: rank,
        visibility: anchor.visibility ?? 'primary',
        investigative_score: anchor.investigative_score,
      }], { investigationId: getActiveInvestigationId(), queryText: query });
    }
  }

  function handleOpen(anchor: ResearchAnchor, rank: number) {
    emit(anchor, 'open', rank);
    const invId = getActiveInvestigationId();
    if (invId) recordTrail(invId, 'open', anchor.label);
    const params = anchor.open?.params ?? {};
    if (anchor.open?.surface === 'thread_detail' && params.thread_id) {
      onOpenThread?.(String(params.thread_id), anchor.label);
    } else if (anchor.open?.surface === 'country_brief' && params.country_code) {
      onOpenCountry?.(String(params.country_code));
    } else if (anchor.open?.surface === 'research_plan' && params.query) {
      const invId2 = getActiveInvestigationId();
      if (invId2) recordTrail(invId2, 'branch', String(params.query));
      onBranchQuery?.(String(params.query));
    }
  }

  function handlePinToggle(anchor: ResearchAnchor, rank: number) {
    const invId = getActiveInvestigationId();
    if (!invId) return;
    if (pinnedIds.has(anchor.id)) {
      removePin(invId, anchor.id);
      emit(anchor, 'unpin', rank);
      setPinnedIds(prev => { const next = new Set(prev); next.delete(anchor.id); return next; });
    } else {
      // #227: freeze what the analyst SEES now, so the dossier doesn't re-fetch
      // drifted data later.
      const anyAnchor = anchor as unknown as Record<string, unknown>;
      const ev = (anyAnchor.evidence_samples ?? anyAnchor.snippets ?? anyAnchor.evidence) as
        | Array<{ headline?: string; title?: string; source?: string; url?: string }>
        | undefined;
      addPin(invId, {
        anchorId: anchor.id,
        anchorType: anchor.anchor_type,
        label: anchor.label,
        evidenceLabel: anchor.evidence_label,
        retrievalLane: anchor.retrieval_lane ?? anchor.lane,
        matchBasis: anchor.match_basis,
        investigativeScore: anchor.investigative_score,
        open: anchor.open ?? null,
        planId: plan?.plan_id,
        queryText: query,
        snapshot: {
          capturedAt: new Date().toISOString(),
          summary: [anchor.label, anchor.evidence_label?.replace(/_/g, ' '),
            anchor.investigative_score != null ? `score ${anchor.investigative_score.toFixed(2)}` : null]
            .filter(Boolean).join(' · '),
          metrics: {
            ...(anchor.investigative_score != null ? { score: Number(anchor.investigative_score.toFixed(3)) } : {}),
            ...(anchor.retrieval_lane || anchor.lane ? { lane: String(anchor.retrieval_lane ?? anchor.lane) } : {}),
            ...(anchor.match_basis ? { basis: String(anchor.match_basis) } : {}),
          },
          evidence: Array.isArray(ev)
            ? ev.slice(0, 3).map(e => ({
                headline: String(e.headline ?? e.title ?? ''),
                source: e.source ? String(e.source) : undefined,
                url: e.url ? String(e.url) : undefined,
              })).filter(e => e.headline)
            : undefined,
        },
      });
      emit(anchor, 'pin', rank);
      setPinnedIds(prev => new Set(prev).add(anchor.id));
    }
    onPinsChanged?.();
  }

  if (loading) return <div className="rp-panel"><div className="rp-status">BUILDING RESEARCH PLAN…</div></div>;
  if (error || !plan) return <div className="rp-panel"><div className="rp-status rp-status--error">RESEARCH PLAN UNAVAILABLE</div></div>;

  const hasInvestigation = !!getActiveInvestigationId();

  const renderAnchor = (anchor: ResearchAnchor, rank: number) => {
    const badge = EVIDENCE_BADGE[anchor.evidence_label] ?? EVIDENCE_BADGE.gap;
    const isGap = anchor.anchor_type === 'coverage_gap';
    const lane = anchor.retrieval_lane ?? anchor.lane;
    return (
      <div key={anchor.id} className={`rp-anchor ${isGap ? 'rp-anchor--gap' : ''}`}>
        <div className="rp-anchor-main">
          <span className={`rp-badge ${badge.cls}`}>{badge.text}</span>
          {isGap ? (
            <span className="rp-anchor-label">{anchor.label}</span>
          ) : (
            <button className="rp-anchor-label rp-anchor-open" onClick={() => handleOpen(anchor, rank)}>
              {anchor.label}
            </button>
          )}
        </div>
        <div className="rp-anchor-meta">
          <span className="rp-lane" data-tip={anchor.match_basis === 'topic_description'
            ? 'Semantic taxonomy match — not found evidence'
            : `Retrieval lane: ${lane}`}>
            {lane}{anchor.semantic_similarity ? ` ${anchor.semantic_similarity.toFixed(2)}` : ''}
          </span>
          {typeof anchor.investigative_score === 'number' && (
            <span className="rp-score" data-tip="Investigative usefulness score">
              {anchor.investigative_score.toFixed(2)}
            </span>
          )}
          {!isGap && hasInvestigation && (
            <button
              className={`rp-pin ${pinnedIds.has(anchor.id) ? 'rp-pin--active' : ''}`}
              data-tip={pinnedIds.has(anchor.id) ? 'Unpin from investigation' : 'Pin to investigation'}
              onClick={() => handlePinToggle(anchor, rank)}
            >
              {pinnedIds.has(anchor.id) ? 'PINNED' : 'PIN'}
            </button>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="rp-panel">
      <div className="rp-intent">
        {plan.intent.geo_scope.length > 0 && (
          <span className="rp-intent-chip">{plan.intent.geo_scope.join(' ')}</span>
        )}
        {plan.intent.topic_axes.map(axis => (
          <span key={axis} className="rp-intent-chip rp-intent-chip--axis">{axis.replace(/_/g, ' ')}</span>
        ))}
      </div>

      <div className="rp-anchors">
        {plan.anchors.map((a, i) => renderAnchor(a, i))}
        {plan.anchors.length === 0 && (
          <div className="rp-status">NO ANCHORS — try widening the window or rephrasing</div>
        )}
      </div>

      {plan.suggested_next_steps.length > 0 && (
        <div className="rp-next">
          <div className="rp-section-title">NEXT STEPS</div>
          {plan.suggested_next_steps.map((step, i) => (
            <div key={i} className="rp-next-step">{step}</div>
          ))}
        </div>
      )}

      {(plan.semantic_evidence?.length ?? 0) > 0 && (
        <div className="rp-evidence">
          <div className="rp-section-title" data-tip="Cross-language semantic matches over the full signal corpus — labeled by quality-gate status, never presented as verified coverage">
            SEMANTIC EVIDENCE ({plan.semantic_evidence!.length})
          </div>
          {plan.semantic_evidence!.map(item => (
            <div key={item.signal_id} className="rp-evidence-item">
              <div className="rp-evidence-head">
                {item.country_code && <span className="rp-evidence-cc">{item.country_code}</span>}
                <span className="rp-evidence-headline">{item.headline}</span>
              </div>
              <div className="rp-anchor-meta">
                <span className="rp-lane">semantic {item.similarity.toFixed(2)}</span>
                <span
                  className={`rp-badge ${item.gate_status === 'below_gate' ? 'rp-badge--gap' : 'rp-badge--context'}`}
                  data-tip={item.gate_status === 'below_gate'
                    ? 'Did not clear the quality gate — candidate material, not verified coverage'
                    : 'Topic-assigned signal'}
                >
                  {item.gate_status === 'below_gate' ? 'UNVERIFIED' : 'ASSIGNED'}
                </span>
                {item.source_name && <span className="rp-score">{item.source_name}</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      {plan.low_confidence_tray.length > 0 && (
        <div className="rp-tray">
          <button className="rp-tray-toggle" onClick={() => setShowTray(s => !s)}>
            {showTray ? '▾' : '▸'} LOW-CONFIDENCE TRAY ({plan.low_confidence_tray.length})
          </button>
          {showTray && plan.low_confidence_tray.map((a, i) =>
            renderAnchor(a, plan.anchors.length + i))}
        </div>
      )}

      {plan.downranking_ledger && (
        <div className="rp-ledger" data-tip={plan.downranking_ledger.appeal_action}>
          {plan.downranking_ledger.candidate_count} candidates ·{' '}
          {plan.downranking_ledger.shown_count} shown ·{' '}
          {plan.downranking_ledger.downranked_count} downranked ·{' '}
          {plan.downranking_ledger.omitted_count} omitted
        </div>
      )}
    </div>
  );
}
