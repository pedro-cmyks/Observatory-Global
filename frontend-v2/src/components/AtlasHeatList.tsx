import { useEffect, useMemo, useState } from 'react';
import { resolveCountryName } from '../lib/countryNames';
import './AtlasHeatList.css';

interface HeatComponents {
  z_velocity: number | null;
  surprise_kl: number | null;
  source_diversity: number | null;
  local_voice_ratio: number | null;
  polyphony: number | null;
  geo_confidence_mean: number | null;
  duplication_index: number | null;
}

interface HeatItem {
  country_code: string;
  atlas_heat: number | null;
  components: HeatComponents;
  volume_now: number;
  volume_baseline_daily: number | null;
  warnings: string[];
}

interface HeatResponse {
  hours: number;
  items: HeatItem[];
  refreshed_at: string;
}

interface AtlasHeatListProps {
  hours: number;
  limit?: number;
  onCountrySelect?: (countryCode: string) => void;
}

const WARNING_LABELS: Record<string, string> = {
  external_coverage: 'told from outside',
  wire_dominance: 'one source family dominates',
  thin_coverage: 'few signals, low confidence',
  echo_chamber: 'single dominant frame',
};

function formatPct(value: number | null): string {
  if (value === null || Number.isNaN(value)) return '—';
  return `${Math.round(value * 100)}%`;
}

export default function AtlasHeatList({ hours, limit = 12, onCountrySelect }: AtlasHeatListProps) {
  const [data, setData] = useState<HeatResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(false);
      try {
        const res = await fetch(`/api/v2/heat/countries?hours=${hours}&limit=${limit}`);
        if (!res.ok) throw new Error('fetch failed');
        const json = (await res.json()) as HeatResponse;
        if (!cancelled) {
          setData(json);
          setLoading(false);
        }
      } catch {
        if (!cancelled) {
          setError(true);
          setLoading(false);
        }
      }
    }
    load();
    const interval = setInterval(load, 300_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [hours, limit]);

  const items = useMemo(() => data?.items ?? [], [data]);
  const refreshedAt = data?.refreshed_at;

  return (
    <div className="atlas-heat">
      <div className="atlas-heat__header">
        <span className="atlas-heat__title">composite heat — last {hours}h</span>
        {refreshedAt && (
          <span
            className="atlas-heat__refreshed"
            data-tip={`Updated ${new Date(refreshedAt).toLocaleTimeString()}`}
          >
            ●
          </span>
        )}
      </div>

      <ul className="atlas-heat__list">
        {loading &&
          Array.from({ length: limit }).map((_, i) => (
            <li key={i} className="atlas-heat__row atlas-heat__row--skeleton" />
          ))}

        {error && <li className="atlas-heat__error">Could not load heat</li>}

        {!loading &&
          !error &&
          items.map((item, idx) => {
            const name = resolveCountryName(item.country_code);
            const heat = item.atlas_heat;
            const heatPct = heat !== null ? Math.round(heat * 100) : 0;
            const baseline = item.volume_baseline_daily;
            const baselineLabel =
              baseline !== null ? `${Math.round(baseline)}/day` : '—';
            const tooltipLines = [
              `velocity ${formatPct(item.components.z_velocity)}`,
              `surprise ${formatPct(item.components.surprise_kl)}`,
              `diversity ${formatPct(item.components.source_diversity)}`,
              `local voice ${formatPct(item.components.local_voice_ratio)}`,
              `polyphony ${formatPct(item.components.polyphony)}`,
              `geo conf ${formatPct(item.components.geo_confidence_mean)}`,
              `dup ${formatPct(item.components.duplication_index)}`,
            ];
            const tooltip = `${name}\nvolume ${item.volume_now} (baseline ${baselineLabel})\n${tooltipLines.join('  ·  ')}`;
            return (
              <li
                key={item.country_code}
                className="atlas-heat__row"
                data-tip={tooltip}
                onClick={() => onCountrySelect?.(item.country_code)}
                role={onCountrySelect ? 'button' : undefined}
                tabIndex={onCountrySelect ? 0 : undefined}
                onKeyDown={(e) => {
                  if (!onCountrySelect) return;
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onCountrySelect(item.country_code);
                  }
                }}
              >
                <span className="atlas-heat__rank">{idx + 1}</span>
                <span className="atlas-heat__country">
                  <span className="atlas-heat__country-code">{item.country_code}</span>
                  <span className="atlas-heat__country-name">{name}</span>
                </span>
                <span className="atlas-heat__bar">
                  <span
                    className="atlas-heat__bar-fill"
                    style={{ width: `${heatPct}%` }}
                  />
                </span>
                <span className="atlas-heat__value">{heatPct}</span>
                {item.warnings.length > 0 && (
                  <span className="atlas-heat__flags">
                    {item.warnings.slice(0, 2).map((flag) => (
                      <span
                        key={flag}
                        className={`atlas-heat__flag atlas-heat__flag--${flag.replace(/_/g, '-')}`}
                        data-tip={WARNING_LABELS[flag] ?? flag}
                      >
                        !
                      </span>
                    ))}
                  </span>
                )}
              </li>
            );
          })}
      </ul>
    </div>
  );
}
