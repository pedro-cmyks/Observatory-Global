from __future__ import annotations

from pathlib import Path


def test_theme_insight_imports_os_for_env_fallback():
    source = Path("app/routers/themes.py").read_text(encoding="utf-8")

    assert "import os" in source
    assert 'os.getenv("ANTHROPIC_API_KEY")' in source
