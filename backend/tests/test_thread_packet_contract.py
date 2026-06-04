from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / "app" / "services" /
       "thread_intelligence.py").read_text(encoding="utf-8")


def test_sample_sql_selects_themes():
    assert "themes" in SRC
    assert "_EMERGENT_SAMPLE_SIGNALS_SQL" in SRC


def test_detail_paths_attach_packet():
    assert "build_thread_packet" in SRC
    assert '"packet"' in SRC
