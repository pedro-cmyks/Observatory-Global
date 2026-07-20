// Workbench panel (Phase 2): the investigation memory. Sidebar of saved
// investigations + pinned route + trail + JSON export (the v1 durability
// mechanism — localStorage is evictable by design, spec amendment B3).
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  addCitation,
  addClaim,
  addPin,
  createInvestigation,
  deleteInvestigation,
  exportInvestigationJSON,
  getActiveInvestigationId,
  getInvestigation,
  investigationQuery,
  listInvestigations,
  mergeInvestigations,
  movePin,
  removeCitation,
  removePin,
  updateCitationNote,
  updatePinNote,
  setActiveInvestigation,
  type Citation,
  type Investigation,
  type WorkbenchPin,
} from '../lib/workbench';
import type { ClaimRelation } from '../lib/claimLedger';
import { resolveOriginChip, resolveTierChip } from '../lib/sourceProvenance';
import { Flag } from './Flag';
import { DossierView } from './DossierView';
import { AccountSection } from './AccountSection';
import WorkbenchConstellation from './WorkbenchConstellation';
import { connectionTopicIds } from '../lib/dossierConnections';
import { countQualifier } from '../lib/countQualifier';
import { extractSnapshotUrls, stateTag, useArticleStates } from '../lib/articleEnrichment';
import { fetchLeads, fetchReadings, readProvenance, type LeadsResult, type Reading } from '../lib/aiRead';
import './WorkbenchPanel.css';

// Gate-tier badge copy for pinned receipts — the same honesty labels the
// evidence rows carry, frozen alongside the receipt.
const GATE_BADGE: Record<string, { label: string; tip: string }> = {
  verified: { label: 'VERIFIED', tip: 'Cleared the quality gate (~90% precision) when pinned.' },
  extended: { label: 'EXTENDED', tip: 'Cleared the extended threshold (~75% precision) when pinned — graded coverage.' },
  below_gate: { label: 'BELOW GATE', tip: 'Did not clear the quality gate — candidate material, not verified coverage.' },
  unknown: { label: 'UNGATED', tip: 'The row carried no gate signal (dynamic/social/archive receipt).' },
};

// Notes must never clip mid-sentence (the truncation complaint): size the
// textarea to its content on mount and as the analyst types.
function autoGrowNote(el: HTMLTextAreaElement | null) {
  if (!el) return;
  el.style.height = 'auto';
  el.style.height = `${el.scrollHeight + 2}px`;
}

interface WorkbenchPanelProps {
  onOpenThread?: (threadId: string, label: string) => void;
  onOpenCountry?: (countryCode: string) => void;
  /** W1: panel pins restore their L2 view from a query-string. */
  onOpenParams?: (params: string) => void;
  onStartInvestigation?: (query: string) => void;
  /** Escape closes the workbench (council P1-11, wish 4). */
  onClose?: () => void;
  refreshToken?: number; // bump to force re-read after external pin changes
}

export default function WorkbenchPanel({
  onOpenThread, onOpenCountry, onOpenParams, onStartInvestigation, onClose, refreshToken,
}: WorkbenchPanelProps) {
  const [, setTick] = useState(0);
  const [newTitle, setNewTitle] = useState('');
  const [showDossier, setShowDossier] = useState(false);
  // Export feedback (council wish 12): the action must confirm itself.
  const [exported, setExported] = useState(false);
  // P0.6b: CORROBORATE opens the report AND fires the web-corroboration run.
  const [autoCorroborate, setAutoCorroborate] = useState(false);
  // Claim ledger (Carolina): select two receipts → mark their relation.
  const [selectedCites, setSelectedCites] = useState<string[]>([]);
  const [claimToast, setClaimToast] = useState<string | null>(null);
  // Undo toast for destructive ops (council P1-11, wish 4): every removal is
  // reversible for a few seconds so a mis-click never loses a pinned receipt.
  const [undoToast, setUndoToast] = useState<{ message: string; undo: () => void } | null>(null);
  void refreshToken;

  const rerender = useCallback(() => setTick(t => t + 1), []);

  const showUndo = useCallback((message: string, undo: () => void) => {
    setUndoToast({ message, undo });
    window.setTimeout(() => setUndoToast(cur => (cur && cur.message === message ? null : cur)), 6000);
  }, []);

  const investigations = listInvestigations();
  const activeId = getActiveInvestigationId();
  const active: Investigation | null = activeId ? getInvestigation(activeId) : null;

  // Enrichment F1: display states for every pinned evidence URL (server-side
  // fetched text — status + excerpt only; article text never lives client-side).
  const evidenceUrls = useMemo(
    () => Array.from(new Set((active?.pins ?? []).flatMap(p => extractSnapshotUrls(p.snapshot)))),
    [active],
  );
  const articleStates = useArticleStates(evidenceUrls);

  // F2 AI-read + F2.5 leads: explicit trigger (first run pays the LLM pass;
  // re-runs hit the server-side ai_readings cache). Per-investigation state.
  const [readings, setReadings] = useState<Map<string, Reading>>(new Map());
  const [leads, setLeads] = useState<LeadsResult | null>(null);
  const [aiReading, setAiReading] = useState(false);
  useEffect(() => { setReadings(new Map()); setLeads(null); }, [activeId]);
  const runAiRead = useCallback(async () => {
    if (!active || evidenceUrls.length === 0 || aiReading) return;
    setAiReading(true);
    try {
      const r = await fetchReadings(evidenceUrls);
      setReadings(r);
      const pinnedIds = active.pins.map(p => p.anchorId);
      setLeads(await fetchLeads(evidenceUrls, pinnedIds));
    } finally {
      setAiReading(false);
    }
  }, [active, evidenceUrls, aiReading]);

  // Escape closes the dossier first (if open), else the whole workbench.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return;
      if (showDossier) { setShowDossier(false); setAutoCorroborate(false); return; }
      onClose?.();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [showDossier, onClose]);

  // accounts-v1 (F4b): the sync engine adopts pulled investigations via a raw
  // localStorage write (deliberate onWorkbenchChange bypass — that bypass is
  // the sync loop guard) and announces it with this DOM event. Re-read the
  // store so a pull from another device shows up without a reopen. UI-only:
  // a re-render can never re-enter sync.
  useEffect(() => {
    const onPulled = () => rerender();
    window.addEventListener('atlas-workbench-pulled', onPulled);
    return () => window.removeEventListener('atlas-workbench-pulled', onPulled);
  }, [rerender]);

  // Destructive-op helpers with undo (capture the removed item, restore on undo).
  const removePinWithUndo = useCallback((inv: Investigation, pin: WorkbenchPin) => {
    removePin(inv.id, pin.anchorId);
    rerender();
    showUndo(`Unpinned “${pin.label}”`, () => { addPin(inv.id, pin); rerender(); });
  }, [rerender, showUndo]);

  const removeCitationWithUndo = useCallback((inv: Investigation, cit: Citation) => {
    removeCitation(inv.id, cit.id);
    rerender();
    showUndo(`Removed receipt “${cit.headline}”`, () => { addCitation(inv.id, cit); rerender(); });
  }, [rerender, showUndo]);

  // Investigations the active one can move a pin into / merge into.
  const otherInvestigations = investigations.filter(i => i.id !== activeId);

  const toggleCiteSelect = useCallback((id: string) => {
    setSelectedCites(prev => {
      if (prev.includes(id)) return prev.filter(x => x !== id);
      // Keep at most two selected — drop the oldest when a third is picked.
      return prev.length >= 2 ? [prev[1], id] : [...prev, id];
    });
  }, []);

  const markRelation = useCallback((relation: ClaimRelation) => {
    if (!activeId || selectedCites.length !== 2) return;
    addClaim(activeId, { citationIdA: selectedCites[0], citationIdB: selectedCites[1], relation });
    setSelectedCites([]);
    setClaimToast(`Marked ${relation.toLowerCase()}`);
    window.setTimeout(() => setClaimToast(null), 1800);
    rerender();
  }, [activeId, selectedCites, rerender]);

  function handleCreate() {
    const title = newTitle.trim();
    if (!title) return;
    createInvestigation(title);
    setNewTitle('');
    rerender();
    onStartInvestigation?.(title);
  }

  function handleExport() {
    if (!active) return;
    const json = exportInvestigationJSON(active.id);
    if (!json) return;
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `atlas-investigation-${active.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setExported(true);
    window.setTimeout(() => setExported(false), 1600);
  }

  function handleOpenPin(pin: Investigation['pins'][number]) {
    const params = pin.open?.params ?? {};
    if (pin.open?.surface === 'thread_detail' && params.thread_id) {
      onOpenThread?.(String(params.thread_id), pin.label);
    } else if (pin.open?.surface === 'country_brief' && params.country_code) {
      onOpenCountry?.(String(params.country_code));
    } else if (pin.open?.surface === 'l2_params' && params.urlParams) {
      // W1: unified panel pins (theme/country/person/source/attention/signal)
      onOpenParams?.(String(params.urlParams));
    }
  }

  return (
    <div className="wb-panel">
      <div className="wb-sidebar">
        <AccountSection />
        <div className="wb-new">
          <input
            className="wb-new-input"
            placeholder="New investigation…"
            value={newTitle}
            onChange={e => setNewTitle(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleCreate(); }}
          />
          <button className="wb-new-btn" onClick={handleCreate} data-tip="Start a new investigation">+</button>
        </div>
        <div className="wb-list">
          {investigations.map(inv => (
            <button
              key={inv.id}
              className={`wb-item ${inv.id === activeId ? 'wb-item--active' : ''}`}
              onClick={() => {
                setActiveInvestigation(inv.id);
                rerender();
                // Re-open its research plan from the PERSISTED query (falls
                // back to last pin queryText, then title, for old records).
                onStartInvestigation?.(investigationQuery(inv));
              }}
            >
              <span className="wb-item-title">{inv.title}</span>
              <span className="wb-item-meta">{inv.pins.length} pins</span>
            </button>
          ))}
          {investigations.length === 0 && (
            <div className="wb-empty">No investigations yet. Create one and pin anchors from a research plan.</div>
          )}
        </div>
      </div>

      <div className="wb-main">
        {!active ? (
          <div className="wb-empty">Select or create an investigation.</div>
        ) : (
          <>
            {showDossier && (
              <DossierView
                investigation={active}
                autoCorroborate={autoCorroborate}
                onMutate={rerender}
                onClose={() => { setShowDossier(false); setAutoCorroborate(false); }}
              />
            )}
            <div className="wb-header">
              <span className="wb-title">{active.title}</span>
              <div className="wb-actions">
                <button className="wb-action wb-action--report" onClick={() => { setAutoCorroborate(false); setShowDossier(true); }} data-tip="Generate a report from the pinned route (Phase 3)" disabled={active.pins.length === 0}>REPORT</button>
                <button className="wb-action wb-action--corroborate" onClick={() => { setAutoCorroborate(true); setShowDossier(true); }} data-tip="Check every evidence-bearing pin against live web coverage; metadata-only context is marked not applicable. Duration grows with the route." disabled={active.pins.length === 0}>CORROBORATE</button>
                <button className="wb-action" onClick={handleExport} data-tip="Export investigation as JSON (durability)">{exported ? 'DOWNLOADED ✓' : 'EXPORT'}</button>
                <button
                  className="wb-action wb-action--airead"
                  onClick={runAiRead}
                  disabled={evidenceUrls.length === 0 || aiReading}
                  data-tip="AI-read the fetched source texts: claims with verbatim quotes (quoteless claims are dropped), plus LEADS — actors the bodies reveal, matched against Atlas threads you haven't pinned. First run pays the model; later runs hit the cache."
                >{aiReading ? 'READING SOURCES…' : (readings.size > 0 ? 'RE-READ' : 'AI READ')}</button>
                {otherInvestigations.length > 0 && (
                  <select
                    className="wb-action wb-merge-select"
                    data-tip="Merge this investigation into another — pins, receipts and claims are unioned (duplicates collapse), trails combine."
                    value=""
                    onChange={e => {
                      const targetId = e.target.value;
                      if (!targetId) return;
                      const target = investigations.find(i => i.id === targetId);
                      if (target && window.confirm(`Merge “${active.title}” into “${target.title}”? This combines both and removes “${active.title}”.`)) {
                        mergeInvestigations(targetId, active.id);
                        rerender();
                        onStartInvestigation?.(investigationQuery(getInvestigation(targetId)!));
                      }
                      e.target.value = '';
                    }}
                  >
                    <option value="">MERGE INTO…</option>
                    {otherInvestigations.map(i => (
                      <option key={i.id} value={i.id}>{i.title}</option>
                    ))}
                  </select>
                )}
                <button
                  className="wb-action wb-action--danger"
                  data-tip="Delete this investigation"
                  onClick={() => {
                    if (window.confirm(`Delete investigation "${active.title}"? Export first if you need it.`)) {
                      deleteInvestigation(active.id);
                      rerender();
                    }
                  }}
                >DELETE</button>
              </div>
            </div>

            {/* Incremental constellation seed: the universe builds as you pin
                (absent under 2 thread pins — nothing to connect). The absence
                gets one honest sentence instead of silent nothing (council
                wish 21). */}
            <WorkbenchConstellation inv={active} />
            {connectionTopicIds(active).length < 2 && (
              <div className="wb-constellation-hint" data-tip="The constellation measures semantic proximity, shared countries and shared actors between pinned topic threads — it needs at least two to have anything to connect.">
                Pin 2+ topic threads to see their measured connections.
              </div>
            )}

            <div className="wb-section-title">PINNED ROUTE ({active.pins.length})</div>
            <div className="wb-pins">
              {active.pins.map(pin => (
                <div key={pin.anchorId} className="wb-pin">
                  <button className="wb-pin-label" onClick={() => handleOpenPin(pin)}>
                    {pin.label}
                  </button>
                  <div className="wb-pin-meta">
                    <span className="wb-pin-tag">{pin.anchorType}</span>
                    {pin.evidenceLabel && <span className="wb-pin-tag">{pin.evidenceLabel.replace(/_/g, ' ')}</span>}
                    {pin.matchBasis === 'topic_description' && (
                      <span className="wb-pin-tag wb-pin-tag--taxonomy" data-tip="Semantic taxonomy match — not found evidence">taxonomy</span>
                    )}
                    {otherInvestigations.length > 0 && (
                      <select
                        className="wb-pin-move"
                        data-tip="Move this pin to another investigation"
                        value=""
                        onChange={e => {
                          const toId = e.target.value;
                          if (toId && movePin(pin.anchorId, active.id, toId)) rerender();
                          e.target.value = '';
                        }}
                      >
                        <option value="">move…</option>
                        {otherInvestigations.map(i => (
                          <option key={i.id} value={i.id}>{i.title}</option>
                        ))}
                      </select>
                    )}
                    <button
                      className="wb-pin-remove"
                      data-tip="Unpin"
                      onClick={() => removePinWithUndo(active, pin)}
                    >×</button>
                  </div>
                  {/* #227: frozen evidence snapshot — what the analyst saw when pinning */}
                  {pin.snapshot && (
                    <div className="wb-pin-snapshot">
                      {pin.snapshot.summary && <div className="wb-snap-summary">{pin.snapshot.summary}</div>}
                      {pin.snapshot.evidence && pin.snapshot.evidence.length > 0 && (
                        <ul className="wb-snap-evidence">
                          {pin.snapshot.evidence.map((e, i) => {
                            const art = e.url ? articleStates.get(e.url) : undefined;
                            const tag = stateTag(art);
                            return (
                            <li key={i}>
                              {e.url ? <a href={e.url} target="_blank" rel="noopener noreferrer">{e.headline}</a> : e.headline}
                              {e.source ? <span className="wb-snap-src"> · {e.source}</span> : null}
                              {art?.status === 'ok' && (
                                <span className="wb-snap-ft wb-snap-ft--ok" data-tip={`Fetched at pin time${art.via === 'wayback' ? ' via Wayback Machine' : ''} — excerpt below`}>
                                  full text ✓{art.via === 'wayback' ? ' · wayback' : ''}
                                </span>
                              )}
                              {tag && <span className="wb-snap-ft">{tag}</span>}
                            </li>
                            );
                          })}
                        </ul>
                      )}
                      {/* Enrichment F1: work WITH the source text during the
                          investigation — excerpts only (full text stays server-side). */}
                      {(() => {
                        const oks = (pin.snapshot.evidence ?? [])
                          .map(e => (e.url ? articleStates.get(e.url) : undefined))
                          .filter(a => a?.status === 'ok' && a.excerpt);
                        if (oks.length === 0) return null;
                        return (
                          <details className="wb-snap-fulltext">
                            <summary>FROM THE SOURCE · {oks.length} excerpt{oks.length === 1 ? '' : 's'}</summary>
                            {oks.map((a, i) => (
                              <blockquote key={i}>
                                “{a!.excerpt}”
                                <span className="wb-snap-ft-meta"> — {a!.outlet ?? 'source'}{a!.fetched_at ? ` · fetched ${a!.fetched_at.slice(0, 10)}` : ''}{a!.via === 'wayback' ? ' · wayback' : ''}</span>
                              </blockquote>
                            ))}
                          </details>
                        );
                      })()}
                      {/* F2 AI-read: quote-backed claims per pin. Every claim
                          shows its verbatim quote — verify in one glance. */}
                      {(() => {
                        const pinReads = extractSnapshotUrls(pin.snapshot)
                          .map(u => readings.get(u))
                          .filter((r): r is Reading => !!r && r.claims.length > 0);
                        if (pinReads.length === 0) return null;
                        const claims = pinReads.flatMap(r => r.claims);
                        return (
                          <details className="wb-snap-airead" open>
                            <summary>{readProvenance(pinReads[0])} · {claims.length} claim{claims.length === 1 ? '' : 's'}</summary>
                            {claims.map((c, i) => (
                              <div key={i} className="wb-airead-claim">
                                <span className={`wb-airead-attr wb-airead-attr--${c.attribution}`}
                                  data-tip={c.attribution === 'attributed' ? `The outlet attributes this${c.attributed_to ? ` to ${c.attributed_to}` : ''} — it does not assert it itself.` : 'The outlet asserts this in its own voice.'}>
                                  {c.attribution === 'attributed' ? `per ${c.attributed_to ?? 'sources'}` : 'asserted'}
                                </span>
                                {c.text}
                                <blockquote>“{c.quote}”</blockquote>
                              </div>
                            ))}
                          </details>
                        );
                      })()}
                      {(() => {
                        // Count-qualifier contract: snapshot numbers are FROZEN —
                        // say so with the shared base explanation, not just a date.
                        const frozenDay = new Date(pin.snapshot.capturedAt).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
                        const q = countQualifier(pin.snapshot.evidence?.length ?? 0, frozenDay, 'frozen');
                        return (
                          <div className="wb-snap-frozen" data-tip={`${q.tip} The live data may have drifted since.`}>
                            frozen {frozenDay} · counts as pinned
                          </div>
                        );
                      })()}
                    </div>
                  )}
                  {/* #227: per-pin analyst note (saved on blur) */}
                  <textarea
                    className="wb-pin-note"
                    defaultValue={pin.note ?? ''}
                    placeholder="Add a note…"
                    rows={1}
                    ref={autoGrowNote}
                    onInput={e => autoGrowNote(e.currentTarget)}
                    onBlur={e => {
                      if ((e.target.value ?? '') !== (pin.note ?? '')) {
                        updatePinNote(active.id, pin.anchorId, e.target.value);
                        rerender();
                      }
                    }}
                  />
                </div>
              ))}
              {active.pins.length === 0 && (
                <div className="wb-empty">No pins yet — open a research plan and pin useful anchors.</div>
              )}
            </div>

            {/* F2.5 LEADS: actors the fetched bodies reveal, matched against
                Atlas threads not yet pinned. The body queries the substrate —
                it never writes it. Every lead shows its quote + measured basis. */}
            {leads && (leads.leads.length > 0 || leads.suppressed.length > 0) && (
              <>
                <div className="wb-section-title" data-tip={leads.basis ?? 'Actors from the fetched article bodies, matched against current Atlas threads.'}>
                  LEADS FROM THE TEXT ({leads.leads.length})
                </div>
                <div className="wb-leads">
                  {leads.leads.map((l, i) => (
                    <div key={i} className="wb-lead">
                      <div className="wb-lead-head">
                        <span className="wb-lead-entity">{l.entity}</span>
                        <span className="wb-lead-kind">{l.kind}{l.role ? ` · ${l.role}` : ''}</span>
                        <span className="wb-lead-basis" data-tip="Measured: how many current Atlas threads this actor appears in (rarest first — a one-thread actor is the investigative one).">
                          {l.thread_count} thread{l.thread_count === 1 ? '' : 's'}
                        </span>
                      </div>
                      {l.quote && <blockquote className="wb-lead-quote">“{l.quote}”</blockquote>}
                      <div className="wb-lead-threads">
                        {l.threads.map(t => (
                          <button
                            key={t.thread_id}
                            className="wb-lead-pin"
                            data-tip={`Pin “${t.label ?? t.thread_id}” — pinning fetches ITS sources too, so the galaxy grows a ring.`}
                            onClick={() => {
                              addPin(active.id, {
                                anchorId: t.thread_id,
                                anchorType: 'thread',
                                label: t.label ?? t.thread_id,
                                retrievalLane: 'body-lead',
                                open: { surface: 'thread_detail', params: { thread_id: t.thread_id } },
                              });
                              rerender();
                            }}
                          >◆ {t.label ?? t.thread_id}{t.signal_count != null ? ` · ${t.signal_count}` : ''}</button>
                        ))}
                      </div>
                    </div>
                  ))}
                  {leads.leads.length === 0 && (
                    <div className="wb-empty">No new leads — the bodies name no rare actors beyond what you pinned.</div>
                  )}
                  {leads.suppressed.length > 0 && (
                    <div className="wb-lead-suppressed" data-tip="No silent filtering: entities skipped for being the investigation's own subject or matching too many threads (a ubiquitous actor relates nothing).">
                      {leads.suppressed.length} suppressed: {leads.suppressed.slice(0, 4).map(s => `${s.name} (${s.reason.replace(/_/g, ' ')})`).join(' · ')}{leads.suppressed.length > 4 ? ' · …' : ''}
                    </div>
                  )}
                </div>
              </>
            )}

            {/* Receipt-level citations (council wish 1) — SEPARATE from thread
                pins: each is one headline pinned with frozen provenance. */}
            {active.citations.length > 0 && (
              <>
                <div className="wb-section-title" data-tip="Single receipts pinned from evidence rows — provenance frozen at pin time. Select two to mark how they relate.">CITATIONS ({active.citations.length})</div>
                {/* Mark-relation affordance (Carolina's claim ledger): pick two
                    receipts, then say how they relate → a Claim the dossier reads. */}
                {active.citations.length >= 2 && (
                  <div className="wb-claim-mark" role="group" aria-label="Mark relation between two receipts">
                    <span className="wb-claim-mark-hint">
                      {selectedCites.length < 2
                        ? `Select ${2 - selectedCites.length} more receipt${selectedCites.length === 1 ? '' : 's'} to mark a relation`
                        : 'How do these two relate?'}
                    </span>
                    <div className="wb-claim-mark-btns">
                      <button className="wb-claim-btn wb-claim-btn--corroborates" disabled={selectedCites.length !== 2}
                        data-tip="These receipts agree / support the same figure or claim."
                        onClick={() => markRelation('CORROBORATES')}>Corroborates</button>
                      <button className="wb-claim-btn wb-claim-btn--contradicts" disabled={selectedCites.length !== 2}
                        data-tip="These receipts disagree — e.g. different death tolls."
                        onClick={() => markRelation('CONTRADICTS')}>Contradicts</button>
                    </div>
                  </div>
                )}
                {claimToast && <div className="wb-claim-toast" role="status">{claimToast} ✓</div>}
                {active.claims.length > 0 && (
                  <div className="wb-claim-count" data-tip="Marked relations render as the Contested figures table in the dossier.">{active.claims.length} claim{active.claims.length === 1 ? '' : 's'} marked</div>
                )}
                <div className="wb-citations">
                  {active.citations.map(cit => {
                    const gate = GATE_BADGE[cit.gateStatus];
                    const selected = selectedCites.includes(cit.id);
                    const day = cit.publishedDate
                      ? new Date(cit.publishedDate + 'T00:00:00Z').toLocaleDateString(undefined, { month: 'short', day: 'numeric', timeZone: 'UTC' })
                      : null;
                    return (
                      <div key={cit.id} className={`wb-cit${selected ? ' wb-cit--selected' : ''}`}>
                        <div className="wb-cit-head">
                          <button
                            className={`wb-cit-select${selected ? ' wb-cit-select--on' : ''}`}
                            data-tip={selected ? 'Deselect receipt' : 'Select to mark a relation'}
                            aria-pressed={selected}
                            onClick={() => toggleCiteSelect(cit.id)}
                          >{selected ? '✓' : ''}</button>
                          {cit.url
                            ? <a className="wb-cit-headline" href={cit.url} target="_blank" rel="noopener noreferrer">{cit.headline}</a>
                            : <span className="wb-cit-headline wb-cit-headline--plain">{cit.headline}</span>}
                          <button
                            className="wb-cit-remove"
                            data-tip="Unpin receipt"
                            onClick={() => removeCitationWithUndo(active, cit)}
                          >×</button>
                        </div>
                        <div className="wb-cit-meta">
                          {/* N1: the flag chip is the OUTLET's recorded origin only.
                              Legacy pins stored the story's SUBJECT country in
                              `sourceCountry` — that field is never rendered as origin
                              (the "LOCAL IR" lie); no chip when origin is unknown. */}
                          {(() => {
                            const oc = resolveOriginChip(cit.originCountry);
                            return oc ? (
                              <span className="wb-cit-chip wb-cit-chip--cc" data-tip={oc.tip}>
                                <Flag code={oc.countryCode} title={oc.countryName} className="wb-cit-flag" />
                                {oc.countryCode}
                              </span>
                            ) : null;
                          })()}
                          {cit.source && <span className="wb-cit-chip">{cit.source}</span>}
                          {(() => {
                            const tc = resolveTierChip(cit.source, cit.originCountry);
                            return (
                              <span
                                className={`wb-cit-chip wb-cit-tier wb-cit-tier--${tc.tier}`}
                                data-tip={tc.tip}
                              >{tc.label}</span>
                            );
                          })()}
                          {cit.sourceLang && !['xx', 'un', 'und', ''].includes(cit.sourceLang.toLowerCase())
                            && <span className="wb-cit-chip wb-cit-chip--lang">{cit.sourceLang.toUpperCase()}</span>}
                          <span className={`wb-cit-chip wb-cit-gate wb-cit-gate--${cit.gateStatus}`} data-tip={gate.tip}>{gate.label}</span>
                          {day && <span className="wb-cit-chip wb-cit-chip--date">{day}</span>}
                        </div>
                        <textarea
                          className="wb-pin-note"
                          defaultValue={cit.note ?? ''}
                          placeholder="Add a note…"
                          rows={1}
                          ref={autoGrowNote}
                          onInput={e => autoGrowNote(e.currentTarget)}
                          onBlur={e => {
                            if ((e.target.value ?? '') !== (cit.note ?? '')) {
                              updateCitationNote(active.id, cit.id, e.target.value);
                              rerender();
                            }
                          }}
                        />
                      </div>
                    );
                  })}
                </div>
              </>
            )}

            <div className="wb-section-title">TRAIL</div>
            <div className="wb-trail">
              {active.trail.slice(-20).reverse().map((step, i) => (
                <div key={i} className="wb-trail-step">
                  <span className="wb-trail-action">{step.action}</span>
                  <span className="wb-trail-detail">{step.detail}</span>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
      {undoToast && (
        <div className="wb-undo-toast" role="status">
          <span className="wb-undo-msg">{undoToast.message}</span>
          <button
            className="wb-undo-btn"
            onClick={() => { undoToast.undo(); setUndoToast(null); }}
          >Undo</button>
        </div>
      )}
    </div>
  );
}
