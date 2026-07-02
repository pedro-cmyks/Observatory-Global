"""Thread-shaped theme-focus values resolve via typed membership (universe entry)."""
from app.services.focus_filters import thread_focus_filter


def test_gdelt_codes_pass_through():
    assert thread_focus_filter("PROTEST") is None
    assert thread_focus_filter("WB_137_WATER") is None  # underscores, no hyphen


def test_dynamic_topic_id_resolves_verbatim():
    sql, param = thread_focus_filter("dynamic-topic-981")
    assert "topic_members" in sql and "role = 'evidence'" in sql
    assert param == "dynamic-topic-981"


def test_atlas_thread_id_strips_country_suffix():
    _, param = thread_focus_filter("gang-control-urban-security--gb-us-in")
    assert param == "gang-control-urban-security"


def test_plain_atlas_slug_kept():
    _, param = thread_focus_filter("Disease-Outbreak")
    assert param == "disease-outbreak"
