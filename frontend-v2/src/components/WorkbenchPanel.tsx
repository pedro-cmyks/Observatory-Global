// Workbench panel (Phase 2): the investigation memory. Sidebar of saved
// investigations + pinned route + trail + JSON export (the v1 durability
// mechanism — localStorage is evictable by design, spec amendment B3).
import { useCallback, useEffect, useState } from 'react';
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
import { classifyOutlet, coarseTierLabel, TIER_TIP } from '../lib/sourceTiers';
import { Flag } from './Flag';
import { DossierView } from './DossierView';
import WorkbenchConstellation from './WorkbenchConstellation';
import { connectionTopicIds } from '../lib/dossierConnections';
import { countQualifier } from '../lib/countQualifier';
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
                          {pin.snapshot.evidence.map((e, i) => (
                            <li key={i}>
                              {e.url ? <a href={e.url} target="_blank" rel="noopener noreferrer">{e.headline}</a> : e.headline}
                              {e.source ? <span className="wb-snap-src"> · {e.source}</span> : null}
                            </li>
                          ))}
                        </ul>
                      )}
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
                          {cit.sourceCountry && (
                            <span className="wb-cit-chip wb-cit-chip--cc">
                              <Flag code={cit.sourceCountry} title={cit.sourceCountry} className="wb-cit-flag" />
                              {cit.sourceCountry}
                            </span>
                          )}
                          {cit.source && <span className="wb-cit-chip">{cit.source}</span>}
                          {(() => {
                            const t = classifyOutlet(cit.source).tier;
                            return (
                              <span
                                className={`wb-cit-chip wb-cit-tier wb-cit-tier--${t}`}
                                data-tip={TIER_TIP[t]}
                              >{coarseTierLabel(t)}</span>
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
