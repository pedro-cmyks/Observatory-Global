from app.services.signal_text import clean_snippet


def test_strips_whitespace():
    assert clean_snippet("  hello  ") == "hello"


def test_caps_at_500():
    out = clean_snippet("a" * 800)
    assert out is not None and len(out) == 500


def test_empty_to_none():
    assert clean_snippet("") is None
    assert clean_snippet("   ") is None


def test_none_to_none():
    assert clean_snippet(None) is None


def test_normal_passthrough():
    assert clean_snippet("Russia warns on the Baltic.") == "Russia warns on the Baltic."
