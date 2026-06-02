from __future__ import annotations

from pathlib import Path


def test_theme_insight_imports_os_for_env_fallback():
    source = Path("app/routers/themes.py").read_text(encoding="utf-8")

    assert "import os" in source
    assert 'os.getenv("ANTHROPIC_API_KEY")' in source


def test_theme_detail_resolves_dynamic_topic_watchlist_slugs():
    source = Path("app/routers/themes.py").read_text(encoding="utf-8")

    assert "_dynamic_topic_detail" in source
    assert 'theme_code.lower().startswith("dynamic-topic-")' in source
    assert "to_regclass('dynamic_topics')" in source
    assert "to_regclass('dynamic_topic_members')" in source
    assert "dtm.dynamic_topic_id" in source
    assert "dtm.emergent_cluster_id" in source
    assert "dynamic_topic_member_preview_sample" in source
