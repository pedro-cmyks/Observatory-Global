"""Lexical connection fallback (spec T1 — embed-down / unembedded items)."""
from app.routers.signals import _lexical_connections, _lex_tokens, _stem


class _Row(dict):
    def __getitem__(self, k): return dict.__getitem__(self, k)


def _rows():
    return [
        {"slug": "election-legitimacy-dispute", "label": "Election legitimacy dispute", "n": 40},
        {"slug": "armed-conflict-escalation", "label": "Armed conflict escalation", "n": 1200},
        {"slug": "heat-public-health-risk", "label": "Heat and public health risk", "n": 700},
    ]


def test_africa_elections_connects_to_election_thread():
    out = _lexical_connections("Who is Buying Africa's Elections? The Shadow Industry Exposed", _rows())
    assert out, "should find a keyword connection"
    assert out[0]["thread_id"] == "election-legitimacy-dispute"
    assert out[0]["basis"] == "keyword"
    assert "election" in out[0]["shared"]


def test_stem_matches_plural():
    assert _stem("elections") == _stem("election")


def test_stopwords_dropped():
    assert "who" not in _lex_tokens("Who is buying elections")
    assert "election" in {_stem(w) for w in _lex_tokens("elections")}


def test_no_overlap_returns_empty():
    out = _lexical_connections("cooking pasta recipe tonight", _rows())
    assert out == []
