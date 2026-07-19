"""Thread-scoped voice mix (council wish 18 — who SPEAKS inside a thread).

Pure aggregation over a thread's typed evidence members: which languages and
outlet origins carry the story, and — when the thread has a dominant subject
country — the self-voice relation (ownership, not language; same definition
as the country Voice Mix, single source of truth via voice_mix.relation).

Honesty invariants:
  * unattributed (no outlet origin) and unknown-language counts are REPORTED,
    never assumed domestic/foreign or folded into known shares;
  * no members -> available=False with a reason, never a fabricated mix;
  * no dominant subject country -> languages/origins still served, relation
    absent (never computed against a guessed subject).
"""
from app.services.thread_voice import aggregate_thread_voice


def _row(lang="en", origin=None, country="IR"):
    return {"source_lang": lang, "source_origin_country": origin,
            "country_code": country}


def test_empty_members_is_unavailable_with_reason():
    out = aggregate_thread_voice([])
    assert out["available"] is False
    assert "reason" in out


def test_language_breakdown_reports_unknown_honestly():
    rows = [_row("en"), _row("en"), _row("fa"), _row("xx"), _row(None), _row("")]
    out = aggregate_thread_voice(rows)
    assert out["available"] is True
    assert out["voices_total"] == 6
    langs = {d["lang"]: d["n"] for d in out["languages"]}
    assert langs == {"en": 2, "fa": 1}
    assert out["language_unknown"] == 3


def test_subject_is_dominant_member_country():
    rows = [_row(country="IR"), _row(country="IR"), _row(country="US")]
    out = aggregate_thread_voice(rows)
    assert out["subject_country"] == "IR"
    assert out["subject_share"] == round(2 / 3, 4)


def test_self_voice_is_ownership_not_language():
    # BBC Persian about Iran = GB eyes, Persian words -> soft power, NOT self.
    rows = [
        _row("fa", origin="IR", country="IR"),   # domestic voice
        _row("fa", origin="GB", country="IR"),   # soft power (foreign, local lang)
        _row("en", origin="US", country="IR"),   # plain foreign
        _row("en", origin=None, country="IR"),   # unattributed — reported, not assumed
    ]
    out = aggregate_thread_voice(rows)
    rel = out["relation"]
    assert rel["self_voice"] == 1
    assert rel["attributable_voices"] == 3
    assert rel["unattributed"] == 1
    assert rel["soft_power_local_language"] == 1
    assert rel["self_voice_ratio"] == round(1 / 3, 4)
    assert rel["dominant_outsider"]["origin"] in ("GB", "US")


def test_no_subject_country_serves_mix_without_relation():
    rows = [_row(country=None), _row(country=None)]
    out = aggregate_thread_voice(rows)
    assert out["available"] is True
    assert out["subject_country"] is None
    assert "relation" not in out


def test_origin_breakdown_and_unattributed():
    rows = [_row(origin="IR"), _row(origin="FR"), _row(origin="FR"), _row(origin=None)]
    out = aggregate_thread_voice(rows)
    origins = {d["cc"]: d["n"] for d in out["origins"]}
    assert origins == {"FR": 2, "IR": 1}
    assert out["origin_unattributed"] == 1
