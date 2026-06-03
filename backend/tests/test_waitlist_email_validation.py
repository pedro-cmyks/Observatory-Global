from app.routers.waitlist import normalize_email, is_valid_email


def test_normalize_trims_and_lowercases():
    assert normalize_email("  A@B.COM ") == "a@b.com"


def test_valid_simple_email():
    assert is_valid_email("user@example.com") is True


def test_valid_after_normalize():
    assert is_valid_email(normalize_email("  User@Example.Com ")) is True


def test_rejects_no_at():
    assert is_valid_email("userexample.com") is False


def test_rejects_no_domain_dot():
    assert is_valid_email("user@example") is False


def test_rejects_spaces():
    assert is_valid_email("user @example.com") is False


def test_rejects_empty():
    assert is_valid_email("") is False


def test_rejects_too_long():
    assert is_valid_email("a" * 320 + "@x.com") is False
