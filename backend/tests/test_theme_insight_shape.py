from __future__ import annotations

from pathlib import Path


def test_theme_insight_uses_central_provider_chain_for_env_fallback():
    router_source = Path("app/routers/themes.py").read_text(encoding="utf-8")
    service_source = Path("app/services/insight_llm.py").read_text(encoding="utf-8")

    assert "from app.services.insight_llm import generate_insight" in router_source
    assert 'os.getenv("ANTHROPIC_API_KEY")' in service_source
    assert 'os.getenv("DEEPSEEK_API_KEY")' in service_source


def test_theme_detail_resolves_dynamic_topic_watchlist_slugs():
    source = Path("app/routers/themes.py").read_text(encoding="utf-8")

    assert "_dynamic_topic_detail" in source
    assert 'theme_code.lower().startswith("dynamic-topic-")' in source
    assert "to_regclass('dynamic_topics')" in source
    assert "to_regclass('dynamic_topic_members')" in source
    assert "dtm.dynamic_topic_id" in source
    assert "dtm.emergent_cluster_id" in source
    assert "dynamic_topic_member_preview_sample" in source
