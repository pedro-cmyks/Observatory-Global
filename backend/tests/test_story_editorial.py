"""Story share-editorial — the quote-gated LinkedIn lede (campaign piece A v2).

Service tests exercise the gate itself (the honesty machinery); the router
section mirrors tests/test_story_router_contract.py's source-contract style
(no DB fixture exists) plus a direct handler call with the chain mocked.
"""
import json
import re
from pathlib import Path

import pytest

from app.services import story_editorial as se
from app.services.story_editorial import EditorialReceipt

ROOT = Path(__file__).resolve().parents[1]
ROUTER = (ROOT / "app" / "routers" / "story.py").read_text()

R_ES = EditorialReceipt(
    headline="Terremoto de 7.4 sacude Colombia y deja 25 muertos",
    outlet="El Tiempo", lang="es",
)
R_STATE = EditorialReceipt(
    headline="Rescue teams reach quake zone", outlet="rt.com", lang="en",
    state_media=True,
)


# ── prompt ───────────────────────────────────────────────────────────────────

def test_prompt_numbers_receipts_and_tags_state_media():
    user = se.build_editorial_user_prompt("Colombia Earthquake", [R_ES, R_STATE])
    assert "Story label: Colombia Earthquake" in user
    assert "[1] (es · El Tiempo) Terremoto de 7.4" in user
    assert "[2] (en · rt.com) Rescue teams reach quake zone [STATE MEDIA]" in user
    # the non-state receipt is NOT tagged
    assert user.count("[STATE MEDIA]") == 1


def test_system_prompt_carries_the_rails():
    assert "STATE MEDIA IS NEVER NEUTRAL" in se._EDITORIAL_SYSTEM
    assert "verbatim" in se._EDITORIAL_SYSTEM.lower()
    assert "STRICT JSON" in se._EDITORIAL_SYSTEM


# ── quote gate ───────────────────────────────────────────────────────────────

def _v(sentences, receipts=(R_ES, R_STATE)):
    return se.validate_editorial({"sentences": sentences}, list(receipts))


def test_grounded_sentences_pass():
    out = _v([
        {"text": "A 7.4 quake killed 25 in Colombia.",
         "quote": "Terremoto de 7.4 sacude Colombia y deja 25 muertos", "receipt": 1},
        {"text": "Rescue teams reached the zone, according to RT.",
         "quote": "Rescue teams reach quake zone", "receipt": 2},
    ])
    assert [s["receipt"] for s in out["sentences"]] == [1, 2]
    assert out["dropped"] == 0


def test_non_substring_quote_is_dropped():
    out = _v([{"text": "Quake hit.", "quote": "This never appeared anywhere", "receipt": 1}])
    assert out == {"sentences": [], "dropped": 1}


def test_quote_gate_normalizes_smart_quotes_and_whitespace():
    r = [EditorialReceipt(headline="Officials say “no danger” after blast")]
    out = se.validate_editorial(
        {"sentences": [{"text": "Officials downplayed it.",
                        "quote": 'say "no danger" after blast', "receipt": 1}]}, r)
    assert len(out["sentences"]) == 1


def test_short_quote_rejected_unless_whole_headline():
    # 'de 7.4 sac' is a substring but trivially short → dropped
    out = _v([{"text": "Quake.", "quote": "de 7.4 sac", "receipt": 1}])
    assert out["sentences"] == []
    # a SHORT headline quoted in full is as grounded as it gets → kept
    r = [EditorialReceipt(headline="Oil spikes")]
    out2 = se.validate_editorial(
        {"sentences": [{"text": "Oil prices spiked.", "quote": "Oil spikes", "receipt": 1}]}, r)
    assert len(out2["sentences"]) == 1


def test_number_guard_drops_invented_digits():
    out = _v([{"text": "Some 300 died in the quake.",
               "quote": "Terremoto de 7.4 sacude Colombia y deja 25 muertos", "receipt": 1}])
    assert out == {"sentences": [], "dropped": 1}
    # numbers the receipt carries are fine
    ok = _v([{"text": "The 7.4 quake left 25 dead.",
              "quote": "Terremoto de 7.4 sacude Colombia y deja 25 muertos", "receipt": 1}])
    assert len(ok["sentences"]) == 1


def test_state_media_sentence_must_name_the_outlet():
    unattributed = _v([{"text": "Rescue teams reached the zone.",
                        "quote": "Rescue teams reach quake zone", "receipt": 2}])
    assert unattributed == {"sentences": [], "dropped": 1}
    attributed = _v([{"text": "Rescue teams reached the zone, RT reported.",
                      "quote": "Rescue teams reach quake zone", "receipt": 2}])
    assert len(attributed["sentences"]) == 1


def test_bad_receipt_refs_and_shapes_dropped():
    out = _v([
        {"text": "x", "quote": "Terremoto de 7.4 sacude Colombia y deja 25 muertos", "receipt": 3},
        {"text": "", "quote": "Terremoto de 7.4 sacude Colombia y deja 25 muertos", "receipt": 1},
        "not-a-dict",
    ])
    assert out == {"sentences": [], "dropped": 3}
    assert se.validate_editorial(None, [R_ES]) == {"sentences": [], "dropped": 0}
    assert se.validate_editorial({"sentences": "nope"}, [R_ES]) == {"sentences": [], "dropped": 0}


def test_caps_at_three_sentences():
    good = {"text": "The quake killed 25.",
            "quote": "Terremoto de 7.4 sacude Colombia y deja 25 muertos", "receipt": 1}
    out = _v([good, good, good, good])
    assert len(out["sentences"]) == 3


# ── run_share_editorial (chain mocked) ───────────────────────────────────────

def _mock_chain(monkeypatch, *, text, provider="deepseek", error=None):
    async def fake(system, user, *, max_tokens=256, surface=None, session_id=None):
        return (text, provider if text is not None else None, error, None)
    monkeypatch.setattr(se, "generate_insight", fake)


@pytest.mark.asyncio
async def test_run_success_joins_lede(monkeypatch):
    payload = {"sentences": [
        {"text": "A 7.4 quake killed 25 in Colombia.",
         "quote": "Terremoto de 7.4 sacude Colombia y deja 25 muertos", "receipt": 1},
        {"text": "Rescue teams reached the zone, according to RT.",
         "quote": "Rescue teams reach quake zone", "receipt": 2},
    ]}
    _mock_chain(monkeypatch, text=json.dumps(payload))
    out = await se.run_share_editorial("Colombia Earthquake", [R_ES, R_STATE])
    assert out["error"] is None
    assert out["lede"].startswith("A 7.4 quake killed 25")
    assert "according to RT" in out["lede"]
    assert len(out["sentences"]) == 2


@pytest.mark.asyncio
async def test_run_truncated_json_is_repaired(monkeypatch):
    full = json.dumps({"sentences": [
        {"text": "A 7.4 quake killed 25 in Colombia.",
         "quote": "Terremoto de 7.4 sacude Colombia y deja 25 muertos", "receipt": 1},
        {"text": "Truncated tail sentence",
         "quote": "Terremoto de 7.4 sacude Colombia y deja 25 muertos", "receipt": 1},
    ]})
    truncated = full[: full.index("Truncated")]  # cut mid-second-object
    _mock_chain(monkeypatch, text=truncated)
    out = await se.run_share_editorial("Colombia Earthquake", [R_ES, R_STATE])
    assert out["error"] is None
    assert len(out["sentences"]) == 1  # first complete sentence survives


@pytest.mark.asyncio
async def test_run_provider_failure_passes_error_through(monkeypatch):
    _mock_chain(monkeypatch, text=None, error="insight_no_credits")
    out = await se.run_share_editorial("X", [R_ES])
    assert out == {"lede": None, "sentences": [], "dropped": 0,
                   "provider": None, "error": "insight_no_credits"}


@pytest.mark.asyncio
async def test_run_all_dropped_is_quote_gate_failed(monkeypatch):
    _mock_chain(monkeypatch, text=json.dumps(
        {"sentences": [{"text": "Invented.", "quote": "never in any headline", "receipt": 1}]}))
    out = await se.run_share_editorial("X", [R_ES])
    assert out["lede"] is None
    assert out["error"] == "quote_gate_failed"
    assert out["dropped"] == 1


# ── router contract + handler ────────────────────────────────────────────────

def test_router_path_contract_and_bucket():
    assert '@router.post("/api/v2/story/{thread_id}/share-editorial")' in ROUTER
    assert "story-share-editorial-v1" in ROUTER
    from app.rate_limit import _build_rules
    path = "/api/v2/story/dynamic-topic-11877/share-editorial"
    bucket = next(b for (p, b, pred) in _build_rules() if p.match(path))
    assert bucket == "paid"


def test_cache_write_requires_a_served_lede():
    # never-cache-degraded: the setex in the editorial section sits behind
    # a body.get("lede") guard, so an outage / all-dropped gate stays retryable.
    section = ROUTER[ROUTER.index("share-editorial"):]
    assert re.search(r'body\.get\("lede"\)', section)
    assert section.index('body.get("lede")') < section.index("setex")


@pytest.mark.asyncio
async def test_handler_invalid_id_and_server_state_or(monkeypatch):
    from app.routers import story as story_router

    monkeypatch.setattr(story_router, "_redis_client", lambda: None)
    captured: dict = {}

    async def fake_run(label, receipts, **kw):
        captured["receipts"] = receipts
        return {"lede": "L.", "sentences": [], "dropped": 0,
                "provider": "deepseek", "error": None}

    monkeypatch.setattr(story_router._story_editorial, "run_share_editorial", fake_run)

    req = story_router.ShareEditorialRequest(
        label="Story",
        receipts=[
            # client did NOT flag it — the server name classifier must
            {"headline": "Official line on the quake", "outlet": "russian.rt.com"},
            {"headline": "Independent account", "outlet": "The Guardian"},
        ],
    )
    bad = await story_router.post_story_share_editorial("///bad id///", req)
    assert bad["error"] == "invalid_thread_id"
    assert bad["lede"] is None

    ok = await story_router.post_story_share_editorial("dynamic-topic-42", req)
    assert ok["contract"] == "story-share-editorial-v1"
    assert ok["story"] == "dynamic-topic-42"
    assert ok["lede"] == "L."
    assert ok["cached"] is False
    flags = [r.state_media for r in captured["receipts"]]
    assert flags == [True, False]  # rt.com forced state by the SERVER, Guardian not


def test_numeric_outlet_token_never_satisfies_attribution():
    # "24" (of 24.kg) appearing as a bare NUMBER in the sentence is not a
    # name reference — only an alphabetic token counts.
    r = [EditorialReceipt(headline="Три склада атакованы ночью дронами",
                          outlet="24.kg", state_media=True)]
    out = se.validate_editorial({"sentences": [{
        "text": "Warehouses were attacked overnight.",
        "quote": "Три склада атакованы ночью дронами", "receipt": 1}]}, r)
    assert out["sentences"] == []
    # Mentioning "24.kg" inline introduces the digits 24, which the cited
    # headline does not carry → the NUMBER guard drops it. Conservative by
    # design (drop over fabricate); the alphabetic token alone attributes.
    dropped = se.validate_editorial({"sentences": [{
        "text": "Warehouses were attacked overnight, 24.kg reported.",
        "quote": "Три склада атакованы ночью дронами", "receipt": 1}]}, r)
    assert dropped["sentences"] == []
    ok = se.validate_editorial({"sentences": [{
        "text": "Warehouses were attacked overnight, the kg outlet reported.",
        "quote": "Три склада атакованы ночью дронами", "receipt": 1}]}, r)
    assert len(ok["sentences"]) == 1
