"""Count-basis contract for /api/v2/nodes.

Cold-user probe 2026-08-12 §4/§7 ("the single biggest hit to my confidence"):
Germany's country card read 4,840 signals/24h while the signal-density list on
the SAME view read 3,836. Measured on prod the same day, both came out of ONE
endpoint through TWO bases:

    /api/v2/nodes?hours=24                      -> source hourly_rollup   DE 3,836
    /api/v2/nodes?focus_type=country&...=DE     -> source signals_v2_focus DE 5,238

Same quantity (a country's signals in the window), different base. A country
focus needs no dimension the rollup lacks, so it serves the rollup base too and
the two numbers agree by construction. Theme/person/source focus genuinely
cannot: country_hourly_v2 has no theme, person or source dimension, so those
keep the raw scan -- and must SAY so rather than print a bare number.
"""
from __future__ import annotations

import pytest

from app.services.count_basis import (
    COUNT_BASIS_LABELS,
    describe_count_basis,
    nodes_count_basis,
)


class TestNodesCountBasis:
    def test_unfocused_nodes_count_over_the_hourly_rollup(self):
        assert nodes_count_basis(None) == "hourly_rollup"

    def test_country_focus_uses_the_same_rollup_base_as_the_map(self):
        # The fix: a country card and the density list twelve inches below it
        # are the same quantity, so they must not come from different tables.
        assert nodes_count_basis("country") == "hourly_rollup"

    @pytest.mark.parametrize("focus_type", ["theme", "person", "source"])
    def test_other_focus_types_keep_the_raw_scan(self, focus_type):
        # The rollup has no theme/person/source dimension -- these genuinely
        # cannot be served from it, so they stay raw and stay labeled.
        assert nodes_count_basis(focus_type) == "signals_v2_focus"

    def test_unknown_focus_type_falls_back_to_the_raw_scan(self):
        assert nodes_count_basis("wormhole") == "signals_v2_focus"

    def test_case_and_whitespace_do_not_change_the_base(self):
        assert nodes_count_basis("  Country ") == "hourly_rollup"


class TestDescribeCountBasis:
    def test_every_basis_has_a_short_label_and_a_reconciling_note(self):
        for basis in COUNT_BASIS_LABELS:
            d = describe_count_basis(basis)
            assert d["basis"] == basis
            assert d["label"], f"{basis} has no label"
            assert len(d["note"]) > 20, f"{basis} note is not explanatory"

    def test_rollup_note_names_the_aggregate_and_warns_it_can_trail_raw(self):
        note = describe_count_basis("hourly_rollup")["note"]
        assert "hourly" in note.lower()
        # A labeled divergence invites reconciliation; a mislabel forecloses it
        # (council R4 N19). The note must let a reader reconcile with /stats.
        assert "raw" in note.lower()

    def test_raw_focus_note_says_it_counts_raw_rows(self):
        note = describe_count_basis("signals_v2_focus")["note"]
        assert "raw" in note.lower()

    def test_unknown_basis_degrades_honestly_rather_than_inventing_a_label(self):
        d = describe_count_basis("something_new")
        assert d["basis"] == "something_new"
        assert d["label"] == "unknown basis"
        assert "not" in d["note"].lower() or "unknown" in d["note"].lower()
