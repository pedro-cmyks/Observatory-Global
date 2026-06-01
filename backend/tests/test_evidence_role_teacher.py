from __future__ import annotations

from scripts.evidence_role_teacher import build_teacher_prompt, parse_teacher_json


def test_build_teacher_prompt_requests_role_reason_codes_and_rationale():
    packet = {
        "signal_id": 10,
        "headline": "Iran threatens retaliation after sanctions",
        "cluster_label": "Iran Threats to US",
        "cluster_description": "Iran-US threats and sanctions.",
        "candidate_topic_slug": "sanctions-diplomatic-pressure",
        "gate_score": 0.66,
    }

    prompt = build_teacher_prompt(packet)

    assert "primary_evidence" in prompt
    assert "reason_codes" in prompt
    assert "rationale" in prompt
    assert "Return only JSON" in prompt


def test_parse_teacher_json_extracts_first_json_object():
    raw = (
        'Here is the JSON:\n{"role":"context","role_confidence":0.7,'
        '"belongs_to_cluster":true,"supports_cluster_claim":false,'
        '"reason_codes":["background_only"],"rationale":"Background only",'
        '"alternate_role":"analysis"}'
    )

    parsed = parse_teacher_json(raw)

    assert parsed["role"] == "context"
    assert parsed["reason_codes"] == ["background_only"]


def test_parse_teacher_json_ignores_trailing_text_or_extra_objects():
    raw = (
        '{"role":"noise","role_confidence":0.9,"belongs_to_cluster":false,'
        '"supports_cluster_claim":false,"reason_codes":["off_topic"],'
        '"rationale":"Off topic"} trailing {"role":"context"}'
    )

    parsed = parse_teacher_json(raw)

    assert parsed["role"] == "noise"
    assert parsed["reason_codes"] == ["off_topic"]
