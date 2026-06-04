from pathlib import Path

SERVICES = Path(__file__).resolve().parents[1] / "app" / "services"
TEXT_INGESTS = [
    "ingest_reddit.py",
    "ingest_newsapi.py",
    "ingest_rss.py",
    "ingest_newsdata.py",
    "ingest_mediastack.py",
    "ingest_reliefweb.py",
]


def test_each_text_ingest_inserts_snippet():
    for name in TEXT_INGESTS:
        src = (SERVICES / name).read_text(encoding="utf-8")
        assert "snippet" in src, f"{name} missing snippet"
        assert "signal_class," in src
        assert "$22" in src, f"{name} INSERT not extended to $22"


def test_gdelt_ingest_does_not_persist_snippet():
    src = (SERVICES / "ingest_v2.py").read_text(encoding="utf-8")
    assert "snippet" not in src
