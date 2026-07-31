"""Country-code correction layer for archive-derived data (FIPS disaster).

Single code consumer of
``docs/research/country-code-remap/country-code-corrections-v1.json`` — the
machine-readable record of the pre-``b7ab7def`` FIPS/ISO map bug
(country_codes.py mapped FIPS LE→LS so the Lesotho bucket served Lebanese
signals, passed raw GEC codes through as if ISO, etc.).

The hot table ``signals_v2`` was mutated directly
(``scripts/backfill_country_code_remap.py`` + ledgers). Everything derived
from the IMMUTABLE external archive (``/Volumes/Ext/Atlas`` gzip partitions →
``historical_topic_country_daily``, ``historical_evidence_samples``,
archive-topics builds) must instead apply these rules AT ETL/WRITE TIME —
the archive itself is never mutated, so any re-sync from it would re-poison
an unguarded table. Writers wired to this module:

- ``scripts/historical_sync.py``            (historical_topic_country_daily)
- ``scripts/populate_historical_evidence_samples.py``  (historical_evidence_samples)
- ``scripts/archive_cluster_offline.py``    (both, archive-topics-v1 lane)
- ``scripts/backfill_historical_country_remap.py``     (one-time stock heal)

SCOPE (mirrors the corrections artifact + the 2026-07-30 archive measurement):

- The bug lived ONLY in the GDELT ingest lane. RSS/NewsData/social lanes write
  ISO directly and were never wrong (MN=ikon.mn Mongolia, PA=tvn-2.com Panama
  are CORRECT rows that must not move). In archive-derived rows the lane is
  the ``source_family`` field: ``'gdelt'`` is the lane marker.
- ``source_family`` missing/'unknown' = the 2026-05-05..05-09 archive era
  BEFORE the field was recorded. Measured 2026-07-30 against
  ``historical_evidence_samples``: LS-unknown is Lebanon (+ Lebanon-Tennessee
  GDELT geocodes), BH-unknown is Belize (+ Caribbean drug-boat geocodes),
  GA-unknown is Gambia (+ the documented Bathurst-NSW pathology) — all
  GDELT-lane content, zero genuine Lesotho/Bahrain/Gabon rows in the samples.
  So the unknown era is treated as GDELT lane. See
  ``docs/research/country-code-remap/2026-07-28-country-code-remap.md``.
- Families derived from real outlets (press/independent/state/wire/...) are
  ISO-correct and NEVER remapped.

SEMANTICS: single hop from the STORED code — a stored 'MN' becomes 'MC' and
stops, never chained onward to 'MO'. Chains exist (BP→SB→PM→PA→PY, …) because
each stored code was produced by a DIFFERENT FIPS input; apply exactly once.

Special case: FIPS LS = Liechtenstein leaked into the Lebanon bucket. Rows
whose headline matches /liechtenstein|vaduz/i go to LI, all others to LB
(measured 5 vs 1,870 in the 7d hot window; keyword-less Liechtenstein rows
ride to LB at ~375:1 volume odds — accepted, documented).

The module is stdlib-only and loads the JSON lazily (first call), so importing
it never costs anything and environments without the docs/ tree fail LOUDLY on
first use instead of silently not correcting.
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path

# The historical-archive lane scope: 'gdelt' is the lane marker; None/''/
# 'unknown' is the measured pre-family era (see module docstring).
GDELT_LANE_FAMILIES = frozenset({"gdelt", "unknown"})

LIECHTENSTEIN_RE = re.compile(r"liechtenstein|vaduz", re.IGNORECASE)

_ENV_OVERRIDE = "ATLAS_COUNTRY_CORRECTIONS_JSON"

# backend/app/services/country_corrections.py → repo root is parents[3].
_DEFAULT_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs" / "research" / "country-code-remap"
    / "country-code-corrections-v1.json"
)


def corrections_path() -> Path:
    override = os.environ.get(_ENV_OVERRIDE)
    return Path(override) if override else _DEFAULT_PATH


@lru_cache(maxsize=1)
def _load() -> dict[str, str]:
    path = corrections_path()
    if not path.is_file():
        raise FileNotFoundError(
            f"country-code corrections artifact not found: {path} "
            f"(set {_ENV_OVERRIDE} to override). Refusing to run without it — "
            "a silent no-op correction layer would re-poison archive-derived "
            "tables."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    remap = data.get("remap")
    if not isinstance(remap, dict) or not remap:
        raise ValueError(f"corrections artifact has no usable 'remap': {path}")
    return {str(k).upper(): str(v).upper() for k, v in remap.items()}


def load_remap() -> dict[str, str]:
    """The verified stored-code → correct-ISO map (single-hop). Copy."""
    return dict(_load())


def is_gdelt_lane_family(source_family: str | None) -> bool:
    """True when an archive-derived row's source_family marks the GDELT lane
    (including the measured pre-family 'unknown'/missing era)."""
    fam = (source_family or "unknown").strip().lower() or "unknown"
    return fam in GDELT_LANE_FAMILIES


_UNSCOPED = object()


def correct_country_code(
    code: str | None,
    *,
    source_family: object = _UNSCOPED,
    headline: str | None = None,
) -> str:
    """Return the corrected ISO code for one archive-derived row (single hop).

    - ``source_family`` given → the correction applies only to GDELT-lane
      rows (``is_gdelt_lane_family``); other families return unchanged.
      Omit it only when the caller has already scoped the rows to the lane.
    - ``headline`` (when available) drives the LS→LI Liechtenstein split;
      without it LS goes wholesale to LB (documented ~375:1 odds).
    - Codes not in the map (or empty) come back unchanged.
    """
    cc = (code or "").strip().upper()
    remap = _load()
    if cc not in remap:
        return code if code is not None else ""
    if source_family is not _UNSCOPED and not is_gdelt_lane_family(source_family):  # type: ignore[arg-type]
        return cc
    if cc == "LS" and headline and LIECHTENSTEIN_RE.search(headline):
        return "LI"
    return remap[cc]


# ---------------------------------------------------------------------------
# Merge policy for historical_topic_country_daily PK collisions.
#
# Remapping a row's country_code can collide with an existing genuine row at
# the same (day, topic_slug, corrected_cc, source_family, signal_class,
# model_version) — e.g. an ex-LS Lebanon aggregate landing beside a genuine
# gdelt-lane LB row written by the outlet-origin override path. Column
# semantics from scripts/historical_process_partition.py:
#
#   signal_count            count                → SUM (exact)
#   evidence_sample_count   count                → SUM (exact)
#   sentiment_coverage      nlp_sentiment_n/n    → weighted avg by signal_count (exact)
#   topic_coverage          topic_n/n            → weighted avg by signal_count (exact)
#   entity_coverage         entity_n/n           → weighted avg by signal_count (exact)
#   avg_sentiment           sum/sentiment_n      → weighted avg by signal_count
#                           (APPROXIMATE: the true weight sentiment_n is not
#                           stored — sentiment_coverage tracks only the NLP
#                           subset — so signal_count is the best available
#                           proxy; NULL side contributes nothing)
#   local_voice_ratio       ratio or NULL        → weighted avg by signal_count
#                           when both present, else the non-null side
#   source_diversity        unique_sources/n     → NOT mergeable (source-set
#                           overlap between the two rows is unknowable from
#                           the aggregate). Documented policy: keep the value
#                           from the side with the LARGER signal_count (the
#                           majority population; ties → target). Both sides
#                           are recorded in full in the backfill ledger, so
#                           the dropped value is never lost.
# ---------------------------------------------------------------------------

#: columns the merge mutates (everything else in the PK stays fixed).
DAILY_MERGE_COLUMNS = (
    "signal_count",
    "avg_sentiment",
    "sentiment_coverage",
    "topic_coverage",
    "entity_coverage",
    "local_voice_ratio",
    "source_diversity",
    "evidence_sample_count",
)


def _weighted(a: float | None, na: int, b: float | None, nb: int) -> float | None:
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    if na + nb <= 0:
        return a
    return round((a * na + b * nb) / (na + nb), 4)


def merge_daily_rows(target: dict, source: dict) -> dict:
    """Merge a remapped ``source`` aggregate row into the ``target`` row that
    already owns the corrected PK. Returns a NEW dict with the merged
    mergeable columns (see DAILY_MERGE_COLUMNS policy above); PK columns are
    taken from ``target``.
    """
    nt = int(target["signal_count"])
    ns = int(source["signal_count"])
    out = dict(target)
    out["signal_count"] = nt + ns
    out["evidence_sample_count"] = (
        int(target.get("evidence_sample_count") or 0)
        + int(source.get("evidence_sample_count") or 0)
    )
    for col in ("sentiment_coverage", "topic_coverage", "entity_coverage"):
        merged = _weighted(target.get(col), nt, source.get(col), ns)
        out[col] = merged if merged is not None else 0.0
    out["avg_sentiment"] = _weighted(
        target.get("avg_sentiment"), nt, source.get("avg_sentiment"), ns
    )
    out["local_voice_ratio"] = _weighted(
        target.get("local_voice_ratio"), nt, source.get("local_voice_ratio"), ns
    )
    # source_diversity: majority side wins (ties → target); fall back to the
    # other side when the majority side has none. See policy note above.
    major, minor = (source, target) if ns > nt else (target, source)
    sd = major.get("source_diversity")
    out["source_diversity"] = sd if sd is not None else minor.get("source_diversity")
    return out
