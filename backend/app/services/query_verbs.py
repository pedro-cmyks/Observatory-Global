"""Atlas Query Protocol — measured verbs over the substrate (slice 1).

Spec: `docs/superpowers/specs/2026-08-14-atlas-query-protocol-design.md`.
Evidence: `docs/research/investigations/2026-08-14-colombia-ruta-c-basedatos.md`.

WHY THIS EXISTS. On 2026-08-14 the same question was put to Atlas three ways.
The UI (route A) spent 22 minutes and produced one story with a Venezuelan
chip. Six direct queries against the substrate (route C) produced the actual
answer: ONE event living in nine active identities, a "Colombia" topic whose
receipts are Belarusian, and 60 of 72 political signals that never became a
story at all. The substrate answers questions the UI cannot formulate. This
module is the way to ask them without a browser — and, via
`scripts/query_parity_check.py`, the instrument that catches the UI lying.

WHAT IT IS NOT. Not SQL exposure: the verbs are a fixed vocabulary of
measurements Atlas already makes, and every one is parameterized, capped and
bounded. Not a chat: no model sits between the analyst and the number. Not a
second truth: it reads the SAME lane serving reads (see `_engine_version`), so
a divergence is a defect on one side, never a difference of opinion.

THE FOUR CONTRACT RULES, and where each is enforced here:

1. Every response carries its measured WINDOW (`window_block`), its
   POPULATION/BASIS (`ingest_basis.basis_field` + an explicit population
   block), and WHAT IT COULD NOT MEASURE (`could_not_measure[]`).
2. A failed lane returns a NAMED reason, never a zero — enforced by running
   every lane through `focus_lanes.LaneRunner`, which cannot raise and records
   `db_busy` / `deadline` / `db_error`. `degraded_result()` deliberately omits
   the `data` key so a degraded verb is structurally unreadable as an empty
   measurement.
3. Bounded by construction: measured per-lane budgets (below) inside a global
   deadline, plus row caps DECLARED in the response whenever they bite.
4. No silent filtering: a term we refuse to run comes back in
   `rejected_terms[]` with a reason code.

MEASURED COST, prod, 2026-08-14 (psql wall time; subtract ~0.6s for psql
startup on the multi-statement runs):

    lane                        query                                  measured
    identities_covering.members 2 terms / 14d / group+join            ~1.5s
    identities_covering.labels  2 terms over dynamic_topics             0.2s
    unclustered.counts          1 term / 24h + NOT EXISTS               0.3s (warm)
    unclustered.detail          1 term / 24h + LATERAL member lookup   58ms (warm)
    receipt_geography           48 members, group by 3                  0.4s
    term match alone            `lower(headline) LIKE '%espriella%'`    324ms cold

The trigram bitmap scan is the cost floor and it is COLD-SENSITIVE — the same
class `focus_lanes` measured at 576ms warm / 14.5s cold for `%trump%`. Budgets
below therefore carry cold-page-in headroom rather than tracking warm times.

THE PREDICATE IS LOAD-BEARING. `idx_signals_v2_headline_trgm` is a GIN on
`lower(headline)`. A trigram index only serves a predicate matching its
expression character for character, so `HEADLINE_MATCH_EXPR` must stay exactly
that spelling. In particular it must NOT be "improved" to
`f_unaccent(lower(headline))` — that is a different index
(`idx_signals_headline_trgm`) and the swap would silently return this endpoint
to a sequential scan of 1.1M rows. Same lesson, same shape, as
`focus_lanes.PERSON_MATCH_EXPR`.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

from app.services import ingest_basis

# ---------------------------------------------------------------- contract

VERB_CONTRACT = "atlas-query-verb-v1"
REQUEST_CONTRACT = "atlas-query-v1"

STATUS_LIVE = "live"
STATUS_DEGRADED = "degraded"

VERBS = frozenset({
    "identities_covering",
    "receipt_geography",
    "unclustered_signals",
    "voice_mix",
})

# Composition (`$1` chaining, spec §"Qué SÍ es") is explicitly the NEXT slice.
# Slice 1 refuses it loudly: silently treating "$1" as a literal topic ref
# would answer a question nobody asked and look like a measured empty.
_COMPOSITION_REF = re.compile(r"^\$\d+$")

# Per-request verb cap. The wire shape stays a LIST so slice 2 can add
# chaining without a breaking change, but each verb here is independent and
# the count is bounded because the request's cost is the sum of its verbs.
MAX_VERBS_PER_REQUEST = 4

MAX_TERMS = 12

# A trigram index needs 3 characters to produce a trigram; a 1-2 char needle
# degrades to a full scan of 1.1M rows. Rejected loudly rather than run.
MIN_TERM_LENGTH = 3


class VerbError(Exception):
    """A refusal with a machine-readable reason code.

    Never a bare 400: the caller gets the reason AND the detail, because a
    protocol whose refusals are unexplained is a protocol that gets guessed at.
    """

    def __init__(self, reason: str, detail: str, status_code: int = 400):
        super().__init__(detail)
        self.reason = reason
        self.detail = detail
        self.status_code = status_code


# ------------------------------------------------------------------- caps
# Every row-returning lane is capped, and the cap is DECLARED in the response
# whenever it bites (`truncation_block`). A silently truncated list is exactly
# the "20 sources over 36 domains" defect this protocol exists to catch.

SCAN_CAP = 4000          # matched signals a term scan will consider
IDENTITY_CAP = 60        # identities returned per lane
GEO_GROUP_CAP = 400      # (country, lang, origin) groups
LANDING_CAP = 40         # distinct topics matched signals landed in
UNASSIGNED_SAMPLE_CAP = 20
DETAIL_CAP = 1000        # matched signals pulled back for the landing lane

# Per-lane statement_timeout (ms). Cold-trigram headroom, not warm times.
LANE_BUDGETS_MS: dict[str, int] = {
    "identities_members": 8000,
    "identities_labels": 3000,
    "receipt_geography": 5000,
    "receipt_resolvability": 4000,
    "unclustered_counts": 8000,
    "unclustered_detail": 8000,
    "voice_members": 5000,
}

# Global wall-clock bound for one request, whatever it asks for. Sized so a
# 4-verb request cannot hold a pool connection (max_size=10) longer than this.
QUERY_DEADLINE_MS = 15000

HEADLINE_MATCH_EXPR = "lower(headline) LIKE"
LABEL_MATCH_EXPR = "lower(dt.label) LIKE"

_LIKE_SPECIALS = re.compile(r"([\\%_])")

DEFAULT_STATES = ("active", "candidate")


# ----------------------------------------------------------------- needles

def like_needle(term: str) -> Optional[str]:
    """Fold a term into the LIKE needle `idx_signals_v2_headline_trgm` expects.

    Lowercased (the index is on `lower(headline)`) and NOT accent-folded (that
    index does not fold; folding here would silently miss every accented row —
    the mirror image of the "Mbappé hole", which applies to the *persons*
    index because mig 090 indexed `f_unaccent`). LIKE metacharacters are
    escaped: an unescaped `%` in a user term matches the entire corpus.
    """
    cleaned = (term or "").strip().lower()
    if not cleaned:
        return None
    return "%" + _LIKE_SPECIALS.sub(r"\\\1", cleaned) + "%"


def normalize_terms(
    terms: Iterable[str], *, require_one: bool = False,
) -> tuple[list[str], list[dict]]:
    """-> (needles, rejected). Rejections are REPORTED, never silent."""
    needles: list[str] = []
    rejected: list[dict] = []
    seen: set[str] = set()

    for raw in list(terms or []):
        text = str(raw or "").strip()
        if not text:
            rejected.append({"term": raw, "reason": "term_empty",
                             "detail": "blank terms match nothing and are not run"})
            continue
        if len(text) < MIN_TERM_LENGTH:
            rejected.append({
                "term": text, "reason": "term_too_short",
                "detail": "terms under 3 characters cannot use the trigram index "
                          "and would scan the corpus",
            })
            continue
        if len(needles) >= MAX_TERMS:
            rejected.append({"term": text, "reason": "term_cap_exceeded",
                             "detail": f"at most {MAX_TERMS} terms are run per verb"})
            continue
        needle = like_needle(text)
        key = text.lower()
        if needle is None or key in seen:
            continue
        seen.add(key)
        needles.append(needle)

    if require_one and not needles:
        raise VerbError(
            "no_usable_terms",
            "every supplied term was rejected; see rejected_terms for why",
        )
    return needles, rejected


# ------------------------------------------------------------------ window

def window_block(
    *, requested_hours: int, oldest_available: Optional[datetime],
    now: Optional[datetime] = None,
) -> dict:
    """The measured window — and the honest gap between it and the request.

    Hot retention measured 2026-08-14: the oldest `signals_v2` row was
    2026-08-05, ~9 days. A caller asking for 14 days therefore CANNOT be
    answered over 14 days, and a protocol that quietly returns 9 days of rows
    under a 14-day label is telling the same class of lie the UI told with
    "18 · last 7d". So the shortfall is computed and stated.

    `fully_covered=None` (not False) when retention is unknown: unknown is a
    third state and collapsing it into either bool is a fabricated claim.
    """
    now = now or datetime.now(timezone.utc)
    measured_from = now - timedelta(hours=requested_hours)
    block: dict[str, Any] = {
        "requested_hours": requested_hours,
        "measured_from": measured_from.isoformat(),
        "measured_to": now.isoformat(),
        "hot_retention_oldest": oldest_available.isoformat() if oldest_available else None,
    }
    if oldest_available is None:
        block["fully_covered"] = None
        block["shortfall_hours"] = None
        block["note"] = (
            "hot-retention depth could not be measured, so it is unknown whether "
            "the requested window is fully covered"
        )
        return block

    shortfall = (oldest_available - measured_from).total_seconds() / 3600.0
    if shortfall <= 0:
        block["fully_covered"] = True
        block["shortfall_hours"] = 0
        block["note"] = "the requested window lies inside hot retention"
        return block

    block["fully_covered"] = False
    block["shortfall_hours"] = round(shortfall, 1)
    block["note"] = (
        f"the hot corpus begins {oldest_available.isoformat()}; "
        f"{round(shortfall / 24, 1)} days of the requested window predate it and "
        "were NOT measured (older rows live in the external archive, which this "
        "verb does not read)"
    )
    return block


# ---------------------------------------------------------------- envelope

def population_block(**kw: Any) -> dict:
    return dict(kw)


def truncation_block(*, returned: int, cap: int) -> dict:
    """Declare the cap whenever it bit. `truncated` is the field a reader must
    be able to see WITHOUT knowing the cap by heart."""
    return {"truncated": returned >= cap, "cap": cap, "returned": returned}


def result_envelope(
    *, verb: str, window: dict, population: dict,
    could_not_measure: Optional[list] = None,
    rejected_terms: Optional[list] = None,
) -> dict:
    """The shell every LIVE verb result carries."""
    out: dict[str, Any] = {
        "contract": VERB_CONTRACT,
        "verb": verb,
        "status": STATUS_LIVE,
        "window": window,
        "basis": ingest_basis.basis_field(),
        "population": population,
        "could_not_measure": list(could_not_measure or []),
    }
    if rejected_terms:
        out["rejected_terms"] = rejected_terms
    return out


def degraded_result(
    verb: str, reason: str, *, window: Optional[dict] = None,
    detail: Optional[str] = None, population: Optional[dict] = None,
) -> dict:
    """A verb that could not be measured.

    Carries NO `data` key at all — the single most important shape in this
    module. A degraded verb that served `data: {...zeros}` would be read as a
    measurement, which is precisely how "0% own voices" got onto a screen
    about a country whose press was covering the story massively.
    """
    out: dict[str, Any] = {
        "contract": VERB_CONTRACT,
        "verb": verb,
        "status": STATUS_DEGRADED,
        "reason": reason,
        "detail": detail or _DEGRADED_DETAIL.get(reason, "this verb could not be measured"),
        "basis": ingest_basis.basis_field(),
    }
    if window:
        out["window"] = window
    if population:
        out["population"] = population
    return out


_DEGRADED_DETAIL = {
    "db_busy": "the substrate did not answer inside this verb's measured budget — "
               "not a zero, a timeout; retry shortly",
    "deadline": "the request's global deadline was spent by earlier verbs before "
                "this one ran — not a zero, an unrun lane",
    "db_error": "the lane failed; this is an absence of measurement, not a measured absence",
    "no_pool": "no database connection was available; nothing was measured",
}


# ------------------------------------------------------------- verb inputs

def validate_ask(ask: Any) -> list[tuple[str, dict]]:
    """Validate the `ask` list -> [(verb, args)]. Every refusal is named."""
    if not isinstance(ask, list):
        raise VerbError("bad_ask", "`ask` must be a list of single-key verb objects")
    if not ask:
        raise VerbError("empty_ask", "`ask` must contain at least one verb")
    if len(ask) > MAX_VERBS_PER_REQUEST:
        raise VerbError(
            "too_many_verbs",
            f"at most {MAX_VERBS_PER_REQUEST} verbs per request in slice 1 "
            "(composition is the next slice)",
        )

    out: list[tuple[str, dict]] = []
    for item in ask:
        if not isinstance(item, dict) or len(item) != 1:
            raise VerbError("bad_verb_object",
                            "each ask entry must be an object with exactly one verb key")
        verb, args = next(iter(item.items()))
        if verb not in VERBS:
            raise VerbError(
                "unknown_verb",
                f"unknown verb '{verb}'; slice 1 serves {sorted(VERBS)}",
            )
        if not isinstance(args, dict):
            raise VerbError("bad_verb_args", f"arguments for '{verb}' must be an object")
        for key, value in args.items():
            if isinstance(value, str) and _COMPOSITION_REF.match(value.strip()):
                raise VerbError(
                    "composition_not_supported",
                    f"'{key}' references a previous result ({value}); verb "
                    "composition is not in slice 1 — run the verbs separately "
                    "and pass the value explicitly",
                )
        out.append((verb, args))
    return out


def parse_topic_ref(ref: Any) -> tuple[str, Optional[int]]:
    """-> (topic_members key, numeric dynamic id or None).

    Accepts `12927`, `dt-12927`, `dynamic-topic-12927` (the research docs use
    all three) and atlas slugs, which have no numeric id.
    """
    text = str(ref or "").strip()
    if not text:
        raise VerbError("missing_topic_id", "this verb requires `topic_id`")
    # Thread ids can carry a `--CC` country suffix in the serving contract.
    text = text.split("--", 1)[0]
    if text.isdigit():
        return f"dynamic-topic-{int(text)}", int(text)
    m = re.match(r"^(?:dt-|dynamic-topic-)(\d+)$", text)
    if m:
        return f"dynamic-topic-{int(m.group(1))}", int(m.group(1))
    if not re.match(r"^[a-z0-9][a-z0-9\-]{0,80}$", text, re.IGNORECASE):
        raise VerbError("bad_topic_id", f"'{ref}' is not a recognizable topic reference")
    return text, None


def validate_voice_mix_scope(args: dict) -> tuple[str, str]:
    """voice_mix takes EXACTLY one of topic_id | country."""
    topic = str(args.get("topic_id") or "").strip()
    country = str(args.get("country") or "").strip()
    if topic and country:
        raise VerbError("ambiguous_scope",
                        "voice_mix takes exactly one of `topic_id` or `country`")
    if topic:
        return "topic_id", topic
    if country:
        if not re.match(r"^[A-Za-z]{2}$", country):
            raise VerbError("bad_country_code",
                            "`country` must be a 2-letter country code")
        return "country", country.upper()
    raise VerbError("missing_scope",
                    "voice_mix requires either `topic_id` or `country`")


def validate_country(raw: Any) -> Optional[str]:
    if raw is None or str(raw).strip() == "":
        return None
    text = str(raw).strip()
    if not re.match(r"^[A-Za-z]{2}$", text):
        raise VerbError("bad_country_code", "`country` must be a 2-letter country code")
    return text.upper()


def validate_states(raw: Any) -> list[str]:
    if raw is None:
        return list(DEFAULT_STATES)
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        raise VerbError("bad_states", "`states` must be a list of lifecycle states")
    allowed = {"active", "candidate", "deprecated", "retired"}
    out = [str(s).strip().lower() for s in raw if str(s).strip()]
    bad = [s for s in out if s not in allowed]
    if bad:
        raise VerbError("bad_states", f"unknown lifecycle state(s): {bad}")
    return out or list(DEFAULT_STATES)


def clamp_hours(raw: Any, *, default: int, maximum: int = 24 * 90) -> int:
    try:
        hours = int(raw) if raw is not None else default
    except (TypeError, ValueError):
        raise VerbError("bad_window", "window must be an integer number of hours/days")
    if hours < 1:
        raise VerbError("bad_window", "window must be at least 1 hour")
    return min(hours, maximum)


# --------------------------------------------------------------------- SQL
# Built here (pure) so shapes are test-pinned without a database, and so the
# caps and the engine-version join live in ONE place.

def term_predicate(needles: list[str], *, start_index: int,
                   expr: str = HEADLINE_MATCH_EXPR) -> tuple[str, list]:
    """OR the needles as bound parameters. Never string-interpolated."""
    parts = [f"{expr} ${start_index + i}" for i in range(len(needles))]
    return "(" + " OR ".join(parts) + ")", list(needles)


# `topic_members.topic_id` is 'dynamic-topic-<n>' or an atlas slug; 14 chars of
# prefix, so the numeric id starts at 15. LEFT JOIN so atlas slugs still return.
_DT_JOIN = """
    LEFT JOIN dynamic_topics dt
      ON dt.id = CASE WHEN mem.topic_id ~ '^dynamic-topic-[0-9]+$'
                      THEN substring(mem.topic_id from 15)::bigint END
"""

# Serving-parity filter. `quarantined` (mig 087) hides black-hole members from
# serving; the protocol must apply the SAME filter or the double-check would be
# comparing two different populations and every topic would "diverge".
_MEMBER_FILTER = """
      AND tm.role = 'evidence'
      AND tm.engine_version = {ev}
      AND tm.quarantined IS NOT TRUE
"""


def identities_covering_member_sql(
    needles: list[str], *, country: Optional[str], hours: int,
) -> tuple[str, list]:
    """Identities whose MEMBER signals match the terms."""
    params: list[Any] = [hours]
    pred, term_params = term_predicate(needles, start_index=2)
    params += term_params
    idx = len(params)

    country_clause = ""
    if country:
        idx += 1
        country_clause = f" AND s.country_code = ${idx}"
        params.append(country)

    idx += 1
    params.append(_engine_version())
    ev = f"${idx}"

    sql = f"""
        WITH matched AS (
            SELECT s.id
            FROM signals_v2 s
            WHERE s.timestamp > NOW() - ($1::int * INTERVAL '1 hour')
              AND {pred}{country_clause}
            LIMIT {SCAN_CAP}
        ), mem AS (
            SELECT tm.topic_id, COUNT(DISTINCT tm.signal_id)::int AS matched_members
            FROM topic_members tm
            JOIN matched m ON m.id = tm.signal_id
            WHERE TRUE {_MEMBER_FILTER.format(ev=ev)}
            GROUP BY tm.topic_id
            ORDER BY matched_members DESC
            LIMIT {IDENTITY_CAP}
        )
        SELECT mem.topic_id, mem.matched_members,
               dt.id AS dt_id, dt.label, dt.state, dt.label_status,
               dt.is_umbrella, dt.parent_id, dt.first_seen, dt.agg_n_signals
        FROM mem
        {_DT_JOIN}
        ORDER BY mem.matched_members DESC
    """
    return sql, params


def identities_covering_label_sql(
    needles: list[str], *, country: Optional[str], states: Optional[list[str]] = None,
) -> tuple[str, list]:
    """Identities whose LABEL matches the terms.

    A second, independent basis. The nine Colombia identities were found this
    way, and a member-only verb would have missed the ones whose signals had
    already aged out of hot retention while the identity stayed active — which
    is exactly the fragmentation being investigated. `country` is deliberately
    NOT applied here: `dynamic_topics` carries no country column, and the
    caller is told so via `could_not_measure` rather than being handed a
    silently unscoped list.
    """
    params: list[Any] = [list(states or DEFAULT_STATES)]
    pred, term_params = term_predicate(needles, start_index=2, expr=LABEL_MATCH_EXPR)
    params += term_params
    sql = f"""
        SELECT dt.id AS dt_id, dt.label, dt.state, dt.label_status,
               dt.is_umbrella, dt.parent_id, dt.first_seen, dt.agg_n_signals
        FROM dynamic_topics dt
        WHERE dt.state = ANY($1::text[])
          AND dt.label IS NOT NULL
          AND {pred}
        ORDER BY dt.agg_n_signals DESC NULLS LAST
        LIMIT {IDENTITY_CAP}
    """
    return sql, params


def receipt_geography_sql(topic_key: str, *, dimension: str = "country_code") -> tuple[str, list]:
    """Country x language x outlet-origin distribution over a topic's members.

    Serves subject country AND outlet origin as separate dimensions because
    they are different facts and conflating them is the exact error
    `ingest_basis` was written for: "Colombia's receipts" can mean the story is
    about Colombia (`country_code`) or that a Colombian outlet published it
    (`source_origin_country`). dt-12927 on 2026-08-14 had VE:24 / DE:24 subject
    countries and not one Colombian receipt, under the label "Colombia
    Declares Disaster".
    """
    ev = _engine_version()
    sql = f"""
        SELECT COALESCE(NULLIF(TRIM(s.country_code), ''), '(unknown)') AS country_code,
               COALESCE(NULLIF(TRIM(s.source_lang), ''), '(unknown)') AS source_lang,
               COALESCE(NULLIF(TRIM(s.source_origin_country), ''), '(unknown)') AS origin,
               COUNT(*)::int AS n
        FROM topic_members tm
        JOIN signals_v2 s ON s.id = tm.signal_id
        WHERE tm.topic_id = $1 {_MEMBER_FILTER.format(ev='$2')}
        GROUP BY 1, 2, 3
        ORDER BY n DESC
        LIMIT {GEO_GROUP_CAP}
    """
    return sql, [topic_key, ev]


def receipt_resolvability_sql(topic_key: str) -> tuple[str, list]:
    """How many members still have a signal row at all.

    Hot retention is ~7 days; `topic_members` is not pruned in lockstep. A
    topic can therefore carry members whose receipts no longer exist — the
    starvation class (`member_sample_starved`, 2026-08-04). Counting the gap is
    what turns "this topic has 8 receipts" from a lie into a measurement.

    `distinct_sources` rides this same scan because it is the counterpart to
    the defect that opened the parity ledger: prod served "20 Sources" over 37
    receipts carrying 36 distinct domains, because a 20-item DISPLAY slice was
    being counted. The true count needs the full member set, which is exactly
    what this lane already touches.
    """
    ev = _engine_version()
    sql = f"""
        SELECT COUNT(*)::int AS members,
               COUNT(s.id)::int AS resolvable,
               COUNT(DISTINCT s.source_name)::int AS distinct_sources
        FROM topic_members tm
        LEFT JOIN signals_v2 s ON s.id = tm.signal_id
        WHERE tm.topic_id = $1 {_MEMBER_FILTER.format(ev='$2')}
    """
    return sql, [topic_key, ev]


def unclustered_counts_sql(needles: list[str], *, hours: int,
                           country: Optional[str] = None) -> tuple[str, list]:
    """Exact matched / unassigned counts. One scan, no row cap on the count."""
    params: list[Any] = [hours]
    pred, term_params = term_predicate(needles, start_index=2)
    params += term_params
    idx = len(params)

    country_clause = ""
    if country:
        idx += 1
        country_clause = f" AND s.country_code = ${idx}"
        params.append(country)

    idx += 1
    params.append(_engine_version())
    ev = f"${idx}"

    sql = f"""
        WITH matched AS (
            SELECT s.id
            FROM signals_v2 s
            WHERE s.timestamp > NOW() - ($1::int * INTERVAL '1 hour')
              AND {pred}{country_clause}
            LIMIT {SCAN_CAP}
        )
        SELECT COUNT(*)::int AS matched,
               COUNT(*) FILTER (
                   WHERE NOT EXISTS (
                       SELECT 1 FROM topic_members tm
                       WHERE tm.signal_id = matched.id {_MEMBER_FILTER.format(ev=ev)}
                   )
               )::int AS unassigned
        FROM matched
    """
    return sql, params


def unclustered_landing_sql(needles: list[str], *, hours: int,
                            country: Optional[str] = None) -> tuple[str, list]:
    """WHERE the assigned ones landed — the finding that broke the case open.

    60 of 72 De la Espriella signals carried no topic at all, and of the twelve
    that landed, one went to a German pension-reform story. A verb that only
    counted the unassigned would have missed that half of the defect.
    """
    params: list[Any] = [hours]
    pred, term_params = term_predicate(needles, start_index=2)
    params += term_params
    idx = len(params)

    country_clause = ""
    if country:
        idx += 1
        country_clause = f" AND s.country_code = ${idx}"
        params.append(country)

    idx += 1
    params.append(_engine_version())
    ev = f"${idx}"

    sql = f"""
        WITH matched AS (
            SELECT s.id
            FROM signals_v2 s
            WHERE s.timestamp > NOW() - ($1::int * INTERVAL '1 hour')
              AND {pred}{country_clause}
            LIMIT {DETAIL_CAP}
        ), mem AS (
            SELECT tm.topic_id, COUNT(DISTINCT tm.signal_id)::int AS n
            FROM topic_members tm
            JOIN matched m ON m.id = tm.signal_id
            WHERE TRUE {_MEMBER_FILTER.format(ev=ev)}
            GROUP BY tm.topic_id
            ORDER BY n DESC
            LIMIT {LANDING_CAP}
        )
        SELECT mem.topic_id, mem.n, dt.label, dt.state, dt.label_status
        FROM mem
        {_DT_JOIN}
        ORDER BY mem.n DESC
    """
    return sql, params


def unassigned_sample_sql(needles: list[str], *, hours: int,
                          country: Optional[str] = None) -> tuple[str, list]:
    """A few of the signals that became nothing — receipts for the claim."""
    params: list[Any] = [hours]
    pred, term_params = term_predicate(needles, start_index=2)
    params += term_params
    idx = len(params)

    country_clause = ""
    if country:
        idx += 1
        country_clause = f" AND s.country_code = ${idx}"
        params.append(country)

    idx += 1
    params.append(_engine_version())
    ev = f"${idx}"

    sql = f"""
        SELECT s.id, s.headline, s.source_name, s.country_code, s.source_lang,
               s.timestamp
        FROM signals_v2 s
        WHERE s.timestamp > NOW() - ($1::int * INTERVAL '1 hour')
          AND {pred}{country_clause}
          AND NOT EXISTS (
              SELECT 1 FROM topic_members tm
              WHERE tm.signal_id = s.id {_MEMBER_FILTER.format(ev=ev)}
          )
        ORDER BY s.timestamp DESC
        LIMIT {UNASSIGNED_SAMPLE_CAP}
    """
    return sql, params


def hot_retention_sql() -> str:
    """Cheapest possible retention probe — the index gives MIN(timestamp)."""
    return "SELECT MIN(timestamp) AS oldest FROM signals_v2"


def _engine_version() -> str:
    """The SAME lane serving reads.

    Imported lazily so this module stays importable without the serving stack.
    Parity by construction: if F4 flips serving to `unified-v2`, the protocol
    follows in the same breath. Two lanes would make the double-check compare
    two different questions and call the difference a defect.
    """
    from app.services.thread_intelligence import topic_members_engine_version
    return topic_members_engine_version()


# ------------------------------------------------------------- aggregation

def summarize_identities(member_rows: list[dict], label_rows: list[dict]) -> dict:
    """Merge the two bases into one identity list, tagging HOW each matched.

    The dispersion summary is the headline number: nine identities for one
    event is the finding, and it should be legible without counting the list.
    """
    by_key: dict[str, dict] = {}

    def _key(row: dict) -> str:
        dt_id = row.get("dt_id")
        if dt_id is not None:
            return f"dynamic-topic-{int(dt_id)}"
        return str(row.get("topic_id") or "")

    for row in member_rows:
        key = _key(row) or str(row.get("topic_id") or "")
        entry = by_key.setdefault(key, _identity_entry(key, row))
        entry["matched_members"] = int(row.get("matched_members") or 0)
        if "members" not in entry["matched_by"]:
            entry["matched_by"].append("members")

    for row in label_rows:
        key = _key(row)
        entry = by_key.setdefault(key, _identity_entry(key, row))
        _fill_identity(entry, row)
        # A label-lane hit proves the identity row exists, so an id the member
        # lane could only see as an orphan is reclassified here.
        if entry["kind"] == KIND_ORPHAN:
            entry["kind"] = KIND_DYNAMIC
        if "label" not in entry["matched_by"]:
            entry["matched_by"].append("label")

    identities = sorted(
        by_key.values(),
        key=lambda e: (-(e.get("matched_members") or 0),
                       -(e.get("lifetime_signals") or 0)),
    )

    labels_seen: dict[str, int] = {}
    for e in identities:
        lab = (e.get("label") or "").strip().lower()
        if lab:
            labels_seen[lab] = labels_seen.get(lab, 0) + 1

    return {
        "identities": identities,
        "summary": {
            "identity_count": len(identities),
            "by_kind": {
                KIND_DYNAMIC: sum(1 for e in identities if e["kind"] == KIND_DYNAMIC),
                KIND_ATLAS: sum(1 for e in identities if e["kind"] == KIND_ATLAS),
                KIND_ORPHAN: sum(1 for e in identities if e["kind"] == KIND_ORPHAN),
            },
            "active": sum(1 for e in identities if e.get("state") == "active"),
            "candidate": sum(1 for e in identities if e.get("state") == "candidate"),
            "umbrellas": sum(1 for e in identities if e.get("is_umbrella")),
            "court_failed": sum(1 for e in identities
                                if e.get("label_status") in ("failed", "too_broad")),
            "matched_members_total": sum(int(e.get("matched_members") or 0)
                                         for e in identities),
            "lifetime_signals_total": sum(int(e.get("lifetime_signals") or 0)
                                          for e in identities),
            # Two identities carrying the SAME label is the loudest possible
            # signal of argmax dispersion — three of the nine Colombia rows
            # said "Death Toll Rises to/Past 130/132".
            "duplicate_labels": sorted(
                [lab for lab, n in labels_seen.items() if n > 1]
            ),
        },
    }


# What kind of thing a matched topic_id actually is. Collapsing these three
# into one "identities" list would repeat two settled confusions: an atlas
# topic is a CATEGORY (the R3 lens), never a story row (2026-07-04), and a
# member row whose identity no longer exists is not an identity with no label
# — it is an orphan, and saying so is the difference between a null and a
# finding. Found on this verb's first live run: `dynamic-topic-11581` carried
# 28 matching members and has no `dynamic_topics` row at all.
KIND_DYNAMIC = "dynamic_identity"
KIND_ATLAS = "atlas_category"
KIND_ORPHAN = "orphan_members"


def _classify_kind(key: str, row: dict) -> str:
    if not key.startswith("dynamic-topic-"):
        return KIND_ATLAS
    # The label lane can only yield rows that exist; only the member lane can
    # surface an id with no identity behind it.
    if row.get("dt_id") is None and row.get("state") is None:
        return KIND_ORPHAN
    return KIND_DYNAMIC


def _identity_entry(key: str, row: dict) -> dict:
    entry = {
        "topic_id": key,
        "kind": _classify_kind(key, row),
        "matched_by": [],
        "matched_members": 0,
        "label": None, "state": None, "label_status": None,
        "is_umbrella": None, "parent_id": None,
        "first_seen": None, "lifetime_signals": None,
    }
    _fill_identity(entry, row)
    return entry


def _fill_identity(entry: dict, row: dict) -> None:
    if row.get("label") is not None:
        entry["label"] = row.get("label")
    if row.get("state") is not None:
        entry["state"] = row.get("state")
    if row.get("label_status") is not None:
        entry["label_status"] = row.get("label_status")
    if row.get("is_umbrella") is not None:
        entry["is_umbrella"] = bool(row.get("is_umbrella"))
    if row.get("parent_id") is not None:
        entry["parent_id"] = int(row["parent_id"])
    fs = row.get("first_seen")
    if fs is not None:
        entry["first_seen"] = fs.isoformat() if hasattr(fs, "isoformat") else str(fs)
    if row.get("agg_n_signals") is not None:
        entry["lifetime_signals"] = int(row["agg_n_signals"])


def summarize_geography(rows: list[dict]) -> dict:
    """Collapse the (country, lang, origin) groups into three distributions."""
    subject: dict[str, int] = {}
    langs: dict[str, int] = {}
    origins: dict[str, int] = {}
    total = 0
    for r in rows:
        n = int(r.get("n") or 0)
        total += n
        subject[r.get("country_code") or "(unknown)"] = \
            subject.get(r.get("country_code") or "(unknown)", 0) + n
        langs[r.get("source_lang") or "(unknown)"] = \
            langs.get(r.get("source_lang") or "(unknown)", 0) + n
        origins[r.get("origin") or "(unknown)"] = \
            origins.get(r.get("origin") or "(unknown)", 0) + n

    def _dist(d: dict[str, int], key: str) -> list[dict]:
        return [
            {key: k, "n": v, "pct": round(v / total, 4) if total else 0.0}
            for k, v in sorted(d.items(), key=lambda kv: -kv[1])
        ]

    return {
        "receipts_counted": total,
        "subject_countries": _dist(subject, "cc"),
        "languages": _dist(langs, "lang"),
        "outlet_origins": _dist(origins, "cc"),
        "dimensions": {
            "subject_countries": "signals_v2.country_code — what the story is ABOUT",
            "outlet_origins": "signals_v2.source_origin_country — where the OUTLET is based",
            "languages": "signals_v2.source_lang — the language it was published in",
        },
    }


def summarize_unclustered(counts: dict, landing_rows: list[dict],
                          sample_rows: list[dict]) -> dict:
    matched = int(counts.get("matched") or 0)
    unassigned = int(counts.get("unassigned") or 0)
    landed = [
        {
            "topic_id": r.get("topic_id"),
            "n": int(r.get("n") or 0),
            "label": r.get("label"),
            "state": r.get("state"),
            "label_status": r.get("label_status"),
        }
        for r in landing_rows
    ]
    return {
        "matched_signals": matched,
        "unassigned_signals": unassigned,
        "assigned_signals": max(matched - unassigned, 0),
        "unassigned_share": round(unassigned / matched, 4) if matched else None,
        "landed_in": landed,
        "landed_in_distinct_topics": len(landed),
        # A signal can hold evidence membership in several topics at once, so
        # these per-topic counts can sum ABOVE `assigned_signals`. Measured on
        # the first live run: 6 assigned signals, 7 memberships. Stated here
        # because an unexplained "6 vs 7" reads as a broken count.
        "landed_in_memberships": sum(r["n"] for r in landed),
        "landed_in_note": (
            "per-topic counts are memberships, not signals: one signal can be "
            "evidence for several topics, so these can sum above assigned_signals"
        ),
        "unassigned_sample": [
            {
                "id": int(r["id"]) if r.get("id") is not None else None,
                "headline": r.get("headline"),
                "source_name": r.get("source_name"),
                "country_code": r.get("country_code"),
                "source_lang": r.get("source_lang"),
                "timestamp": r["timestamp"].isoformat()
                if hasattr(r.get("timestamp"), "isoformat") else r.get("timestamp"),
            }
            for r in sample_rows
        ],
    }
