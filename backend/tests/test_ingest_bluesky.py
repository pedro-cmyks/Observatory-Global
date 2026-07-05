"""Unified Engine F1.1 — Bluesky Jetstream parse/filter tests (spec §7)."""
from __future__ import annotations

from datetime import datetime, timezone

from app.services.ingest_bluesky import _event_to_signal, _parse_created


_REAL_TEXT = (
    "Parliament passed the emergency budget tonight after a long debate "
    "over energy subsidies and the deficit."
)


def _ev(text=_REAL_TEXT, langs=("en",), reply=False, op="create",
        collection="app.bsky.feed.post", did="did:plc:abc", rkey="rk1"):
    record = {"text": text, "langs": list(langs), "createdAt": "2026-06-29T18:00:00.000Z"}
    if reply:
        record["reply"] = {"parent": {"uri": "at://x"}}
    return {"kind": "commit", "did": did,
            "commit": {"operation": op, "collection": collection, "rkey": rkey, "record": record}}


def test_valid_post_becomes_signal():
    s = _event_to_signal(_ev())
    assert s is not None
    assert s["source_family"] == "social"
    assert s["signal_class"] == "social_commentary"
    assert s["attribution_method"] == "bluesky_jetstream"
    assert s["source_origin_country"] is None
    assert s["source_url"].startswith("https://bsky.app/profile/did:plc:abc/post/rk1")


def test_reply_dropped():
    assert _event_to_signal(_ev(reply=True)) is None


def test_short_text_dropped():
    assert _event_to_signal(_ev(text="too short")) is None


def test_no_langs_dropped():
    assert _event_to_signal(_ev(langs=())) is None


def test_non_create_dropped():
    assert _event_to_signal(_ev(op="delete")) is None


def test_wrong_collection_dropped():
    assert _event_to_signal(_ev(collection="app.bsky.feed.like")) is None


def test_bcp47_lang_reduced_to_two_letters():
    s = _event_to_signal(_ev(langs=("pt-BR",)))
    assert s is not None and s["source_lang"] == "pt"
    s2 = _event_to_signal(_ev(langs=("zh-Hans",)))
    assert s2 is not None and s2["source_lang"] == "zh"


def test_junk_lang_dropped():
    # a non-alpha / non-2-letter base must not overflow CHAR(2)
    assert _event_to_signal(_ev(langs=("123",))) is None


def test_missing_ids_dropped():
    ev = _ev()
    ev["did"] = None
    assert _event_to_signal(ev) is None


def test_parse_created_future_clamped_to_now():
    dt = _parse_created("2999-01-01T00:00:00Z")
    assert dt <= datetime.now(timezone.utc)


def test_parse_created_garbage_is_now():
    dt = _parse_created("nonsense")
    assert dt.tzinfo == timezone.utc


def test_headline_truncated_to_500():
    s = _event_to_signal(_ev(text=(_REAL_TEXT + " ") * 9))
    assert s is not None and len(s["headline"]) == 500


def test_number_template_spam_dropped():
    # the "Digit: N / In words: ..." counting bot (2026-07-04 junk cluster)
    spam = (
        "Digit: 5,250,037\n"
        "In words: Five Million Two Hundred Fifty Thousand Thirty Seven\n"
        "अङ्कः ५२,५०,०३७"
    )
    assert _event_to_signal(_ev(text=spam)) is None


def test_blocked_did_dropped():
    ev = _ev(did="did:plc:f4z2nftgrn75h7h3wucdyzaf")
    assert _event_to_signal(ev) is None
