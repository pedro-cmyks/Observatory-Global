"""Relabel pure logic: generated-label cleaning + no-op detection."""
from scripts.relabel_court_failed import clean_generated_label, is_label_unchanged


def test_strips_quotes_and_label_prefix():
    assert clean_generated_label('"Label: Venezuela Earthquake Recovery Efforts."') == \
        "Venezuela Earthquake Recovery Efforts"


def test_rejects_placeholder_and_empty_and_extremes():
    assert clean_generated_label("(label failed)") is None
    assert clean_generated_label("") is None
    assert clean_generated_label("Short") is None
    assert clean_generated_label("x" * 120) is None


def test_plain_label_passes():
    assert clean_generated_label("Moldova Political Crisis Deepens") == \
        "Moldova Political Crisis Deepens"


# ---------------------------------------------------------------------------
# No-op relabel detection (GB2 incidental finding, 2026-07-29): the 15:38 pass
# cleared label_status on dt-8172/5549/8170 while writing back the byte-
# identical string that had just failed — the front page lost its court stamp
# with zero label change, and the next court pass re-failed the same string.
# A relabel equal to the current label (modulo whitespace/case) must be a
# NO-OP: keep the existing stamp, ledger reason='relabel_no_change'.
# ---------------------------------------------------------------------------

def test_byte_identical_witness_strings_are_unchanged():
    # the three 2026-07-29 15:38 witnesses, verbatim from the relabel ledger
    for lab in ("Wildfires in France and Spain Force Evacuations",       # dt-8172
                "EU Sanctions, US Arrests, and Defense Moves",           # dt-5549
                "Global heatwaves, wildfires, and power outages"):       # dt-8170
        assert is_label_unchanged(lab, lab)


def test_case_and_whitespace_differences_are_unchanged():
    assert is_label_unchanged("France Heatwave Alerts", "france heatwave alerts")
    assert is_label_unchanged("France  Heatwave\tAlerts", " France Heatwave Alerts ")


def test_real_rewrite_is_a_change():
    # dt-8070's Sites<->Facilities churn is a real text change — stamp reset stands
    assert not is_label_unchanged("Iran Strikes US Sites in Bahrain, Jordan",
                                  "Iran Strikes US Facilities in Bahrain, Jordan")
    assert not is_label_unchanged("France Heatwave Alerts",
                                  "Historic wildfires in France and Spain force evacuations")


def test_missing_old_label_is_a_change():
    assert not is_label_unchanged(None, "France Heatwave Alerts")
    assert not is_label_unchanged("", "France Heatwave Alerts")
