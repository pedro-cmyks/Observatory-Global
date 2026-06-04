from app.services.deepseek_narrative import (
    build_deepseek_thread_note_messages,
    parse_deepseek_thread_note,
)


def test_deepseek_prompt_includes_compact_thread_context():
    messages = build_deepseek_thread_note_messages({
        "label": "Infrastructure and Public Services",
        "signal_count": 483,
        "changed_10h": 25,
        "top_countries": ["ID", "BR", "CA"],
        "top_sources": ["rri.co.id"],
        "quality": {"noise_rate": 0.21},
        "evidence_samples": [
            {
                "headline": "Currency pressure builds",
                "snippet": "Bank officials discussed public-service pressure.",
                "source": "rri.co.id",
                "country_code": "ID",
            }
        ],
    })

    assert messages[0]["role"] == "system"
    assert "Return strict JSON only" in messages[0]["content"]
    assert "Currency pressure builds" in messages[1]["content"]
    assert "noise_rate" in messages[1]["content"]


def test_parse_deepseek_thread_note_normalizes_quality_and_source():
    note = parse_deepseek_thread_note(
        """
        {
          "lede": "This cluster mixes several public-service stories.",
          "movement": "Volume is rising, but evidence is mostly country-local.",
          "evidence": "The visible examples include currency and immigration items.",
          "caveat": "",
          "quality": "unknown"
        }
        """,
        model="deepseek-v4-flash",
    )

    assert note == {
        "lede": "This cluster mixes several public-service stories.",
        "movement": "Volume is rising, but evidence is mostly country-local.",
        "evidence": "The visible examples include currency and immigration items.",
        "caveat": None,
        "quality": "provisional",
        "source": "deepseek:deepseek-v4-flash",
    }


def test_parse_deepseek_thread_note_rejects_incomplete_json():
    assert parse_deepseek_thread_note('{"lede":"Only one field"}', model="deepseek-v4-flash") is None


def test_parse_deepseek_thread_note_extracts_json_from_wrapped_text():
    note = parse_deepseek_thread_note(
        'Here is the JSON: {"lede":"L","movement":"M","evidence":"E","quality":"thin"}',
        model="deepseek-v4-pro",
    )

    assert note is not None
    assert note["source"] == "deepseek:deepseek-v4-pro"
    assert note["quality"] == "thin"
