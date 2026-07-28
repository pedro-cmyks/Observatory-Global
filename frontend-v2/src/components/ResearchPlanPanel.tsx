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
  researchLedgerSummary,
  sendPinEvents,
  type ResearchAnchor,
  type ResearchPlan,
} from '../lib/researchPlan';
import {
  addPin,
  createInvestigation,
  getActiveInvestigationId,
  getInvestigation,
  recordTrail,
  removePin,
  updatePinSnapshot,
  type PinSnapshot,
} from '../lib/workbench';
import { toCitationGateStatus } from '../lib/workbench';
import { fetchThreadEvidence } from '../lib/pinEvidence';
import PinReceiptButton from './PinReceiptButton';
import StoryTimeTravel from './StoryTimeTravel';
import './ResearchPlanPanel.css';

// Live research lanes are hot-only; the backend clamps `hours` here too. Widen
// tops out at the live-detail limit — past it, the archive strip is the path.
const MAX_LIVE_HOURS = 720; // 30 days

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
  const [showHistory, setShowHistory] = useState(false);
  const [hoursOverride, setHoursOverride] = useState<number | null>(null);
  const [pinnedIds, setPinnedIds] = useState<Set<string>>(new Set());
  const impressionsSent = useRef<string | null>(null);

  // A widen ("30 days") is per-query — a new story resets to the caller window.
  useEffect(() => { setHoursOverride(null); }, [query]);

  const effectiveHours = Math.min(hoursOverride ?? hours, MAX_LIVE_HOURS);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);
    fetchResearchPlan(query, { hours: effectiveHours, countryCode })
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
  }, [query, effectiveHours, countryCode]);

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
    // W4 (2026-07-05): the first pin with no active investigation CREATES one
    // from the current query — the search→story ramp no longer dead-ends at
    // the capture moment.
    let invId = getActiveInvestigationId();
    if (!invId || !getInvestigation(invId)) {
      invId = createInvestigation(query).id;
      onPinsChanged?.();
    }
    if (pinnedIds.has(anchor.id)) {
      removePin(invId, anchor.id);
      emit(anchor, 'unpin', rank);
      setPinnedIds(prev => { const next = new Set(prev); next.delete(anchor.id); return next; });
    } else {
      // #227: freeze what the analyst SEES now, so the dossier doesn't re-fetch
      // drifted data later.
      const anyAnchor = anchor as unknown as Record<string, unknown>;
      const ev = (anyAnchor.evidence_samples ?? anyAnchor.snippets ?? anyAnchor.evidence) as
        | Array<{ headline?: string; title?: string; source?: string; url?: string; timestamp?: string; date?: string }>
        | undefined;
      const frozenEvidence = Array.isArray(ev)
        ? ev.slice(0, 3).map(e => {
            const ts = e.timestamp ?? e.date;
            return {
              headline: String(e.headline ?? e.title ?? ''),
              source: e.source ? String(e.source) : undefined,
              url: e.url ? String(e.url) : undefined,
              date: typeof ts === 'string' && ts.length >= 10 ? ts.slice(0, 10) : undefined,
            };
          }).filter(e => e.headline)
        : [];
      const snapshot: PinSnapshot = {
        capturedAt: new Date().toISOString(),
        summary: [anchor.label, anchor.evidence_label?.replace(/_/g, ' '),
          anchor.investigative_score != null ? `score ${anchor.investigative_score.toFixed(2)}` : null]
          .filter(Boolean).join(' · '),
        metrics: {
          ...(anchor.investigative_score != null ? { score: Number(anchor.investigative_score.toFixed(3)) } : {}),
          ...(anchor.retrieval_lane || anchor.lane ? { lane: String(anchor.retrieval_lane ?? anchor.lane) } : {}),
          ...(anchor.match_basis ? { basis: String(anchor.match_basis) } : {}),
        },
        evidence: frozenEvidence.length > 0 ? frozenEvidence : undefined,
      };
      addPin(invId, {
        anchorId: anchor.id,
        anchorType: anchor.anchor_type,
        label: anchor.label,
        evidenceLabel: anchor.evidence_label,
        retrievalLane: anchor.retrieval_lane ?? anchor.lane,
        matchBasis: anchor.match_basis,
        investigativeScore: anchor.investigative_score,
        category: anchor.category ?? undefined,
        open: anchor.open ?? null,
        planId: plan?.plan_id,
        queryText: query,
        snapshot,
      });
      // #227 hole (NATO-Ankara dossier): a story-panel anchor often carries NO
      // inline evidence — the pin froze metadata only and the dossier reported
      // "captured without frozen evidence". The anchor has a thread id, so
      // fetch its evidence now (async; the pin never waits) like the thread-row
      // path does, and merge it into the frozen snapshot.
      const threadId = anchor.open?.surface === 'thread_detail'
        ? anchor.open?.params?.thread_id : undefined;
      if (frozenEvidence.length === 0 && threadId) {
        const capturedInvId = invId;
        fetchThreadEvidence(String(threadId))
          .then(evidence => {
            if (!evidence) return;
            updatePinSnapshot(capturedInvId, anchor.id, { ...snapshot, evidence });
            onPinsChanged?.();
          })
          .catch(() => { /* metadata-only snapshot stands */ });
      }
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
      // rank in the key: degraded lanes can emit the SAME gap id twice
      // (gap-lane_degraded-general for thread + semantic) — ids alone collide.
      <div key={`${anchor.id}-${rank}`} className={`rp-anchor ${isGap ? 'rp-anchor--gap' : ''}`}>
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
          {anchor.category && (
            <span className="rp-intent-chip rp-intent-chip--axis" data-tip="Atlas category (R3 lens)">
              {anchor.category.replace(/-/g, ' ')}
            </span>
          )}
          {anchor.movement?.source === 'kalman-topic-movement' && anchor.movement.trend && (
            <span className="rp-lane" data-tip="Kalman movement trend (shared #219 field)">
              {anchor.movement.trend}
            </span>
          )}
          {!isGap && (
            <button
              className={`rp-pin ${pinnedIds.has(anchor.id) ? 'rp-pin--active' : ''}`}
              data-tip={pinnedIds.has(anchor.id)
                ? 'Unpin from investigation'
                : hasInvestigation ? 'Pin to investigation' : 'Pin — starts an investigation from this query'}
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
      {/* Scrollable body. The honesty rails (low-confidence tray + downranking
          ledger) live OUTSIDE this scroller, pinned at the panel bottom, so a
          short grid slot (laptop stream preset = 6 rows) can never clip them
          out of existence — they are always painted. */}
      <div className="rp-scroll">
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
          <div className="rp-empty">
            <div className="rp-status">
              No live anchors in the last {Math.round(effectiveHours / 24)} days.
            </div>
            <div className="rp-widen">
              {effectiveHours < MAX_LIVE_HOURS ? (
                <button
                  type="button"
                  className="rp-widen-btn"
                  onClick={() => setHoursOverride(MAX_LIVE_HOURS)}
                  data-tip="Re-run the live search over the last 30 days — Atlas's live-detail limit"
                >
                  ⤢ Widen to 30 days
                </button>
              ) : (
                <span className="rp-widen-note">
                  Widened to 30 days — the limit of live detail.
                </span>
              )}
              <span className="rp-widen-hint">
                To reach further back, travel the archive below.
              </span>
            </div>
            <StoryTimeTravel query={query} />
          </div>
        )}
      </div>

      {plan.anchors.length > 0 && (
        <div className="rp-history">
          <button className="rp-tray-toggle" onClick={() => setShowHistory(s => !s)}>
            {showHistory ? '▾' : '▸'} ARCHIVE ACTIVITY · TIME TRAVEL
          </button>
          {showHistory && <StoryTimeTravel query={query} />}
        </div>
      )}

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
                <PinReceiptButton
                  contextLabel={query}
                  citation={{
                    headline: item.headline,
                    source: item.source_name || undefined,
                    // N1: item.country_code = SUBJECT country, never an origin
                    // assertion; semantic-evidence rows carry no outlet origin.
                    gateStatus: toCitationGateStatus(item.gate_status),
                    publishedDate: item.timestamp ? item.timestamp.slice(0, 10) : undefined,
                  }}
                />
              </div>
              <div className="rp-anchor-meta">
                <span className="rp-lane">semantic {item.similarity.toFixed(2)}</span>
                <span
                  className={`rp-badge ${item.gate_status === 'verified' ? 'rp-badge--direct' : item.gate_status === 'extended' ? 'rp-badge--context' : item.gate_status === 'below_gate' ? 'rp-badge--gap' : 'rp-badge--context'}`}
                  data-tip={{
                    verified: 'Cleared the quality gate (~90% precision)',
                    extended: 'Clears the extended threshold (~75% precision) — graded coverage, below the strict gate',
                    assigned: 'Topic-assigned but below both gate tiers',
                    below_gate: 'Did not clear the quality gate — candidate material, not verified coverage',
                  }[item.gate_status ?? 'below_gate'] ?? 'Gate status unknown'}
                >
                  {(item.gate_status ?? 'unverified').toUpperCase()}
                </span>
                {item.source_name && <span className="rp-score">{item.source_name}</span>}
              </div>
            </div>
          ))}
        </div>
      )}
      </div>

      {/* Honesty rails — pinned below the scroller, never clipped by a short
          panel. The expanded tray scrolls within its own capped area. */}
      {(plan.low_confidence_tray.length > 0 || plan.downranking_ledger) && (
        <div className="rp-rails">
          {plan.low_confidence_tray.length > 0 && (
            <div className="rp-tray">
              <button className="rp-tray-toggle" onClick={() => setShowTray(s => !s)}>
                {showTray ? '▾' : '▸'} LOW-CONFIDENCE CANDIDATES — ALL ACCESSIBLE ({plan.low_confidence_tray.length})
              </button>
              {showTray && plan.low_confidence_tray.map((a, i) =>
                renderAnchor(a, plan.anchors.length + i))}
            </div>
          )}

          {plan.downranking_ledger && (
            <div className="rp-ledger" data-tip={plan.downranking_ledger.appeal_action}>
              {researchLedgerSummary(plan.downranking_ledger)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
