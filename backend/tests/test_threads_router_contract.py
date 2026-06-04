from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "app" / "routers" / "threads.py"


def _src() -> str:
    return ROUTER.read_text(encoding="utf-8")


def test_threads_list_accepts_country_code_and_passes_country_filter():
    source = _src()
    assert "country_code: str | None" in source
    assert '"country_code": country' in source
    assert "country_codes=[country] if country else None" in source


def test_thread_detail_accepts_llm_flag_and_falls_back_when_absent():
    source = _src()
    assert "llm: bool = Query(False)" in source
    assert "build_deepseek_thread_narrative_note(thread)" in source
    assert 'thread["narrative_note"] = llm_note' in source
