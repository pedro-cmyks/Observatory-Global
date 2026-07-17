// Workbench panel (Phase 2): the investigation memory. Sidebar of saved
// investigations + pinned route + trail + JSON export (the v1 durability
// mechanism — localStorage is evictable by design, spec amendment B3).
import { useCallback, useState } from 'react';
import {
  createInvestigation,
  deleteInvestigation,
  exportInvestigationJSON,
  getActiveInvestigationId,
  getInvestigation,
  investigationQuery,
  listInvestigations,
  removePin,
  updatePinNote,
  setActiveInvestigation,
  type Investigation,
} from '../lib/workbench';
import { DossierView } from './DossierView';
import WorkbenchConstellation from './WorkbenchConstellation';
import { connectionTopicIds } from '../lib/dossierConnections';
import { countQualifier } from '../lib/countQualifier';
import './WorkbenchPanel.css';

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
  refreshToken?: number; // bump to force re-read after external pin changes
}

export default function WorkbenchPanel({
  onOpenThread, onOpenCountry, onOpenParams, onStartInvestigation, refreshToken,
}: WorkbenchPanelProps) {
  const [, setTick] = useState(0);
  const [newTitle, setNewTitle] = useState('');
  const [showDossier, setShowDossier] = useState(false);
  // Export feedback (council wish 12): the action must confirm itself.
  const [exported, setExported] = useState(false);
  // P0.6b: CORROBORATE opens the report AND fires the web-corroboration run.
  const [autoCorroborate, setAutoCorroborate] = useState(false);
  void refreshToken;

  const rerender = useCallback(() => setTick(t => t + 1), []);

  const investigations = listInvestigations();
  const activeId = getActiveInvestigationId();
  const active: Investigation | null = activeId ? getInvestigation(activeId) : null;

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
                    <button
                      className="wb-pin-remove"
                      data-tip="Unpin"
                      onClick={() => { removePin(active.id, pin.anchorId); rerender(); }}
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
    </div>
  );
}
