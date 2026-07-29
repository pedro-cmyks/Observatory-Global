"""Label Court pure-logic: verdict parsing + neutral-label building."""
import asyncio

from scripts.label_court import (
    parse_verdict, build_neutral_label, _dominant_geo,
    _judge_prompt, _flatten_family_receipts, _umbrella_clause,
    _CHILD_LABELS_RANKED_SQL, _UMBRELLA_MAX_CHILDREN, _UMBRELLA_RECEIPTS_PER_CHILD,
    _RECEIPTS_SQL, _RECEIPTS_FALLBACK_SQL, _receipts_for, topic_members_engine_version,
    _SINGLE_CHILD_SKIP_SQL, _SINGLE_CHILD_CLEANUP_SQL, _reason_quotes_a_receipt,
    _WITHHOLD_CLEAR_SQL,
)


def test_parse_verdict_json():
    v, r = parse_verdict('{"verdict": "failed", "reason": "Greek traffic news, not a British teen"}')
    assert v == "failed"
    assert "Greek" in r


def test_parse_verdict_fenced_json():
    v, _ = parse_verdict('```json\n{"verdict": "entailed", "reason": "fits"}\n```')
    assert v == "entailed"


def test_parse_verdict_bare_word():
    assert parse_verdict("failed")[0] == "failed"
    assert parse_verdict("The verdict is PARTIAL here")[0] == "partial"


def test_parse_verdict_unknown_defaults_partial_never_entailed():
    # an unreadable judgment must NOT clear a label
    assert parse_verdict("")[0] == "partial"
    assert parse_verdict("¯\\_(ツ)_/¯")[0] == "partial"


def test_dominant_geo_ignores_xx_and_empty():
    assert _dominant_geo(["GR", "GR", "XX", "", "IR"]) == "GR"
    assert _dominant_geo(["XX", "", None]) == "Global"


def test_build_neutral_label_shape():
    receipts = [
        {"headline": "Family killed in Halkidiki tanker crash", "country_code": "GR"},
        {"headline": "Halkidiki road tragedy claims mother and baby", "country_code": "GR"},
        {"headline": "Two women die in Lesbos collision", "country_code": "GR"},
    ]
    lab = build_neutral_label(receipts)
    assert lab.startswith("GR:")
    assert "from 3 receipts" in lab
    # subject drawn from the receipts, never a fabricated narrative
    assert "Halkidiki" in lab or "Lesbos" in lab or "crash" in lab.lower()


def test_build_neutral_label_decodes_html_entities():
    # the Greek-blob class: receipts arrive HTML-entity-encoded; without
    # html.unescape the tokens come out as 'x3c4x3bf' escape fragments
    receipts = [
        {"headline": "&#x3A4;&#x3C1;&#x3B1;&#x3B3;&#x3C9;&#x3B4;&#x3AF;&#x3B1; Halkidiki crash", "country_code": "GR"},
        {"headline": "Covid cases surge in hospitals", "country_code": "GR"},
    ]
    lab = build_neutral_label(receipts)
    assert "x3c4" not in lab.lower() and "x3b1" not in lab.lower()
    assert "Halkidiki" in lab or "Covid" in lab or "cases" in lab


def test_build_neutral_label_drops_bare_numbers_and_dates():
    receipts = [
        {"headline": "2026 2026 World roundup 1500", "country_code": "US"},
        {"headline": "Election results tallied nationwide", "country_code": "US"},
    ]
    lab = build_neutral_label(receipts)
    assert "2026" not in lab and "1500" not in lab


def test_build_neutral_label_global_when_no_geo():
    receipts = [
        {"headline": "Markets mixed across regions today", "country_code": "XX"},
        {"headline": "Global roundup of financial reports", "country_code": None},
    ]
    assert build_neutral_label(receipts).startswith("Global:")


def test_fallback_sql_columns_match_live_schema():
    # 2026-07-18 general-review finding: the fallback SQL referenced
    # dtm.cluster_id (real column: emergent_cluster_id) — it crashed the court
    # on exactly the thin-substrate case it exists for, swallowed as non-fatal.
    # Freeze the column names against the migration files (no DB needed).
    from scripts.label_court import _RECEIPTS_FALLBACK_SQL
    assert "dtm.emergent_cluster_id" in _RECEIPTS_FALLBACK_SQL
    assert "dtm.cluster_id" not in _RECEIPTS_FALLBACK_SQL.replace("emergent_cluster_id", "")


# ---------------------------------------------------------------------------
# Lever B1 (2026-07-29): umbrella family lane — prompt builder + gating.
# ---------------------------------------------------------------------------

def _family(n_children=3, n_receipts=2):
    return [
        {"child_id": 100 + i, "child_label": f"Child Label {i}",
         "receipts": [{"headline": f"Child {i} headline {j}", "country_code": "GR"}
                      for j in range(n_receipts)]}
        for i in range(n_children)
    ]


def test_judge_prompt_family_includes_umbrella_and_child_labels_and_receipts():
    family = _family(n_children=2, n_receipts=2)
    prompt = _judge_prompt("Halkidiki Wildfire Family", [], family=True, family_children=family)
    assert 'FAMILY (UMBRELLA) LABEL: "Halkidiki Wildfire Family"' in prompt
    # every child's OWN label still appears (marked stale), not just a flat
    # headline pool — but demoted (2026-07-29 GB3): after its receipts.
    assert '(label, may be stale — do not treat as evidence): "Child Label 0"' in prompt
    assert '(label, may be stale — do not treat as evidence): "Child Label 1"' in prompt
    assert "Child 0 headline 0" in prompt
    assert "Child 1 headline 1" in prompt
    # the family question, not the single-headline-identity question
    assert "family" in prompt.lower()
    assert '"verdict": "entailed" | "partial" | "failed"' in prompt


def test_judge_prompt_family_receipts_precede_label_per_child_block():
    # GB3 (2026-07-29): the block used to lead with CHILD LABEL — the most
    # salient token the judge sees — so the judge kept dismissing on-topic
    # children by their stale label. Receipts must now appear BEFORE the
    # label in each child's block.
    family = _family(n_children=1, n_receipts=2)
    prompt = _judge_prompt("Umbrella", [], family=True, family_children=family)
    receipts_pos = prompt.index("RECEIPTS:")
    label_pos = prompt.index('(label, may be stale')
    assert receipts_pos < label_pos
    # the actual headline text must also physically precede the label marker
    headline_pos = prompt.index("Child 0 headline 0")
    assert headline_pos < label_pos


def test_judge_prompt_family_bounded_to_ten_children_three_receipts():
    # the fetch layer (_umbrella_family_for) enforces the ≤10×3 bound before
    # the prompt builder ever sees it; freeze the constants so a future edit
    # can't silently widen the trial's cost.
    assert _UMBRELLA_MAX_CHILDREN == 10
    assert _UMBRELLA_RECEIPTS_PER_CHILD == 3
    family = _family(n_children=_UMBRELLA_MAX_CHILDREN, n_receipts=_UMBRELLA_RECEIPTS_PER_CHILD)
    prompt = _judge_prompt("Umbrella", [], family=True, family_children=family)
    assert prompt.count("do not treat as evidence") == _UMBRELLA_MAX_CHILDREN
    for i in range(_UMBRELLA_MAX_CHILDREN):
        assert f"Child {i} headline {_UMBRELLA_RECEIPTS_PER_CHILD - 1}" in prompt


def test_judge_prompt_family_child_with_no_receipts_stays_visible():
    family = [{"child_id": 1, "child_label": "Thin Child", "receipts": []}]
    prompt = _judge_prompt("Umbrella", [], family=True, family_children=family)
    assert '(label, may be stale — do not treat as evidence): "Thin Child"' in prompt
    assert "no receipts" in prompt


def test_judge_prompt_family_falls_back_to_flat_receipts_without_children():
    # defensive: if family_children is None/empty, the prompt still renders
    # (never crashes) using the flat receipt list.
    receipts = [{"headline": "Some headline", "country_code": "GR"}]
    prompt = _judge_prompt("Umbrella", receipts, family=True, family_children=None)
    assert "Some headline" in prompt
    assert "HEADLINES:" in prompt


def test_judge_prompt_non_family_unaffected_by_family_children_param():
    # story-lane callers never pass family_children; make sure the default
    # doesn't leak into the ordinary single-topic question.
    receipts = [{"headline": "A headline", "country_code": "US"}]
    prompt = _judge_prompt("A Label", receipts, family=False)
    assert "FAMILY" not in prompt
    assert '"reason": "<one short sentence>"' in prompt


def test_flatten_family_receipts_dedupes_across_children():
    family = [
        {"child_id": 1, "child_label": "A", "receipts": [
            {"headline": "Shared headline text here", "country_code": "GR"}]},
        {"child_id": 2, "child_label": "B", "receipts": [
            {"headline": "Shared headline text here", "country_code": "GR"},
            {"headline": "Unique second headline", "country_code": "IT"}]},
    ]
    flat = _flatten_family_receipts(family)
    assert len(flat) == 2
    assert {r["headline"] for r in flat} == {"Shared headline text here", "Unique second headline"}


def test_flatten_family_receipts_empty_family_is_empty():
    assert _flatten_family_receipts([]) == []


def test_umbrella_clause_default_off_excludes_umbrellas():
    # the kill-switch default: umbrellas stay OUT of the trial until GB passes
    # and ATLAS_COURT_UMBRELLAS is flipped on.
    assert _umbrella_clause(only_umbrellas=False, umbrellas_enabled=False) == "AND is_umbrella = false "


def test_umbrella_clause_env_on_includes_both_lanes():
    assert _umbrella_clause(only_umbrellas=False, umbrellas_enabled=True) == ""


def test_umbrella_clause_only_umbrellas_wins_regardless_of_env():
    # --only-umbrellas is the scoped manual-run override; it must work even
    # when the cron gate is still off (it never touches the gate itself).
    assert _umbrella_clause(only_umbrellas=True, umbrellas_enabled=False) == "AND is_umbrella = true "
    assert _umbrella_clause(only_umbrellas=True, umbrellas_enabled=True) == "AND is_umbrella = true "


def test_child_labels_ranked_sql_schema_freeze():
    # schema-freeze (mirrors test_fallback_sql_columns_match_live_schema):
    # the family fetch must reference real dynamic_topics columns and stay
    # scoped to active, labeled children only, bounded by LIMIT $2.
    sql = _CHILD_LABELS_RANKED_SQL
    assert "parent_id = $1" in sql
    assert "state = 'active'" in sql
    assert "label IS NOT NULL" in sql
    assert "LIMIT $2" in sql
    assert "agg_n_signals DESC" in sql


# ---------------------------------------------------------------------------
# 2026-07-29 GB blind-check fallout: _RECEIPTS_SQL had no engine_version or
# quarantined filter — nightly-rebuilt unified-v2 topic_members rows (fresher
# timestamps) crowded served v1-compat evidence out of the per-child window,
# voiding all 36 umbrella verdicts (GB scored 3/10; see
# docs/research/label-court/2026-07-29-gb-blind-check.md). Freeze the fix so
# it can't silently regress: every receipts SQL that reads topic_members must
# scope to the SERVED engine_version and exclude quarantined rows.
# ---------------------------------------------------------------------------

def test_receipts_sql_scoped_to_served_engine_version_and_not_quarantined():
    sql = _RECEIPTS_SQL
    assert "topic_members" in sql
    # bound parameter, never a hardcoded literal — must track
    # topic_members_engine_version() / the eventual F4 cutover var, or the
    # court and the product can drift apart again.
    assert "tm.engine_version = $3" in sql
    assert "'v1-compat'" not in sql and '"v1-compat"' not in sql
    assert "tm.quarantined" in sql and "false" in sql.lower()
    assert "role = 'evidence'" in sql
    # ordered by SERVED-evidence freshness (assigned_at), not the signal's own
    # timestamp — the latter lets an experimental lane's nightly rebuild
    # crowd out served rows purely by refreshing its own timestamps.
    assert "max(tm.assigned_at)" in sql


def test_receipts_fallback_sql_has_no_topic_members_contamination_surface():
    # the emergent-sample fallback reads dynamic_topic_members/emergent_clusters,
    # never topic_members — no engine_version/quarantined column exists there,
    # so the contamination class this fix targets cannot occur on this path.
    # If a future edit repoints it at topic_members, it must gain the same
    # two filters and this assertion should flip.
    assert "topic_members" not in _RECEIPTS_FALLBACK_SQL.replace("dynamic_topic_members", "")


class _FakeConn:
    """Minimal asyncpg-shaped stub that records every fetch() call's SQL+args
    so we can assert the engine_version binding without touching a real DB."""

    def __init__(self, rows_by_sql=None):
        self.calls: list[tuple[str, tuple]] = []
        self._rows_by_sql = rows_by_sql or {}

    async def fetch(self, sql, *args):
        self.calls.append((sql, args))
        return self._rows_by_sql.get(sql, [])


def test_receipts_for_binds_engine_version_as_third_param(monkeypatch):
    monkeypatch.delenv("ATLAS_TOPIC_MEMBERS_ENGINE_VERSION", raising=False)
    conn = _FakeConn()
    asyncio.run(_receipts_for(conn, "dynamic-topic-1", 1, 8))
    assert conn.calls, "expected at least one fetch() call"
    sql, args = conn.calls[0]
    assert sql == _RECEIPTS_SQL
    assert args == ("dynamic-topic-1", 8, "v1-compat")
    assert args[-1] == topic_members_engine_version()


def test_receipts_for_falls_back_when_engine_version_scoped_query_is_empty():
    # if the served engine_version yields nothing (topic_members not yet
    # projected for this topic), the emergent-sample fallback still fires.
    conn = _FakeConn({_RECEIPTS_FALLBACK_SQL: [{"headline": "Fallback headline text", "country_code": "GR"}]})
    result = asyncio.run(_receipts_for(conn, "dynamic-topic-1", 1, 8))
    assert len(conn.calls) == 2
    assert result == [{"headline": "Fallback headline text", "country_code": "GR"}]


# ---------------------------------------------------------------------------
# 2026-07-29 GB2 (round 2) blind-check fallout: contamination was gone but the
# calibration scored 6/10. Three fixes — receipts-over-labels, generic-bucket
# honesty (bounded to not relax SPECIFIC labels), single-child skip.
# See docs/research/label-court/2026-07-29-gb2-blind-check.md.
# ---------------------------------------------------------------------------

def test_family_prompt_states_receipts_over_labels_rule():
    family = _family(n_children=1, n_receipts=1)
    prompt = _judge_prompt("Umbrella", [], family=True, family_children=family)
    low = prompt.lower()
    assert "receipts over labels" in low
    assert "stale" in low
    assert "judge by the receipts" in low or "judge by the\nreceipts" in low
    # the OLD (wrong-direction) instruction must be gone, not just supplemented
    assert "judge its label first" not in low


def test_family_prompt_states_generic_bucket_rule_with_named_examples():
    family = _family(n_children=1, n_receipts=1)
    prompt = _judge_prompt("Umbrella", [], family=True, family_children=family)
    low = prompt.lower()
    assert "generic bucket" in low
    assert "daily earthquake updates" in low
    assert "european heatwaves" in low
    assert "italy and uk" in low


def test_family_prompt_states_specific_label_still_needs_receipt_rule():
    # the caution GB2 named explicitly: rule 2 must not become blanket
    # lenience (dt-8193 "Heat Wave in Valencia" false-entailed over Spain-wide
    # alerts) — the specificity bar must survive alongside the generic-bucket
    # rule, in the same prompt.
    family = _family(n_children=1, n_receipts=1)
    prompt = _judge_prompt("Umbrella", [], family=True, family_children=family)
    low = prompt.lower()
    assert "specific labels still need a matching receipt" in low
    assert "rule 2 never" in low and "relax" in low


def test_family_prompt_all_three_rules_coexist_and_are_numbered():
    family = _family(n_children=2, n_receipts=2)
    prompt = _judge_prompt("Some Umbrella", [], family=True, family_children=family)
    assert "1. RECEIPTS OVER LABELS" in prompt
    assert "2. GENERIC BUCKETS ARE HONEST" in prompt
    assert "3. SPECIFIC LABELS STILL NEED A MATCHING RECEIPT" in prompt
    # ordering: rule 1 before rule 2 before rule 3
    assert prompt.index("1. RECEIPTS") < prompt.index("2. GENERIC") < prompt.index("3. SPECIFIC")


# ---------------------------------------------------------------------------
# 2026-07-29 GB3 (round 3) blind-check fallout: 7/10, one remaining mechanism
# (child label read as evidence of non-membership), zero false-entailments.
# See docs/research/label-court/2026-07-29-gb3-blind-check.md.
# ---------------------------------------------------------------------------

def test_family_prompt_states_compound_label_partial_trigger_rule():
    family = _family(n_children=1, n_receipts=1)
    prompt = _judge_prompt("Umbrella", [], family=True, family_children=family)
    assert "4. COMPOUND LABELS GET PARTIAL, NOT FAILED" in prompt
    assert prompt.index("3. SPECIFIC") < prompt.index("4. COMPOUND")
    low = prompt.lower()
    assert "partial" in low and "dominant" in low and "secondary clause" in low


def test_family_prompt_requires_verbatim_quoted_receipt_in_reason():
    family = _family(n_children=1, n_receipts=1)
    prompt = _judge_prompt("Umbrella", [], family=True, family_children=family)
    low = prompt.lower()
    assert "verbatim" in low and "quoted" in low
    assert "never from a child label" in low


# --- quote-gate: pure, DB-free behavior (mirrors the AI-read quote-gate) ---

_RECEIPTS_FIXTURE = [
    {"headline": "Trump defends his tariffs during Michigan visit", "country_code": "US"},
    {"headline": "Russians hit a foreign vessel with a drone in the Black Sea", "country_code": "UA"},
]


def test_reason_quotes_a_receipt_true_for_exact_verbatim_quote():
    reason = 'The label is supported: one receipt says "Trump defends his tariffs during Michigan visit".'
    assert _reason_quotes_a_receipt(reason, _RECEIPTS_FIXTURE) is True


def test_reason_quotes_a_receipt_true_for_curly_quotes():
    reason = 'It literally reads “Russians hit a foreign vessel with a drone in the Black Sea”.'
    assert _reason_quotes_a_receipt(reason, _RECEIPTS_FIXTURE) is True


def test_reason_quotes_a_receipt_true_for_partial_verbatim_excerpt():
    # a short exact substring of a receipt still grounds the reason
    reason = 'Confirmed by "defends his tariffs during Michigan visit".'
    assert _reason_quotes_a_receipt(reason, _RECEIPTS_FIXTURE) is True


def test_reason_quotes_a_receipt_false_when_no_quotes_at_all():
    # GB3's dt-8111 class: a fabricated absence with no quote to check
    reason = "None of the child story receipts mention a GM plant or a Michigan visit."
    assert _reason_quotes_a_receipt(reason, _RECEIPTS_FIXTURE) is False


def test_reason_quotes_a_receipt_false_when_quote_does_not_match_any_receipt():
    # a quoted string that isn't actually in any receipt (fabricated quote,
    # or a quoted CHILD LABEL instead of a receipt) must not pass
    reason = 'The children are about "Romania Demands Drone Reprogramming", unrelated to ships.'
    assert _reason_quotes_a_receipt(reason, _RECEIPTS_FIXTURE) is False


def test_reason_quotes_a_receipt_false_for_short_quoted_fragment():
    # too short to be a meaningful grounding quote (avoid trivial false-passes)
    reason = 'It says "US" somewhere.'
    assert _reason_quotes_a_receipt(reason, _RECEIPTS_FIXTURE) is False


def test_reason_quotes_a_receipt_tolerant_of_whitespace_and_case():
    reason = 'It reads: "TRUMP DEFENDS   his tariffs during michigan visit" per the wire.'
    assert _reason_quotes_a_receipt(reason, _RECEIPTS_FIXTURE) is True


def test_reason_quotes_a_receipt_true_for_single_quoted_receipt():
    # DeepSeek observed live reaching for single quotes around a receipt
    # excerpt (likely to dodge escaping receipts that contain double quotes)
    reason = ("All three receipts report the same event, e.g., 'Trump defends "
              "his tariffs during Michigan visit'.")
    assert _reason_quotes_a_receipt(reason, _RECEIPTS_FIXTURE) is True


def test_reason_quotes_a_receipt_ignores_leading_possessive_apostrophe():
    # regression: a naive single-quote regex mis-paired an EARLIER possessive
    # apostrophe ("child stories'") as the opening quote, swallowing the real
    # quote's start and missing the genuine grounding excerpt entirely — this
    # exact shape was observed live on dt-8130.
    reason = ("All three child stories' receipts report that Trump was there, "
              "e.g., 'Trump defends his tariffs during Michigan visit'.")
    assert _reason_quotes_a_receipt(reason, _RECEIPTS_FIXTURE) is True


def test_reason_quotes_a_receipt_false_for_possessives_only_no_real_quote():
    reason = "It's the world's biggest story about Trump's tariffs and Canada's response."
    assert _reason_quotes_a_receipt(reason, _RECEIPTS_FIXTURE) is False


def test_reason_quotes_a_receipt_tolerates_trailing_punctuation_inside_quote():
    # regression (observed live, dt-8130): the model closes a quote with a
    # trailing period INSIDE the quote marks that the receipt itself doesn't
    # carry — an American quote-punctuation habit, not a fabricated quote.
    reason = 'Confirmed: "Trump defends his tariffs during Michigan visit."'
    assert _reason_quotes_a_receipt(reason, _RECEIPTS_FIXTURE) is True


def test_reason_quotes_a_receipt_true_for_short_single_quoted_proper_noun():
    # regression (observed live, dt-8105): a naive 20-char floor on single
    # quotes rejected a genuine short quote ('Typhoon Noul') contrasting with
    # the label's unsupported claim ('Typhoon Bavi') — the lookaround already
    # disambiguates apostrophes from real quote marks, so a length floor this
    # low no longer needs to compensate.
    receipts = [{"headline": "Typhoon Noul makes landfall in the Philippines", "country_code": "PH"}]
    reason = "All receipts describe 'Typhoon Noul', not 'Typhoon Bavi' as the label claims."
    assert _reason_quotes_a_receipt(reason, receipts) is True


def test_withhold_clear_sql_nulls_all_four_court_columns():
    # "mark the verdict unchecked" (GB3) must be an ACTIVE reset keyed by id,
    # not a silent skip — otherwise a row that already carries a stale stamp
    # from an earlier pass keeps displaying it forever once a later pass
    # finds the reason ungrounded.
    sql = _WITHHOLD_CLEAR_SQL
    assert sql.startswith("UPDATE dynamic_topics SET")
    for col in ("label_status=NULL", "label_checked_at=NULL",
                "label_court_model=NULL", "label_proposed=NULL"):
        assert col in sql
    assert "WHERE id=$1" in sql


def test_single_child_skip_sql_excludes_umbrellas_with_one_child():
    sql = _SINGLE_CHILD_SKIP_SQL
    assert "is_umbrella = false OR" in sql
    assert ">= 2" in sql
    assert "c.state = 'active'" in sql
    assert "c.label IS NOT NULL" in sql
    assert "c.parent_id = dynamic_topics.id" in sql


def test_single_child_skip_sql_is_a_noop_shape_for_non_umbrella_rows():
    # the short-circuit `is_umbrella = false OR (...)` means a non-umbrella
    # row never even evaluates the correlated subquery — freeze the OR-first
    # ordering so this stays cheap and correct for the (much larger) story
    # lane population.
    sql = _SINGLE_CHILD_SKIP_SQL.strip()
    assert sql.startswith("AND (is_umbrella = false OR")


def test_single_child_cleanup_sql_nulls_all_four_court_columns():
    # invariant companion to the skip: a single-child umbrella judged BEFORE
    # this fix (e.g. GB2's dt-8193, false-entailed) must not keep a stale
    # verdict forever just because the skip now prevents re-judgment.
    sql = _SINGLE_CHILD_CLEANUP_SQL
    assert sql.startswith("UPDATE dynamic_topics SET")
    for col in ("label_status=NULL", "label_checked_at=NULL",
                "label_court_model=NULL", "label_proposed=NULL"):
        assert col in sql
    assert "is_umbrella = true" in sql
    assert "label_status IS NOT NULL" in sql  # no-op once already clean
    assert "< 2" in sql
