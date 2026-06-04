from app.services import thread_intelligence as ti


def test_serialize_evidence_includes_snippet():
    row = {
        "id": 1, "headline": "Russia warns on the Baltic", "source_name": "Reuters",
        "source_url": "http://x", "country_code": "RU", "country_name": "Russia",
        "timestamp": None, "nlp_sentiment": None, "confidence": None,
        "syndication_count": 1, "snippet": "Moscow said it would respond.",
    }
    out = ti._serialize_evidence(row)
    assert out["snippet"] == "Moscow said it would respond."


def test_serialize_evidence_snippet_nullsafe():
    row = {"id": 2, "headline": "h", "source_name": None, "source_url": None,
           "country_code": None, "country_name": None, "timestamp": None,
           "nlp_sentiment": None, "confidence": None, "syndication_count": 1}
    out = ti._serialize_evidence(row)
    assert out["snippet"] is None
