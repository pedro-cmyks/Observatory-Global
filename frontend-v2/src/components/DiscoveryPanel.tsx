import { useEffect, useState } from 'react';
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
        // Fetch more than we need so we can filter for accelerating ones
        const res = await fetch(`/api/v2/narratives?hours=${hours}&limit=10`);
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

  // Prefer accelerating topics; fall back to top by signal_count if fewer than 2
  const rising = narratives.filter(n => n.trend === 'accelerating');
  const displayed = rising.length >= 2
    ? rising.slice(0, 4)
    : narratives.slice(0, 4);
  const isRisingView = rising.length >= 2;

  return (
    <div className="discovery-panel">
      <div className="discovery-intro">
        {isRisingView ? 'gaining momentum right now' : 'most active right now'}
      </div>
      <div className="discovery-list">
        {loading && Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="discovery-card discovery-card--skeleton" />
        ))}
        {error && (
          <div className="discovery-error">Could not load topics</div>
        )}
        {!loading && !error && displayed.map((n) => {
          const label = getThemeLabel(n.theme_code);
          return (
            <div
              key={n.theme_code}
              className="discovery-card"
              onClick={() => onThemeSelect(n.theme_code)}
              role="button"
              tabIndex={0}
              aria-label={label}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  onThemeSelect(n.theme_code);
                }
              }}
            >
              <div className="discovery-card__top">
                <span className="discovery-card__name">{label}</span>
                <span className="discovery-card__meta">
                  <span className="discovery-card__signals">{formatSignals(n.signal_count)}</span>
                </span>
              </div>
              <div className="discovery-card__countries">{n.top_countries.slice(0, 4).join(' · ')}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
