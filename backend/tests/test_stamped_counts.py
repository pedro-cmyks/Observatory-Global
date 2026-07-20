"""N15 fold-coverage observability: /threads meta.stamped_counts.

The council found the Label Court does not cover the fold (31/37 served
threads unstamped incl. ALL leads). stamped_counts makes that measurable PER
REQUEST: a cheap census of the SERVED page's label_status values, so the
weekly read can grep how much of what users actually see the court has judged.
"""
from app.services.thread_intelligence import stamped_counts


def _t(status):
    return {"thread_id": "x", "label": "y", "label_status": status}


def test_counts_each_verdict_bucket():
    threads = [
        _t("entailed"), _t("entailed"),
        _t("partial"),
        _t("failed"),
        _t(None),
    ]
    assert stamped_counts(threads) == {
        "entailed": 2, "partial": 1, "failed": 1, "unchecked": 1,
    }


def test_missing_field_and_unknown_values_count_as_unchecked():
    threads = [
        {"thread_id": "a", "label": "no status field at all"},
        _t(""),
        _t("weird-future-value"),
    ]
    assert stamped_counts(threads) == {
        "entailed": 0, "partial": 0, "failed": 0, "unchecked": 3,
    }


def test_normalizes_case_and_whitespace():
    assert stamped_counts([_t(" Entailed "), _t("FAILED")]) == {
        "entailed": 1, "partial": 0, "failed": 1, "unchecked": 0,
    }


def test_empty_page_serves_all_zero():
    assert stamped_counts([]) == {
        "entailed": 0, "partial": 0, "failed": 0, "unchecked": 0,
    }
