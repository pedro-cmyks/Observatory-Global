"""Label Court pure-logic: verdict parsing + neutral-label building."""
import asyncio

from scripts.label_court import (
    parse_verdict, build_neutral_label, _dominant_geo,
    _judge_prompt, _flatten_family_receipts, _umbrella_clause,
    _CHILD_LABELS_RANKED_SQL, _UMBRELLA_MAX_CHILDREN, _UMBRELLA_RECEIPTS_PER_CHILD,
    _RECEIPTS_SQL, _RECEIPTS_FALLBACK_SQL, _receipts_for, topic_members_engine_version,
    _SINGLE_CHILD_SKIP_SQL, _SINGLE_CHILD_CLEANUP_SQL, _reason_quotes_a_receipt,
    _WITHHOLD_MARK_SQL, _WITHHELD_COURT_MODEL, _absence_claim_contradicted,
    _rule4_majority_satisfied, _COURT_MODEL, _rule4_named_children_verified,
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


def test_judge_prompt_family_children_are_numbered_for_rule4_citation():
    # GB5 Class D' fix: the model must be able to CITE which children
    # support a compound label's dominant clause; each block is now labeled
    # with a stable 1-based index it can name in "(children: 1,2,3)".
    family = _family(n_children=3, n_receipts=1)
    prompt = _judge_prompt("Umbrella", [], family=True, family_children=family)
    for i in range(1, 4):
        assert f"CHILD {i}:" in prompt
    # numbering must precede that child's own receipts/label content
    assert prompt.index("CHILD 1:") < prompt.index("Child 0 headline 0")


def test_judge_prompt_rule4_text_requires_named_children_tail():
    family = _family(n_children=2, n_receipts=1)
    prompt = _judge_prompt("Umbrella", [], family=True, family_children=family)
    low = prompt.lower()
    assert "name the children" in low
    assert "(children: 1,2,3)" in prompt or "(children:" in prompt


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


# ---------------------------------------------------------------------------
# 2026-07-29 GB4 blind-check fallout: GB3's withhold cleared ALL FOUR court
# columns unconditionally, erasing dt-8084's CORRECT prior `failed` stamp
# once a later pass found its reasoning ungrounded. See
# docs/research/label-court/2026-07-29-gb4-blind-check.md.
# ---------------------------------------------------------------------------

def test_withhold_mark_sql_never_touches_label_status():
    # the fix: label_status is not in the SET list at all — a withheld
    # attempt can only ever mark checked_at/court_model, never the verdict
    # column, so a prior valid stamp is structurally impossible to erase.
    sql = _WITHHOLD_MARK_SQL
    assert sql.startswith("UPDATE dynamic_topics SET")
    assert "label_status" not in sql.split("WHERE")[0]  # not in the SET clause
    assert "label_checked_at=$2" in sql
    assert "label_court_model=$3" in sql


def test_withhold_mark_sql_scoped_to_rows_with_no_prior_stamp():
    # the WHERE clause is what actually preserves a valid stamp: a row that
    # already has entailed/partial/failed is excluded from this UPDATE
    # entirely, so it survives byte-identical.
    sql = _WITHHOLD_MARK_SQL
    assert "WHERE id=$1 AND label_status IS NULL" in sql


def test_withheld_court_model_is_distinguishable_from_the_ordinary_model():
    # durable DB-level signal ("attempted, could not ground") distinct from
    # "never reached" (label_checked_at IS NULL) — without needing a new
    # label_status value (migration 080's CHECK constraint forbids one
    # outside entailed/partial/failed/NULL; widening it is out of this fix's
    # scope, see the module docstring).
    assert _WITHHELD_COURT_MODEL != _COURT_MODEL
    assert _WITHHELD_COURT_MODEL.startswith(_COURT_MODEL)
    assert "withheld" in _WITHHELD_COURT_MODEL.lower()


# --- GB4 fix 4: absence-claim contradiction (class B, third attempt) -------

def test_absence_claim_contradicted_true_for_witness_dt_8175():
    # the exact GB4 witness: the reason claims $91 is absent while an Arabic-
    # script receipt reports it verbatim in plain Western digits.
    receipts = [
        {"headline": "أسعار النفط تنخفض بأكثر من 5% إلى 91 دولارا للبرميل بعد توقف الضربات الأمريكية على إيران",
         "country_code": "AE"},
        {"headline": "Trump vows to punish Iran, oil surges over $100", "country_code": "US"},
    ]
    reason = ('The label is contradicted: no receipt anywhere reports oil dropping '
             'to $91 or any easing of tensions — the receipts instead describe '
             'ongoing US strikes and Iranian warnings.')
    assert _absence_claim_contradicted(reason, receipts) is True


def test_absence_claim_contradicted_false_when_absence_is_genuine():
    receipts = [{"headline": "Oil prices climb amid Middle East tensions", "country_code": "US"}]
    reason = "No receipt anywhere reports a specific $91 figure, so the claim is unsupported."
    assert _absence_claim_contradicted(reason, receipts) is False


def test_absence_claim_contradicted_false_without_an_absence_trigger():
    # a bare number in an otherwise ordinary reason is not itself suspicious
    receipts = [{"headline": "Oil falls to $91 a barrel", "country_code": "US"}]
    reason = "The family is entailed: receipts confirm oil at $91 a barrel."
    assert _absence_claim_contradicted(reason, receipts) is False


def test_absence_claim_contradicted_does_not_false_positive_on_larger_numbers():
    # "91" must not match inside "1991" or "919" — word-boundary-ish digit match
    receipts = [{"headline": "Founded in 1991, the agency reports 919 cases", "country_code": "US"}]
    reason = "No receipt mentions 91 as a standalone figure."
    assert _absence_claim_contradicted(reason, receipts) is False


def test_absence_claim_contradicted_false_for_single_digit_targets():
    # a bare single digit near an absence trigger is too common to be
    # meaningful (avoid trivial false-positives on "no receipt mentions 5 ...")
    receipts = [{"headline": "5 dead in the incident", "country_code": "US"}]
    reason = "No receipt mentions 5 witnesses being interviewed."
    assert _absence_claim_contradicted(reason, receipts) is False


def test_absence_claim_contradicted_ignores_bare_years_far_from_the_trigger():
    # regression (observed live, dt-8177): a long, comma-spliced reason had
    # "no receipt mentions 'Pageants'" near the START and an unrelated
    # "China Open 2026" clause LATER in the same period-delimited sentence —
    # "2026" spuriously matched as a "contradicted absence target" purely
    # because every receipt is dated 2026. The proximity window (scanning
    # only right after the trigger) and the bare-year exclusion both guard
    # against this.
    receipts = [
        {"headline": "Ana/Trias terhenti di babak pertama China Open 2026", "country_code": "ID"},
        {"headline": "El gol de Ferran Torres hizo vibrar España", "country_code": "ES"},
    ]
    reason = ("The umbrella label is not supported: no receipt mentions 'Pageants' at all, "
             "and the fourth child's receipts are about badminton at the China Open 2026, "
             "which is not a FIFA or pageant event.")
    assert _absence_claim_contradicted(reason, receipts) is False


def test_absence_claim_contradicted_still_catches_a_currency_figure_disguised_as_a_year():
    # the year exclusion is narrow: a $-marked or %-marked figure that
    # happens to look like a year is still a real target.
    receipts = [{"headline": "Damages estimated at $2026 million", "country_code": "US"}]
    reason = "No receipt mentions damages of $2026 million anywhere in the family."
    assert _absence_claim_contradicted(reason, receipts) is True


# --- GB5 Class B, fourth attempt: TEXTUAL absence targets -------------------

def test_absence_claim_contradicted_true_for_witness_dt_8241():
    # the exact GB5 witness: "drones" is Latin-script inside Greek prose —
    # the reason claims the drone-attack clause is unsupported while a
    # receipt reports it verbatim.
    receipts = [
        {"headline": "Ιράν: Ο στρατός επιτέθηκε στο Μπαχρέιν και στην Ιορδανία με drones",
         "country_code": "GR"},
        {"headline": "Αράκτσι υπόσχεται απάντηση στο Ζελένσκι", "country_code": "GR"},
    ]
    reason = ("No receipt mentions 'drone attacks' or 'threats' by Iran that escalate "
             "tensions; the receipts describe AI-generated images of Trump, a war cost "
             "figure, and unrelated claims about Ukraine.")
    assert _absence_claim_contradicted(reason, receipts) is True


def test_absence_claim_contradicted_false_when_textual_absence_is_genuine():
    receipts = [{"headline": "Iran announces new oil export figures", "country_code": "IR"}]
    reason = "No receipt mentions 'drone attacks' by Iran anywhere in the family."
    assert _absence_claim_contradicted(reason, receipts) is False


def test_absence_claim_contradicted_textual_check_is_case_insensitive():
    receipts = [{"headline": "DRONES strike energy infrastructure", "country_code": "UA"}]
    reason = "No receipt mentions 'drones' anywhere in the family."
    assert _absence_claim_contradicted(reason, receipts) is True


def test_absence_claim_contradicted_textual_check_ignores_court_vocabulary():
    # quoted words that are the court's OWN reasoning vocabulary (not a real
    # target) must not self-trigger even though they'd trivially match any
    # reason that also uses them, or a receipt that happens to share them.
    receipts = [{"headline": "The family filed a claim about the umbrella label",
                "country_code": "US"}]
    reason = "No receipt mentions 'the claim' or 'this family' anywhere."
    assert _absence_claim_contradicted(reason, receipts) is False


def test_absence_claim_contradicted_textual_check_ignores_short_words():
    receipts = [{"headline": "A war over oil and gas", "country_code": "US"}]
    reason = "No receipt mentions 'war' anywhere in the family."
    # "war" is only 3 letters — below the >=4 floor, avoid trivial noise
    assert _absence_claim_contradicted(reason, receipts) is False


def test_absence_claim_contradicted_textual_check_respects_proximity_window():
    # a quoted phrase far from the trigger (well past the 80-char window,
    # in an unrelated later clause) must not be treated as the claim target —
    # mirrors the "China Open 2026" numeric lesson, extended to text.
    receipts = [{"headline": "Drone factory opens in Kharkiv", "country_code": "UA"}]
    reason = ("No receipt supports the claim, since the family instead covers tariffs, "
             "trade disputes, diplomatic meetings, and separately a child labeled "
             "'drone factory' that is unrelated to this specific umbrella.")
    assert _absence_claim_contradicted(reason, receipts) is False


# --- GB4 fix 3: rule 4 numeric majority enforcement -------------------------

def test_rule4_majority_satisfied_true_for_strict_majority():
    assert _rule4_majority_satisfied("6/7 children support the wildfire clause.") is True
    assert _rule4_majority_satisfied("Supported by 3 of 4 children.") is True


def test_rule4_majority_satisfied_false_for_tie_or_minority():
    # the exact GB4 witness: dt-5549 earned `partial` on a stated 4/8 tie
    assert _rule4_majority_satisfied("The sanctions clause reaches 4/8 children.") is False
    assert _rule4_majority_satisfied("Only 2 of 8 children support this claim.") is False


def test_rule4_majority_satisfied_none_when_no_count_is_stated():
    # rule 4 REQUIRES the count to be stated — an absent count is itself a
    # defect (silently trusting an un-quantified "majority" claim is exactly
    # how dt-5549 slipped through), not something to silently pass.
    assert _rule4_majority_satisfied("Most children support the dominant clause.") is None


def test_rule4_majority_satisfied_ignores_nonsensical_counts():
    # defensive: a count where the numerator exceeds the denominator (a
    # malformed or hallucinated fraction) is treated as no-count-stated.
    assert _rule4_majority_satisfied("9 of 4 children support this.") is None


# --- GB5 Class D' fix: rule 4's stated count must be named + consistent ----

def test_rule4_named_children_true_when_count_and_list_agree():
    reason = "6/7 children (children: 1,2,3,4,6,7) support the wildfire clause."
    assert _rule4_named_children_verified(reason, n_children_total=7) is True


def test_rule4_named_children_witness_dt_8237_fabricated_count():
    # the exact GB5 witness: "3/4" stated, but only ONE child is actually
    # named as supporting — the count and the list disagree.
    reason = "3/4 children (children: 1) support the 'Ukraine Aid Delayed' clause."
    assert _rule4_named_children_verified(reason, n_children_total=4) is False


def test_rule4_named_children_none_when_no_list_given():
    # rule 4 now REQUIRES the named list — an absent one is itself a defect,
    # mirroring _rule4_majority_satisfied's contract for an absent fraction.
    reason = "6/7 children support the wildfire clause."
    assert _rule4_named_children_verified(reason, n_children_total=7) is None


def test_rule4_named_children_false_for_out_of_range_index():
    # a named child number outside the family is a hallucinated reference
    reason = "2/3 children (children: 1,9) support the clause."
    assert _rule4_named_children_verified(reason, n_children_total=3) is False


def test_rule4_named_children_false_for_duplicate_indices_padding_the_count():
    # listing the same child twice to reach the stated N must not pass —
    # DISTINCT indices are what's compared against N
    reason = "3/5 children (children: 1,1,2) support the clause."
    assert _rule4_named_children_verified(reason, n_children_total=5) is False


def test_rule4_named_children_none_without_a_fraction_at_all():
    assert _rule4_named_children_verified("Most children agree.", n_children_total=5) is None


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


def test_unchecked_backoff_sql_rests_fresh_withholds():
    # 2026-07-30 withhold-loop fix: dt-8258/8228 were re-judged every 33-min
    # cycle (23 identical `ungrounded` trials in a day) because a withheld row
    # keeps label_status NULL. Fresh withholds must rest before retry.
    from scripts.label_court import _UNCHECKED_BACKOFF_SQL
    sql = _UNCHECKED_BACKOFF_SQL
    assert "label_status IS NULL" in sql
    assert "NOT LIKE '%#withheld'" in sql
    assert "interval '6 hours'" in sql


def test_unchecked_backoff_sql_is_null_safe_for_never_checked_rows():
    # Three-valued-logic regression guard: the clause must be an OR chain
    # whose first branch is `label_court_model IS NULL`. The rejected form
    # `NOT (model LIKE ... AND checked_at > ...)` evaluates to NULL for a
    # never-checked row (both columns NULL) and WHERE drops it — which would
    # silently exclude every NEW topic from the court forever.
    from scripts.label_court import _UNCHECKED_BACKOFF_SQL
    sql = _UNCHECKED_BACKOFF_SQL
    assert "label_court_model IS NULL" in sql
    assert "NOT (" not in sql
    # the aged-withhold re-entry branch uses <= (rested), not > (fresh)
    assert "label_checked_at <= now()" in sql


def test_trial_population_includes_revived_candidates_actives_first():
    # TF-3b: revived candidates (revived_at set by the v2b clock) must enter
    # the trial so their court-gated promotion can ever clear; actives keep
    # priority in the ORDER BY so serving rows never wait behind revivals.
    import inspect
    import scripts.label_court as lc
    src = inspect.getsource(lc.main)
    assert "state='candidate' AND revived_at IS NOT NULL" in src
    assert "(state='active') DESC" in src


def test_trial_candidate_arm_requires_null_status_no_retrial_burn():
    # TF-3b finding-3 guard: a court-failed revived candidate belongs to the
    # RELABEL lane; the nightly full court must not re-judge its frozen
    # receipts forever. The candidate arm gates on label_status IS NULL in
    # BOTH modes (relabel resets the status, which re-enters it here).
    import inspect
    import scripts.label_court as lc
    src = inspect.getsource(lc.main)
    assert "state='candidate' AND revived_at IS NOT NULL " in src
    assert "AND label_status IS NULL))" in src


# ---------------------------------------------------------------------------
# 2026-08-03 #261 item 3: the `too_broad` verdict (mega-topic fusion named,
# not folded into `failed`) + stratified receipt sampling (env-gated OFF).
# ---------------------------------------------------------------------------
from scripts.label_court import (  # noqa: E402
    _MARKS, _VALID, _RECEIPTS_STRATIFIED_SQL, stratified_receipts_enabled,
)


def test_parse_verdict_too_broad_json_and_separator_drift():
    assert parse_verdict('{"verdict": "too_broad", "reason": "three unrelated stories"}')[0] == "too_broad"
    # models paraphrase compound enum values — space/hyphen forms normalize
    assert parse_verdict('{"verdict": "too broad", "reason": "fusion"}')[0] == "too_broad"
    assert parse_verdict('{"verdict": "too-broad", "reason": "fusion"}')[0] == "too_broad"


def test_parse_verdict_too_broad_bare_prose_wins_over_embedded_failed():
    # unparseable prose mentioning both: the compound (most specific) term wins
    v, _ = parse_verdict("this label failed because the cluster is TOO BROAD")
    assert v == "too_broad"


def test_marks_cover_every_valid_verdict():
    # the print path indexes _MARKS[verdict] — a vocabulary word without a mark
    # would crash the cron mid-run
    assert set(_MARKS) == set(_VALID)


def test_stratified_receipts_env_gated_default_off(monkeypatch):
    monkeypatch.delenv("ATLAS_COURT_STRATIFIED_RECEIPTS", raising=False)
    assert stratified_receipts_enabled() is False
    conn = _FakeConn()
    asyncio.run(_receipts_for(conn, "dynamic-topic-1", 1, 8))
    assert conn.calls[0][0] == _RECEIPTS_SQL


def test_stratified_receipts_env_on_switches_sql_same_binds(monkeypatch):
    monkeypatch.delenv("ATLAS_TOPIC_MEMBERS_ENGINE_VERSION", raising=False)
    monkeypatch.setenv("ATLAS_COURT_STRATIFIED_RECEIPTS", "on")
    conn = _FakeConn()
    asyncio.run(_receipts_for(conn, "dynamic-topic-1", 1, 8))
    sql, args = conn.calls[0]
    assert sql == _RECEIPTS_STRATIFIED_SQL
    assert args == ("dynamic-topic-1", 8, "v1-compat")


def test_stratified_sql_keeps_the_contamination_filters():
    # the 2026-07-29 contamination fix must hold on BOTH receipt queries:
    # served engine_version bind, quarantined exclusion, evidence role,
    # assigned_at ordering (never s.timestamp)
    assert "tm.engine_version = $3" in _RECEIPTS_STRATIFIED_SQL
    assert "COALESCE(tm.quarantined, false) = false" in _RECEIPTS_STRATIFIED_SQL
    assert "tm.role = 'evidence'" in _RECEIPTS_STRATIFIED_SQL
    assert "NTILE($2)" in _RECEIPTS_STRATIFIED_SQL
    assert "s.timestamp" not in _RECEIPTS_STRATIFIED_SQL


def test_story_prompt_offers_too_broad_family_prompt_does_not():
    story = _judge_prompt("Some Label", [{"headline": "h1", "country_code": "US"},
                                         {"headline": "h2", "country_code": "FR"}])
    assert "too_broad" in story
    # the GB-calibrated family lane keeps its three-verdict vocabulary
    family = _judge_prompt("Family Label", [{"headline": "h1", "country_code": "US"}],
                           family=True,
                           family_children=[{"child_id": 1, "child_label": "c1",
                                             "receipts": [{"headline": "h1", "country_code": "US"}]}])
    assert "too_broad" not in family
