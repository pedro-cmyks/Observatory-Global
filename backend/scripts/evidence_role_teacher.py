#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from scripts.evidence_role_schema import (
    EVIDENCE_ROLE_SCHEMA_VERSION,
    REASON_CODES,
    ROLES,
    read_jsonl,
    validate_teacher_label,
    write_jsonl,
)


def build_teacher_prompt(packet: dict[str, Any]) -> str:
    roles = ", ".join(sorted(ROLES))
    reason_codes = ", ".join(sorted(REASON_CODES))
    return f"""You are labeling evidence roles for Atlas narrative intelligence.

Choose exactly one role from: {roles}.
Choose zero or more reason_codes from: {reason_codes}.

Definitions:
- primary_evidence: directly supports the cluster's core event or claim.
- context: background or indirect mention, not proof.
- reaction: political, public, institutional, market, or social response.
- analysis: opinion, forecast, explainer, or interpretive article.
- entity_reference: useful mainly because it mentions a related actor/entity.
- noise: does not belong in this cluster.

Cluster label: {packet.get("cluster_label")}
Cluster description: {packet.get("cluster_description")}
Candidate topic: {packet.get("candidate_topic_slug")}
Gate score: {packet.get("gate_score")}
Headline: {packet.get("headline")}
Source: {packet.get("source_name")} / {packet.get("source_lang")} / {packet.get("country_code")}

Return only JSON with keys:
role, role_confidence, belongs_to_cluster, supports_cluster_claim,
reason_codes, rationale, alternate_role.
Keep rationale to one concise sentence.
"""


def parse_teacher_json(raw: str) -> dict[str, Any]:
    start = raw.find("{")
    if start == -1:
        raise ValueError("teacher response did not contain JSON object")
    parsed, _ = json.JSONDecoder().raw_decode(raw[start:])
    if not isinstance(parsed, dict):
        raise ValueError("teacher response JSON was not an object")
    return parsed


async def call_deepseek(prompt: str, model: str) -> str:
    import httpx

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise SystemExit("DEEPSEEK_API_KEY is required for --provider deepseek")
    async with httpx.AsyncClient(timeout=45.0) as client:
        res = await client.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
    res.raise_for_status()
    return res.json()["choices"][0]["message"].get("content") or ""


async def call_openai(prompt: str, model: str) -> str:
    import httpx

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required for --provider openai")
    async with httpx.AsyncClient(timeout=45.0) as client:
        res = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
    res.raise_for_status()
    return res.json()["choices"][0]["message"].get("content") or ""


async def call_anthropic(prompt: str, model: str) -> str:
    import httpx

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY is required for --provider anthropic")
    async with httpx.AsyncClient(timeout=45.0) as client:
        res = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 500,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}],
            },
        )
    res.raise_for_status()
    return "".join(
        block.get("text", "")
        for block in res.json().get("content", [])
        if block.get("type") == "text"
    )


async def label_one(packet: dict[str, Any], *, provider: str, model: str) -> dict[str, Any]:
    prompt = build_teacher_prompt(packet)
    if provider == "deepseek":
        raw = await call_deepseek(prompt, model)
    elif provider == "openai":
        raw = await call_openai(prompt, model)
    elif provider == "anthropic":
        raw = await call_anthropic(prompt, model)
    else:
        raise ValueError(f"unknown provider: {provider}")

    parsed = parse_teacher_json(raw)
    merged = {
        **packet,
        "schema_version": EVIDENCE_ROLE_SCHEMA_VERSION,
        "role": parsed["role"],
        "role_confidence": parsed["role_confidence"],
        "belongs_to_cluster": parsed["belongs_to_cluster"],
        "supports_cluster_claim": parsed["supports_cluster_claim"],
        "reason_codes": parsed.get("reason_codes", []),
        "rationale": parsed["rationale"],
        "alternate_role": parsed.get("alternate_role"),
        "teacher_model": model,
        "teacher_vendor": provider,
    }
    return validate_teacher_label(merged)


async def run(args: argparse.Namespace) -> list[dict[str, Any]]:
    packets = read_jsonl(args.input)
    selected = packets[: args.limit] if args.limit else packets
    semaphore = asyncio.Semaphore(max(1, args.concurrency))

    async def label_with_limit(packet: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            return await label_one(packet, provider=args.provider, model=args.model)

    return await asyncio.gather(*(label_with_limit(packet) for packet in selected))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one teacher model over an evidence-role packet."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--provider",
        choices=["deepseek", "openai", "anthropic"],
        required=True,
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--concurrency", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = asyncio.run(run(args))
    write_jsonl(args.output, rows)
    print(
        json.dumps(
            {
                "rows": len(rows),
                "provider": args.provider,
                "model": args.model,
                "output": str(args.output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
