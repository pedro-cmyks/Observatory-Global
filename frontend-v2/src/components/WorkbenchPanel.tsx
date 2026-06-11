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
  listInvestigations,
  removePin,
  setActiveInvestigation,
  type Investigation,
} from '../lib/workbench';
import './WorkbenchPanel.css';

interface WorkbenchPanelProps {
  onOpenThread?: (threadId: string, label: string) => void;
  onOpenCountry?: (countryCode: string) => void;
  onStartInvestigation?: (query: string) => void;
  refreshToken?: number; // bump to force re-read after external pin changes
}

export default function WorkbenchPanel({
  onOpenThread, onOpenCountry, onStartInvestigation, refreshToken,
}: WorkbenchPanelProps) {
  const [, setTick] = useState(0);
  const [newTitle, setNewTitle] = useState('');
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
  }

  function handleOpenPin(pin: Investigation['pins'][number]) {
    const params = pin.open?.params ?? {};
    if (pin.open?.surface === 'thread_detail' && params.thread_id) {
      onOpenThread?.(String(params.thread_id), pin.label);
    } else if (pin.open?.surface === 'country_brief' && params.country_code) {
      onOpenCountry?.(String(params.country_code));
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
                onStartInvestigation?.(inv.title); // re-open its research plan
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
            <div className="wb-header">
              <span className="wb-title">{active.title}</span>
              <div className="wb-actions">
                <button className="wb-action" onClick={handleExport} data-tip="Export investigation as JSON (durability)">EXPORT</button>
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
