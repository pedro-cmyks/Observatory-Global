// Time-as-dimension for the STORY panel (#236, 2026-07-06).
//
// A research-plan query is HOT-ONLY (~7d). When it returns 0 anchors ("Maduro"
// today) the topic still has a real past in the processed archive. This strip
// plots the query's activity across the archive window (~61 days), marks where
// it SPIKED, and lets the user click a day to see what was covered then.
//
// HONESTY: the archive is the only thing reachable past retention. The horizon
// label bounds the claim to real days (May 4 – last-compacted); older is not
// queryable and the UI never implies otherwise. Day receipts are archive
// SAMPLES (≤N distinct-source per cluster), never passed off as live coverage.
import { useEffect, useMemo, useRef, useState } from 'react';
import { fetchStoryHistory, type StoryHistory } from '../lib/researchPlan';

interface Props {
  query: string;
}

// Continuous ISO-day axis min..max inclusive — so gaps between matched days
// render as flat baseline, making a spike read as a spike.
function dayAxis(minDay: string, maxDay: string): string[] {
  const out: string[] = [];
  const start = new Date(minDay + 'T00:00:00Z');
  const end = new Date(maxDay + 'T00:00:00Z');
  if (isNaN(start.getTime()) || isNaN(end.getTime())) return out;
  for (let d = new Date(start); d <= end; d.setUTCDate(d.getUTCDate() + 1)) {
    out.push(d.toISOString().slice(0, 10));
  }
  return out;
}

function fmtDay(iso: string): string {
  const d = new Date(iso + 'T00:00:00Z');
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', timeZone: 'UTC' });
}

export default function StoryTimeTravel({ query }: Props) {
  const [hist, setHist] = useState<StoryHistory | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [dayData, setDayData] = useState<StoryHistory | null>(null);
  const [dayLoading, setDayLoading] = useState(false);
  const reqRef = useRef(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setHist(null);
    setSelectedDay(null);
    setDayData(null);
    fetchStoryHistory(query)
      .then(h => { if (!cancelled) { setHist(h); setLoading(false); } })
      .catch(() => { if (!cancelled) { setHist(null); setLoading(false); } });
    return () => { cancelled = true; };
  }, [query]);

  const counts = useMemo(() => {
    const m = new Map<string, { units: number; signals: number; peak: number }>();
    for (const s of hist?.series ?? []) {
      m.set(s.day, { units: s.units, signals: s.signals, peak: s.peak_sim ?? 0 });
    }
    return m;
  }, [hist]);

  const axis = useMemo(() => {
    if (!hist?.horizon) return [] as string[];
    return dayAxis(hist.horizon.min_day, hist.horizon.max_day);
  }, [hist]);

  // Bars height on match STRENGTH above the floor, self-scaled to this query's
  // own peak — so a flat ~floor background collapses and real spikes stand out
  // (raw unit counts track total archive volume, not topic presence).
  const tau = hist?.match_tau ?? 0.32;
  const maxPeak = useMemo(() => {
    let mx = 0;
    for (const v of counts.values()) mx = Math.max(mx, v.peak);
    return mx;
  }, [counts]);
  const barHeight = (peak: number): number => {
    const span = maxPeak - tau;
    if (span <= 0) return peak > 0 ? 100 : 0;
    return Math.round(Math.max(0, (peak - tau) / span) * 100);
  };

  function pickDay(day: string) {
    if (!counts.has(day)) return;
    setSelectedDay(day);
    setDayData(null);
    setDayLoading(true);
    const req = ++reqRef.current;
    fetchStoryHistory(query, { day })
      .then(d => { if (req === reqRef.current) { setDayData(d); setDayLoading(false); } })
      .catch(() => { if (req === reqRef.current) { setDayLoading(false); } });
  }

  if (loading) {
    return <div className="rp-status">READING THE ARCHIVE…</div>;
  }
  if (!hist || !hist.available) {
    return (
      <div className="sh-note">
        Deep history unavailable{hist?.reason ? ` — ${hist.reason}` : ''}.
      </div>
    );
  }

  const matchedDays = counts.size;
  const horizon = hist.horizon;

  return (
    <div className="sh-wrap">
      <div className="sh-head">
        <span className="section-label rp-section-title">ARCHIVE ACTIVITY</span>
        {horizon && (
          <span className="sh-horizon" data-tip="The processed archive is the only window reachable past ~7 days of live detail. Older is not queryable.">
            {fmtDay(horizon.min_day)} – {fmtDay(horizon.max_day)} · {horizon.days}d
          </span>
        )}
      </div>

      {matchedDays === 0 ? (
        <div className="sh-note">
          No archive activity found for this topic in the last {horizon?.days ?? '~60'} days.
          It may be older than the archive reaches, or phrased differently there.
        </div>
      ) : (
        <>
          <div className="sh-chart" role="list" aria-label="Archive activity by day">
            {axis.map(day => {
              const c = counts.get(day);
              const active = counts.has(day);
              const h = c ? barHeight(c.peak) : 0;
              const isPeak = active && maxPeak > tau && c!.peak === maxPeak;
              return (
                <button
                  key={day}
                  type="button"
                  role="listitem"
                  className={`sh-bar${active ? ' sh-bar--active' : ''}${isPeak ? ' sh-bar--peak' : ''}${selectedDay === day ? ' sh-bar--sel' : ''}`}
                  style={{ height: `${Math.max(h, active ? 10 : 3)}%` }}
                  disabled={!active}
                  data-tip={active
                    ? `${fmtDay(day)} · ${c!.units} cluster${c!.units === 1 ? '' : 's'} · ${c!.signals} signals · match ${c!.peak.toFixed(2)}`
                    : fmtDay(day)}
                  onClick={() => pickDay(day)}
                />
              );
            })}
          </div>
          <div className="sh-legend">
            {matchedDays} active day{matchedDays === 1 ? '' : 's'} · peak marked · click a bar to see that day
          </div>
        </>
      )}

      {selectedDay && (
        <div className="sh-day">
          <div className="sh-day-head">
            <span className="section-label rp-section-title">{fmtDay(selectedDay)} · FROM THE ARCHIVE</span>
            <button type="button" className="sh-day-close" onClick={() => { setSelectedDay(null); setDayData(null); }} aria-label="Close day">✕</button>
          </div>
          {dayLoading && <div className="rp-status">LOADING RECEIPTS…</div>}
          {!dayLoading && dayData && (dayData.day?.items?.length ?? 0) === 0 && (
            <div className="sh-note">{dayData.day?.empty_reason ?? 'No receipts for this day.'}</div>
          )}
          {!dayLoading && dayData?.day?.items?.map((it, i) => (
            <div key={i} className="sh-cluster">
              <div className="sh-cluster-head">
                <span className="sh-cluster-label">{it.cluster_label}</span>
                <span className="rp-lane" data-tip="Archive sample — a distinct-source snapshot, not exhaustive coverage">
                  archive {it.sim.toFixed(2)}{it.top_cc.length ? ` · ${it.top_cc.slice(0, 3).join(' ')}` : ''}
                </span>
              </div>
              {it.headlines.slice(0, 5).map((h, j) => (
                <div key={j} className="sh-headline">{h}</div>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
