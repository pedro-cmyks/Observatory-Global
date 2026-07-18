"""Label-fold pre-pass guardrails (Lane B — the 15x Venezuela problem).

The fold must collapse literal/near-literal duplicate labels (9x "Venezuela
Earthquake Death Toll") WITHOUT merging same-theme-different-event labels —
that judgment stays with the LLM same-event judge.
"""
from app.services.label_fold import (
    label_fold_groups,
    merge_index_groups,
    normalize_label_tokens,
)


class TestNormalizeLabelTokens:
    def test_basic_tokenize_lower(self):
        assert normalize_label_tokens("Venezuela Earthquake Death Toll") == {
            "venezuela", "earthquake", "death", "toll"
        }

    def test_digits_and_dates_dropped(self):
        toks = normalize_label_tokens("World Cup 2026 Updates")
        assert "2026" not in toks
        assert toks == {"world", "cup", "updates"}

    def test_stopwords_dropped(self):
        assert normalize_label_tokens("Terremotos en Venezuela") == {
            "terremotos", "venezuela"
        }

    def test_emerging_prefix_stripped(self):
        toks = normalize_label_tokens("Emerging: Peste bovine outbreak")
        assert "emerging" not in toks
        assert "peste" in toks

    def test_placeholder_labels_do_not_participate(self):
        assert normalize_label_tokens("(label failed)") == frozenset()
        assert normalize_label_tokens("") == frozenset()
        assert normalize_label_tokens(None) == frozenset()

    def test_html_entities_unescaped(self):
        toks = normalize_label_tokens("S&amp;P Downgrade Alert")
        assert "amp" not in toks

    def test_non_latin_scripts_tokenize(self):
        toks = normalize_label_tokens("ЧМ-2026 Четвертьфиналисты")
        assert "четвертьфиналисты" in toks
        assert not any(ch.isdigit() for t in toks for ch in t)


class TestLabelFoldGroups:
    def test_exact_duplicates_fold(self):
        labels = ["Venezuela Earthquake Death Toll"] * 9 + ["Ukraine War Escalation"]
        groups = label_fold_groups(labels)
        assert len(groups) == 1
        assert groups[0] == list(range(9))  # the 9 dups, Ukraine untouched

    def test_same_theme_different_wording_does_not_fold(self):
        # Jaccard({venezuela,earthquake,death,toll},{venezuela,earthquake,tragedy})
        # = 2/5 = 0.4 < 0.8 — the judge's job, not the fold's.
        labels = [
            "Venezuela Earthquake Death Toll",
            "Venezuela Earthquake Tragedy",
            "Venezuela Earthquake Disaster",
        ]
        assert label_fold_groups(labels) == {}

    def test_near_duplicate_above_threshold_folds(self):
        # {world,cup,matches} vs {world,cup,matches,live} = 3/4 = 0.75 < 0.8: no.
        # Identical after date-strip: yes.
        labels = ["World Cup 2026 Matches", "World Cup 2027 Matches"]
        groups = label_fold_groups(labels)
        assert groups == {0: [0, 1]}

    def test_placeholder_labels_never_fold_together(self):
        labels = ["(label failed)", "(label failed)", "(label failed)"]
        assert label_fold_groups(labels) == {}

    def test_emerging_marker_does_not_connect_unrelated(self):
        labels = [
            "Emerging: Tour de France crash chaos",
            "Emerging: Merchantwise acquisition deal",
        ]
        assert label_fold_groups(labels) == {}

    def test_short_labels_excluded(self):
        # < 2 event-bearing tokens cannot participate (one token would fold
        # every "Venezuela ..." label into one blob).
        labels = ["Venezuela", "Venezuela", "Venezuela Earthquake Death Toll"]
        assert label_fold_groups(labels) == {}

    def test_complete_linkage_no_chaining(self):
        # A and B identical; C shares enough with B (subset) but not with A?
        # With Jaccard on sets, construct: A={a,b,c,d,e}, B={a,b,c,d}, C={a,b,c}.
        # A-B = 4/5 = 0.8 edge; B-C = 3/4 = 0.75 no edge; A-C = 3/5 = 0.6 no.
        labels = [
            "alpha bravo charlie delta echo",
            "alpha bravo charlie delta",
            "alpha bravo charlie",
        ]
        groups = label_fold_groups(labels)
        assert groups == {0: [0, 1]}  # C never chains in

    def test_multiple_independent_groups(self):
        labels = [
            "Venezuela Earthquake Death Toll",
            "Venezuela Earthquake Death Toll",
            "Lindsey Graham Dies at Age",
            "Lindsey Graham Dies at Age",
            "Iran Strikes Update",
        ]
        groups = label_fold_groups(labels)
        assert groups == {0: [0, 1], 2: [2, 3]}


class TestMergeIndexGroups:
    def test_disjoint_groups_pass_through(self):
        merged = merge_index_groups(6, {0: [0, 1]}, {2: [2, 3]})
        assert merged == {0: [0, 1], 2: [2, 3]}

    def test_overlapping_groups_union(self):
        # label fold says {0,1}; judge says {1,2} — one event through topic 1.
        merged = merge_index_groups(4, {0: [0, 1]}, {1: [1, 2]})
        assert merged == {0: [0, 1, 2]}

    def test_empty_secondary_keeps_primary(self):
        assert merge_index_groups(3, {0: [0, 2]}, {}) == {0: [0, 2]}

    def test_singletons_never_emitted(self):
        merged = merge_index_groups(5, {0: [0, 1]}, {})
        assert all(len(v) >= 2 for v in merged.values())
        assert 4 not in merged
