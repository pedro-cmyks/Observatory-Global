"""Atlas Query Protocol slice 1 — the pure half.

Spec: `docs/superpowers/specs/2026-08-14-atlas-query-protocol-design.md`.

These tests freeze the CONTRACT RULES, which are the reason the protocol is
worth building at all:

  * every response carries its measured window, its population/basis, and what
    it could NOT measure;
  * a failed lane returns a NAMED reason, never a zero;
  * every verb is bounded by a measured cost ceiling and a row cap that is
    DECLARED in the response when it truncates.

The predicate spelling is load-bearing the same way `focus_lanes.PERSON_MATCH_EXPR`
is: `idx_signals_v2_headline_trgm` is a trigram GIN on `lower(headline)`, and a
trigram index only serves a predicate matching its expression character for
character. Measured on prod 2026-08-14: `lower(headline) LIKE '%espriella%'`
over a 24h window plans as a Bitmap Index Scan on that index, 324ms cold.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services import query_verbs as qv


# ------------------------------------------------------------------ needles

class TestNeedleSpelling:
    """The needle must match the indexed expression or the verb seq-scans
    1.1M rows — the N26 hang class, moved to a new endpoint."""

    def test_predicate_is_spelled_the_way_the_index_was_built(self):
        # idx_signals_v2_headline_trgm = GIN (lower(headline) gin_trgm_ops).
        # NOT f_unaccent(lower(headline)) — that is a DIFFERENT index
        # (idx_signals_headline_trgm) and cannot serve this predicate.
        assert qv.HEADLINE_MATCH_EXPR == "lower(headline) LIKE"

    def test_needle_is_lowercased_and_wrapped(self):
        assert qv.like_needle("Espriella") == "%espriella%"

    def test_like_metacharacters_are_escaped(self):
        # An unescaped % would silently match the entire corpus.
        assert qv.like_needle("100%") == r"%100\%%"
        assert qv.like_needle("a_b") == r"%a\_b%"

    def test_accents_are_preserved_because_the_index_does_not_fold_them(self):
        # The person predicate folds accents (mig 090 indexed f_unaccent).
        # This index does NOT, so folding here would silently miss rows.
        assert qv.like_needle("Golán") == "%golán%"


class TestTermRejectionIsNamedNeverSilent:
    """No-silent-filtering: a term we refuse to run is REPORTED, with why."""

    def test_short_terms_are_rejected_with_a_reason_not_dropped(self):
        needles, rejected = qv.normalize_terms(["espriella", "co"])
        assert needles == ["%espriella%"]
        assert rejected == [{"term": "co", "reason": "term_too_short",
                             "detail": "terms under 3 characters cannot use the "
                                       "trigram index and would scan the corpus"}]

    def test_blank_terms_are_rejected_with_a_reason(self):
        _, rejected = qv.normalize_terms(["   "])
        assert rejected[0]["reason"] == "term_empty"

    def test_terms_are_deduplicated_case_insensitively(self):
        needles, _ = qv.normalize_terms(["Golán", "golán"])
        assert needles == ["%golán%"]

    def test_all_terms_rejected_raises_named_verb_error(self):
        with pytest.raises(qv.VerbError) as exc:
            qv.normalize_terms(["a", "b"], require_one=True)
        assert exc.value.reason == "no_usable_terms"

    def test_term_count_is_capped_and_the_cap_is_reported(self):
        many = [f"term{i:03d}" for i in range(qv.MAX_TERMS + 3)]
        needles, rejected = qv.normalize_terms(many)
        assert len(needles) == qv.MAX_TERMS
        over = [r for r in rejected if r["reason"] == "term_cap_exceeded"]
        assert len(over) == 3


# ------------------------------------------------------------------- window

class TestWindowHonesty:
    """The window block is the difference between 'measured zero' and 'we
    cannot see that far back'. Hot retention measured 2026-08-14: the oldest
    signal was 2026-08-05, so a 14-day request can only be answered over ~9."""

    def _now(self):
        return datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)

    def test_window_fully_covered_when_retention_reaches_back_far_enough(self):
        w = qv.window_block(requested_hours=24, oldest_available=self._now() - timedelta(days=9),
                            now=self._now())
        assert w["fully_covered"] is True
        assert w["requested_hours"] == 24
        assert w["shortfall_hours"] == 0

    def test_window_declares_the_shortfall_when_the_request_outruns_retention(self):
        w = qv.window_block(requested_hours=24 * 14,
                            oldest_available=self._now() - timedelta(days=9),
                            now=self._now())
        assert w["fully_covered"] is False
        assert w["shortfall_hours"] == pytest.approx(24 * 5, abs=1)
        assert "hot corpus" in w["note"]

    def test_unknown_retention_is_reported_as_unknown_never_as_covered(self):
        w = qv.window_block(requested_hours=24, oldest_available=None, now=self._now())
        assert w["fully_covered"] is None
        assert w["note"]

    def test_window_carries_the_measured_bounds_not_only_the_request(self):
        w = qv.window_block(requested_hours=48, oldest_available=self._now() - timedelta(days=9),
                            now=self._now())
        assert w["measured_from"] == (self._now() - timedelta(hours=48)).isoformat()
        assert w["measured_to"] == self._now().isoformat()


# ----------------------------------------------------------------- envelope

class TestEnvelopeCarriesItsBase:
    def test_every_result_carries_basis_population_and_could_not_measure(self):
        r = qv.result_envelope(verb="receipt_geography", window={"requested_hours": 24},
                               population={"table": "topic_members"})
        assert r["basis"]["measured_over"] == "atlas_ingest"
        assert r["population"]["table"] == "topic_members"
        assert r["could_not_measure"] == []
        assert r["status"] == qv.STATUS_LIVE
        assert r["contract"] == qv.VERB_CONTRACT

    def test_degraded_result_names_its_reason_and_carries_no_data(self):
        r = qv.degraded_result("identities_covering", "db_busy",
                               window={"requested_hours": 24})
        assert r["status"] == qv.STATUS_DEGRADED
        assert r["reason"] == "db_busy"
        # The whole point: a degraded lane must not be readable as a zero.
        assert "data" not in r
        assert r["detail"]

    def test_truncation_is_declared_when_the_cap_bites(self):
        t = qv.truncation_block(returned=50, cap=50)
        assert t["truncated"] is True and t["cap"] == 50
        assert qv.truncation_block(returned=7, cap=50)["truncated"] is False


# -------------------------------------------------------------------- verbs

class TestVerbRegistry:
    def test_slice_one_ships_exactly_the_four_approved_verbs(self):
        assert qv.VERBS == frozenset({
            "identities_covering", "receipt_geography",
            "unclustered_signals", "voice_mix",
        })

    def test_unknown_verb_is_a_named_error(self):
        with pytest.raises(qv.VerbError) as exc:
            qv.validate_ask([{"nonexistent_verb": {}}])
        assert exc.value.reason == "unknown_verb"

    def test_composition_is_refused_with_a_named_reason_in_slice_one(self):
        # `$1` chaining is explicitly the NEXT slice. Refusing it loudly beats
        # silently treating the reference as a literal string.
        with pytest.raises(qv.VerbError) as exc:
            qv.validate_ask([{"receipt_geography": {"topic_id": "$1"}}])
        assert exc.value.reason == "composition_not_supported"

    def test_ask_length_is_capped(self):
        ask = [{"voice_mix": {"country": "CO"}}] * (qv.MAX_VERBS_PER_REQUEST + 1)
        with pytest.raises(qv.VerbError) as exc:
            qv.validate_ask(ask)
        assert exc.value.reason == "too_many_verbs"

    def test_empty_ask_is_a_named_error(self):
        with pytest.raises(qv.VerbError) as exc:
            qv.validate_ask([])
        assert exc.value.reason == "empty_ask"


class TestTopicRefParsing:
    def test_accepts_bare_numeric_id_and_normalizes_to_member_key(self):
        assert qv.parse_topic_ref("12927") == ("dynamic-topic-12927", 12927)

    def test_accepts_the_full_member_key(self):
        assert qv.parse_topic_ref("dynamic-topic-12927") == ("dynamic-topic-12927", 12927)

    def test_accepts_dt_shorthand_used_throughout_the_research_docs(self):
        assert qv.parse_topic_ref("dt-12927") == ("dynamic-topic-12927", 12927)

    def test_atlas_slug_keeps_its_key_and_has_no_numeric_id(self):
        assert qv.parse_topic_ref("armed-conflict-escalation") == (
            "armed-conflict-escalation", None)

    def test_rejects_empty_ref_with_a_named_reason(self):
        with pytest.raises(qv.VerbError) as exc:
            qv.parse_topic_ref("")
        assert exc.value.reason == "missing_topic_id"


class TestVoiceMixScopeValidation:
    def test_requires_exactly_one_of_topic_id_or_country(self):
        with pytest.raises(qv.VerbError) as exc:
            qv.validate_voice_mix_scope({})
        assert exc.value.reason == "missing_scope"
        with pytest.raises(qv.VerbError) as exc:
            qv.validate_voice_mix_scope({"topic_id": "dt-1", "country": "CO"})
        assert exc.value.reason == "ambiguous_scope"

    def test_country_is_normalized_upper(self):
        assert qv.validate_voice_mix_scope({"country": "co"}) == ("country", "CO")

    def test_rejects_malformed_country_code(self):
        with pytest.raises(qv.VerbError) as exc:
            qv.validate_voice_mix_scope({"country": "COL"})
        assert exc.value.reason == "bad_country_code"


# --------------------------------------------------------------------- SQL

class TestSqlBuilders:
    """The SQL is built here (pure) so the shape is test-pinned without a DB."""

    def test_term_predicate_ors_the_needles_and_parameterizes_them(self):
        sql, params = qv.term_predicate(["%a%", "%b%"], start_index=2)
        assert sql == "(lower(headline) LIKE $2 OR lower(headline) LIKE $3)"
        assert params == ["%a%", "%b%"]

    def test_member_lane_reads_the_same_engine_version_serving_reads(self):
        # Parity by construction: if F4 flips serving to unified-v2, the
        # protocol follows in the same breath, because both call the same
        # resolver. Two different lanes would make the double-check a lie.
        sql, _ = qv.identities_covering_member_sql(["%x%"], country=None, hours=24)
        assert "engine_version = " in sql
        assert "role = 'evidence'" in sql

    def test_every_row_returning_lane_carries_a_limit(self):
        for sql, _ in (
            qv.identities_covering_member_sql(["%x%"], country=None, hours=24),
            qv.identities_covering_label_sql(["%x%"], country=None),
            qv.unclustered_landing_sql(["%x%"], hours=24),
            qv.receipt_geography_sql("dynamic-topic-1", dimension="country_code"),
        ):
            assert "LIMIT" in sql.upper(), sql

    def test_country_scope_is_parameterized_not_interpolated(self):
        sql, params = qv.identities_covering_member_sql(["%x%"], country="CO", hours=24)
        assert "'CO'" not in sql
        assert "CO" in params
