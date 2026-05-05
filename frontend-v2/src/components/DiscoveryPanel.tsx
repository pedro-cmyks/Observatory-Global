import React, { useEffect, useState } from 'react';
import { getThemeLabel } from '../lib/themeLabels';
import './DiscoveryPanel.css';

interface Narrative {
  theme_code: string;
  label: string;
  signal_count: number;
  country_count: number;
  source_count: number;
  first_seen: string | null;
  velocity: number;
  trend: 'accelerating' | 'stable' | 'fading';
  spread_pct: number;
  avg_sentiment: number;
  top_persons: string[];
  hourly_timeline: Array<{ hour: string; count: number }>;
  top_countries: string[];
  has_public_interest?: boolean;
  trending_keywords?: string[];
  has_wiki_activity?: boolean;
  wiki_views?: number;
}

interface DiscoveryPanelProps {
  hours: number;
  onThemeSelect: (themeCode: string) => void;
}

function formatSignals(n: number): string {
  return n >= 1000 ? `${Math.round(n / 1000)}K signals` : `${n} signals`;
}

function trendArrow(trend: 'accelerating' | 'stable' | 'fading'): { char: string; color: string } {
  if (trend === 'accelerating') return { char: '↑', color: '#4ade80' };
  if (trend === 'fading') return { char: '↓', color: '#f87171' };
  return { char: '→', color: '#94a3b8' };
}

export default function DiscoveryPanel({ hours, onThemeSelect }: DiscoveryPanelProps) {
  const [narratives, setNarratives] = useState<Narrative[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function fetch_data() {
      setLoading(true);
      setError(false);
      try {
        const res = await fetch(`/api/v2/narratives?hours=${hours}&limit=5`);
        if (!res.ok) throw new Error('fetch failed');
        const data = await res.json();
        if (!cancelled) {
          setNarratives(data.narratives || []);
          setLoading(false);
        }
      } catch {
        if (!cancelled) {
          setError(true);
          setLoading(false);
        }
      }
    }

    fetch_data();
    const interval = setInterval(fetch_data, 300_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [hours]);

  return (
    <div className="discovery-panel">
      <div className="panel-header">
        <span className="panel-title">WHAT'S HAPPENING</span>
        <span className="panel-subtitle">top topics right now — click to explore</span>
      </div>
      <div className="discovery-list">
        {loading && Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="discovery-card discovery-card--skeleton" />
        ))}
        {error && (
          <div className="discovery-error">Could not load topics</div>
        )}
        {!loading && !error && narratives.map((n) => {
          const arrow = trendArrow(n.trend);
          return (
            <div
              key={n.theme_code}
              className="discovery-card"
              onClick={() => onThemeSelect(n.theme_code)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && onThemeSelect(n.theme_code)}
            >
              <div className="discovery-card__top">
                <span className="discovery-card__name">{getThemeLabel(n.theme_code)}</span>
                <span className="discovery-card__meta">
                  <span className="discovery-card__trend" style={{ color: arrow.color }}>{arrow.char}</span>
                  <span className="discovery-card__signals">{formatSignals(n.signal_count)}</span>
                </span>
              </div>
              <div className="discovery-card__countries">{n.top_countries.slice(0, 3).join(' · ')}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
