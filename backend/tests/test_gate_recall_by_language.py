"""Pure-logic tests for the gate keep-rate-by-language report (no DB)."""

import json

from scripts.gate_recall_by_language import (
    build_report,
    enrich_counts,
    flag_bias,
)


def _lang(lang, scored, kept):
    return enrich_counts(
        {"lang": lang, "assignments": scored, "scored": scored, "kept": kept,
         "abstained": scored - kept, "unscored": 0}
    )


def test_keep_rate_of_scored_computed():
    row = _lang("es", scored=100, kept=40)
    assert row["kept_rate_of_scored"] == 0.4


def test_bias_flagged_when_deficit_over_threshold_and_enough_rows():
    rows = [_lang("en", 200, 180), _lang("es", 100, 40)]  # en .90 vs es .40
    out = flag_bias(rows)
    es = next(r for r in out if r["lang"] == "es")
    assert es["keep_rate_deficit_vs_baseline"] == 0.5
    assert es["language_bias_suspected"] is True


def test_baseline_never_flags_itself():
    rows = [_lang("en", 200, 180), _lang("es", 100, 40)]
    out = flag_bias(rows)
    en = next(r for r in out if r["lang"] == "en")
    assert en["language_bias_suspected"] is False
    assert en["keep_rate_deficit_vs_baseline"] == 0.0


def test_thin_language_not_flagged_even_with_deficit():
    rows = [_lang("en", 200, 180), _lang("fa", 10, 0)]  # huge deficit but <30 scored
    out = flag_bias(rows)
    fa = next(r for r in out if r["lang"] == "fa")
    assert fa["language_bias_suspected"] is False


def test_small_deficit_not_flagged():
    rows = [_lang("en", 200, 180), _lang("pt", 100, 85)]  # .90 vs .85, deficit .05
    out = flag_bias(rows)
    pt = next(r for r in out if r["lang"] == "pt")
    assert pt["language_bias_suspected"] is False


def test_no_baseline_means_no_deficit():
    rows = [_lang("es", 100, 40), _lang("pt", 100, 50)]  # no 'en' row
    out = flag_bias(rows)
    assert all(r["keep_rate_deficit_vs_baseline"] is None for r in out)
    assert all(r["language_bias_suspected"] is False for r in out)


def test_build_report_shape_and_flagged_list():
    db_row = {
        "overall": json.dumps(
            {"assignments": 300, "scored": 300, "kept": 220,
             "abstained": 80, "unscored": 0}
        ),
        "by_lang": json.dumps(
            [
                {"lang": "en", "assignments": 200, "scored": 200, "kept": 180,
                 "abstained": 20, "unscored": 0, "distinct_signals": 200},
                {"lang": "es", "assignments": 100, "scored": 100, "kept": 40,
                 "abstained": 60, "unscored": 0, "distinct_signals": 100},
            ]
        ),
    }
    report = build_report(hours=168, db_row=db_row)
    assert report["schema_version"] == "atlas-gate-recall-by-language-v1"
    assert report["overall"]["kept_rate_of_scored"] == round(220 / 300, 4)
    assert report["languages_with_suspected_bias"] == ["es"]
