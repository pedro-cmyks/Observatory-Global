"""Relabel pure logic: generated-label cleaning."""
from scripts.relabel_court_failed import clean_generated_label


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
