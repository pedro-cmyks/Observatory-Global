# Narrative Cluster Evidence Roles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a file-based teacher-student pilot that labels evidence roles inside narrative clusters, measures whether Atlas can recover >=80% visible coverage while preserving >=90% precision for verified evidence, and keeps the Obsidian documentation path current.

**Architecture:** Keep the existing `signal_topic_assignments` + scope gate as candidate/confidence input. Sample `(cluster, signal)` pairs from recent `emergent_clusters`, have LLM teachers assign evidence roles plus rationales/reason codes offline, build consensus labels, train a local e5-base + logistic-regression student, and report coverage/precision tiers without adding production tables yet.

**Tech Stack:** Python 3.12, stdlib JSON/argparse/asyncio, asyncpg, existing `backend/.venv`, local `intfloat/multilingual-e5-base`, numpy/scikit-learn patterns already used by scope-gate scripts, Markdown docs/MOCs for Obsidian.

---

## Scope Check

This plan implements only the file-based pilot from the spec. It does not add the future `thread_evidence_roles` table, does not change frontend UI, and does not alter production read paths. The output is a measured report that decides whether the role layer is worth promotion.

## File Structure

- Create `backend/scripts/evidence_role_schema.py`: shared constants, role/reason-code validation, teacher/consensus JSONL helpers.
- Create `backend/scripts/evidence_role_sampler.py`: read-only Supabase sampler from latest `emergent_clusters`, `signals_v2`, and `signal_topic_assignments`.
- Create `backend/scripts/evidence_role_teacher.py`: offline teacher runner for Anthropic/OpenAI-compatible/DeepSeek APIs, emitting versioned JSONL with `rationale` and `reason_codes`.
- Create `backend/scripts/evidence_role_consensus.py`: combines teacher outputs into consensus labels and disagreement packets.
- Create `backend/scripts/train_evidence_role_student.py`: local student training/evaluation from consensus labels; writes model/report artifacts.
- Create tests:
  - `backend/tests/test_evidence_role_schema.py`
  - `backend/tests/test_evidence_role_sampler.py`
  - `backend/tests/test_evidence_role_consensus.py`
  - `backend/tests/test_train_evidence_role_student.py`
- Write artifacts under:
  - `docs/research/atlas-paper/phase-1-validation/evidence-role/teacher-packets/`
  - `docs/research/atlas-paper/phase-1-validation/labels/evidence-role-teacher/`
  - `docs/research/atlas-paper/phase-1-validation/labels/evidence-role-consensus/`
  - `docs/research/atlas-paper/phase-1-validation/reports/evidence-role/`
  - `docs/research/atlas-paper/phase-1-validation/models/evidence-role/`
- Update Obsidian-linked docs:
  - `docs/maps/Narrative Intelligence.md`
  - `docs/maps/Validation and Paper Track.md`
  - `docs/000-INDEX.md`
  - `SESSION_LOG.md`
  - `STATUS.md`

---

### Task 1: Shared Evidence Role Schema

**Files:**
- Create: `backend/scripts/evidence_role_schema.py`
- Test: `backend/tests/test_evidence_role_schema.py`

- [ ] **Step 1: Write the failing schema tests**

Create `backend/tests/test_evidence_role_schema.py`:

```python
from __future__ import annotations

import json

import pytest

from scripts.evidence_role_schema import (
    EVIDENCE_ROLE_SCHEMA_VERSION,
    REASON_CODES,
    ROLES,
    normalize_reason_codes,
    validate_teacher_label,
)


def test_validate_teacher_label_accepts_role_rationale_and_reason_codes():
    row = {
        "schema_version": EVIDENCE_ROLE_SCHEMA_VERSION,
        "signal_id": 101,
        "cluster_id": "2026-06-01T12:00:00Z/48",
        "headline": "Iran threatens retaliation after US sanctions",
        "cluster_label": "Iran Threats to US",
        "cluster_description": "Coverage of Iran-US threats and sanctions.",
        "candidate_topic_slug": "sanctions-diplomatic-pressure",
        "role": "reaction",
        "role_confidence": 0.86,
        "belongs_to_cluster": True,
        "supports_cluster_claim": True,
        "reason_codes": ["public_reaction", "same_actor", "same_time_window"],
        "rationale": "The headline describes a reaction by Iran inside the same Iran-US sanctions cluster.",
        "alternate_role": "context",
        "teacher_model": "deepseek-chat",
        "teacher_vendor": "deepseek",
    }

    validated = validate_teacher_label(row)

    assert validated["role"] == "reaction"
    assert validated["reason_codes"] == ["public_reaction", "same_actor", "same_time_window"]
    assert validated["role_confidence"] == 0.86


def test_validate_teacher_label_rejects_unknown_role_and_reason_code():
    bad_role = {
        "signal_id": 101,
        "cluster_id": "snap/1",
        "headline": "Headline",
        "cluster_label": "Cluster",
        "role": "rumor",
        "role_confidence": 0.5,
        "belongs_to_cluster": True,
        "supports_cluster_claim": False,
        "reason_codes": ["same_actor"],
        "rationale": "Reason",
        "teacher_model": "model",
        "teacher_vendor": "vendor",
    }
    with pytest.raises(ValueError, match="invalid evidence role"):
        validate_teacher_label(bad_role)

    bad_reason = dict(bad_role, role="context", reason_codes=["vibes"])
    with pytest.raises(ValueError, match="invalid reason code"):
        validate_teacher_label(bad_reason)


def test_normalize_reason_codes_dedupes_and_sorts_known_codes():
    assert normalize_reason_codes(["same_actor", "off_topic", "same_actor"]) == [
        "off_topic",
        "same_actor",
    ]


def test_role_and_reason_sets_are_stable_for_teacher_prompts():
    assert "primary_evidence" in ROLES
    assert "context" in ROLES
    assert "noise" in ROLES
    assert "direct_event_match" in REASON_CODES
    assert "generic_roundup" in REASON_CODES
```

- [ ] **Step 2: Run the schema tests and verify they fail**

Run:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_evidence_role_schema.py -q
```

Expected: fail with `ModuleNotFoundError: No module named 'scripts.evidence_role_schema'`.

- [ ] **Step 3: Implement the shared schema module**

Create `backend/scripts/evidence_role_schema.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


EVIDENCE_ROLE_SCHEMA_VERSION = "atlas-evidence-role-teacher-v1"

ROLES = {
    "primary_evidence",
    "context",
    "reaction",
    "analysis",
    "entity_reference",
    "noise",
}

REASON_CODES = {
    "direct_event_match",
    "same_actor",
    "same_place",
    "same_time_window",
    "causal_update",
    "official_action",
    "public_reaction",
    "analysis_frame",
    "background_only",
    "entity_only",
    "generic_roundup",
    "off_topic",
    "insufficient_context",
}

REQUIRED_TEACHER_FIELDS = {
    "signal_id",
    "cluster_id",
    "headline",
    "cluster_label",
    "role",
    "role_confidence",
    "belongs_to_cluster",
    "supports_cluster_claim",
    "reason_codes",
    "rationale",
    "teacher_model",
    "teacher_vendor",
}


def normalize_reason_codes(codes: Iterable[str]) -> list[str]:
    normalized = sorted({str(code).strip() for code in codes if str(code).strip()})
    invalid = [code for code in normalized if code not in REASON_CODES]
    if invalid:
        raise ValueError(f"invalid reason code(s): {', '.join(invalid)}")
    return normalized


def validate_teacher_label(row: dict[str, Any]) -> dict[str, Any]:
    missing = sorted(REQUIRED_TEACHER_FIELDS - set(row))
    if missing:
        raise ValueError(f"missing teacher field(s): {', '.join(missing)}")

    role = str(row["role"]).strip()
    if role not in ROLES:
        raise ValueError(f"invalid evidence role: {role}")

    confidence = float(row["role_confidence"])
    if confidence < 0.0 or confidence > 1.0:
        raise ValueError("role_confidence must be between 0 and 1")

    validated = dict(row)
    validated["schema_version"] = row.get("schema_version", EVIDENCE_ROLE_SCHEMA_VERSION)
    validated["role"] = role
    validated["role_confidence"] = round(confidence, 4)
    validated["belongs_to_cluster"] = bool(row["belongs_to_cluster"])
    validated["supports_cluster_claim"] = bool(row["supports_cluster_claim"])
    validated["reason_codes"] = normalize_reason_codes(row.get("reason_codes") or [])
    return validated


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
```

- [ ] **Step 4: Run schema tests and verify they pass**

Run:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_evidence_role_schema.py -q
```

Expected: `4 passed`.

- [ ] **Step 5: Commit Task 1**

```bash
git add backend/scripts/evidence_role_schema.py backend/tests/test_evidence_role_schema.py
git commit -m "feat(validation): add evidence role schema"
```

---

### Task 2: Read-Only Evidence Role Sampler

**Files:**
- Create: `backend/scripts/evidence_role_sampler.py`
- Test: `backend/tests/test_evidence_role_sampler.py`

- [ ] **Step 1: Write failing sampler tests**

Create `backend/tests/test_evidence_role_sampler.py`:

```python
from __future__ import annotations

from scripts.evidence_role_sampler import (
    SAMPLE_SQL,
    build_cluster_id,
    build_teacher_packet_row,
)


def test_build_cluster_id_is_stable_from_snapshot_and_cluster_pk():
    assert build_cluster_id("2026-06-01T12:41:32Z", 48) == "2026-06-01T12:41:32Z/48"


def test_build_teacher_packet_row_maps_cluster_signal_and_candidate_fields():
    row = build_teacher_packet_row(
        {
            "signal_id": 10,
            "headline": "Iran threatens retaliation after sanctions",
            "source_name": "example.org",
            "source_lang": "en",
            "country_code": "IR",
            "cluster_pk": 48,
            "snapshot_at": "2026-06-01T12:41:32Z",
            "cluster_label": "Iran Threats to US",
            "cluster_description": "Iran-US sanctions and threats.",
            "raw_signal_count": 122,
            "n_signals": 109,
            "cohesion": 0.72,
            "candidate_topic_slug": "sanctions-diplomatic-pressure",
            "candidate_topic_label": "Sanctions and diplomatic pressure",
            "candidate_confidence": 0.77,
            "gate_score": 0.66,
            "gate_kept": False,
            "matched_terms": ["sanction"],
            "sample_reason": "centroid_near",
        }
    )

    assert row["schema_version"] == "atlas-evidence-role-packet-v1"
    assert row["cluster_id"] == "2026-06-01T12:41:32Z/48"
    assert row["candidate_topic_slug"] == "sanctions-diplomatic-pressure"
    assert row["gate_kept"] is False
    assert row["matched_terms"] == ["sanction"]
    assert row["teacher_role"] is None


def test_sampler_sql_reads_emergent_clusters_signals_and_assignments():
    assert "FROM emergent_clusters ec" in SAMPLE_SQL
    assert "JOIN signals_v2 s" in SAMPLE_SQL
    assert "LEFT JOIN signal_topic_assignments sta" in SAMPLE_SQL
    assert "sample_signal_ids" in SAMPLE_SQL
```

- [ ] **Step 2: Run sampler tests and verify they fail**

Run:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_evidence_role_sampler.py -q
```

Expected: fail with missing module.

- [ ] **Step 3: Implement the sampler**

Create `backend/scripts/evidence_role_sampler.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from scripts.evidence_role_schema import write_jsonl


PACKET_SCHEMA_VERSION = "atlas-evidence-role-packet-v1"

SAMPLE_SQL = """
WITH latest AS (
    SELECT MAX(snapshot_at) AS snapshot_at
    FROM emergent_clusters
    WHERE snapshot_at > NOW() - ($1::int * INTERVAL '1 hour')
),
clusters AS (
    SELECT ec.*
    FROM emergent_clusters ec
    JOIN latest l ON l.snapshot_at = ec.snapshot_at
    ORDER BY ec.n_signals DESC, ec.raw_signal_count DESC
    LIMIT $2
),
cluster_signals AS (
    SELECT
        ec.id AS cluster_pk,
        ec.snapshot_at,
        ec.label AS cluster_label,
        ec.description AS cluster_description,
        ec.raw_signal_count,
        ec.n_signals,
        ec.cohesion,
        unnest(ec.sample_signal_ids) AS signal_id
    FROM clusters ec
),
candidate AS (
    SELECT DISTINCT ON (sta.signal_id)
        sta.signal_id,
        at.slug AS candidate_topic_slug,
        at.label AS candidate_topic_label,
        sta.confidence AS candidate_confidence,
        sta.gate_score,
        sta.gate_kept,
        COALESCE(sta.evidence->'matched_terms', '[]'::jsonb) AS matched_terms
    FROM signal_topic_assignments sta
    JOIN atlas_topics at ON at.id = sta.topic_id
    WHERE sta.method = 'lexicon'
      AND sta.model_version = 'theme-hint-lex-v2'
    ORDER BY sta.signal_id, sta.gate_score DESC NULLS LAST, sta.confidence DESC
)
SELECT
    cs.cluster_pk,
    cs.snapshot_at,
    cs.cluster_label,
    cs.cluster_description,
    cs.raw_signal_count,
    cs.n_signals,
    cs.cohesion,
    s.id AS signal_id,
    s.headline,
    s.source_name,
    s.source_lang,
    s.country_code,
    c.candidate_topic_slug,
    c.candidate_topic_label,
    c.candidate_confidence,
    c.gate_score,
    c.gate_kept,
    c.matched_terms,
    'sample_signal_id'::text AS sample_reason
FROM cluster_signals cs
JOIN signals_v2 s ON s.id = cs.signal_id
LEFT JOIN candidate c ON c.signal_id = s.id
ORDER BY cs.n_signals DESC, cs.cluster_pk, s.id
LIMIT $3;
"""


def build_cluster_id(snapshot_at: Any, cluster_pk: int) -> str:
    return f"{snapshot_at}/{cluster_pk}"


def _json_value(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, str):
        return json.loads(value)
    return value


def build_teacher_packet_row(row: dict[str, Any]) -> dict[str, Any]:
    matched_terms = _json_value(row.get("matched_terms"), [])
    return {
        "schema_version": PACKET_SCHEMA_VERSION,
        "signal_id": int(row["signal_id"]),
        "headline": row.get("headline"),
        "source_name": row.get("source_name"),
        "source_lang": row.get("source_lang"),
        "country_code": row.get("country_code"),
        "cluster_id": build_cluster_id(row["snapshot_at"], int(row["cluster_pk"])),
        "cluster_pk": int(row["cluster_pk"]),
        "snapshot_at": str(row["snapshot_at"]),
        "cluster_label": row.get("cluster_label"),
        "cluster_description": row.get("cluster_description"),
        "raw_signal_count": int(row.get("raw_signal_count") or 0),
        "n_signals": int(row.get("n_signals") or 0),
        "cohesion": float(row["cohesion"]) if row.get("cohesion") is not None else None,
        "candidate_topic_slug": row.get("candidate_topic_slug"),
        "candidate_topic_label": row.get("candidate_topic_label"),
        "candidate_confidence": float(row["candidate_confidence"]) if row.get("candidate_confidence") is not None else None,
        "gate_score": float(row["gate_score"]) if row.get("gate_score") is not None else None,
        "gate_kept": bool(row["gate_kept"]) if row.get("gate_kept") is not None else None,
        "matched_terms": matched_terms,
        "sample_reason": row.get("sample_reason", "sample_signal_id"),
        "teacher_role": None,
        "teacher_rationale": None,
    }


async def run(args: argparse.Namespace) -> list[dict[str, Any]]:
    import asyncpg

    db_url = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL or SUPABASE_DB_URL is required")

    conn = await asyncpg.connect(db_url)
    try:
        rows = await conn.fetch(SAMPLE_SQL, args.hours, args.clusters, args.limit)
    finally:
        await conn.close()
    return [build_teacher_packet_row(dict(row)) for row in rows]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sample cluster/signal rows for evidence-role teacher labeling.")
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--clusters", type=int, default=30)
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = asyncio.run(run(args))
    write_jsonl(args.output, rows)
    print(json.dumps({"rows": len(rows), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run sampler tests and verify they pass**

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_evidence_role_sampler.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Generate the first teacher packet**

Run using the worker env without printing secrets:

```bash
set -a
source /Users/pedro/AtlasLocalWorker/.env
set +a
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/evidence_role_sampler.py \
  --hours 24 \
  --clusters 30 \
  --limit 500 \
  --output docs/research/atlas-paper/phase-1-validation/evidence-role/teacher-packets/2026-06-01-evidence-role-teacher-packet.jsonl
```

Expected output includes:

```json
{
  "rows": 500,
  "output": "docs/research/atlas-paper/phase-1-validation/evidence-role/teacher-packets/2026-06-01-evidence-role-teacher-packet.jsonl"
}
```

If fewer than 300 rows are available, keep the artifact and note the exact count in `STATUS.md`.

- [ ] **Step 6: Commit Task 2**

```bash
git add backend/scripts/evidence_role_sampler.py backend/tests/test_evidence_role_sampler.py docs/research/atlas-paper/phase-1-validation/evidence-role/teacher-packets/2026-06-01-evidence-role-teacher-packet.jsonl
git commit -m "feat(validation): sample evidence role teacher packet"
```

---

### Task 3: Teacher Prompt and Offline Teacher Runner

**Files:**
- Create: `backend/scripts/evidence_role_teacher.py`
- Test: `backend/tests/test_evidence_role_teacher.py`

- [ ] **Step 1: Write failing teacher-runner tests**

Create `backend/tests/test_evidence_role_teacher.py`:

```python
from __future__ import annotations

import json

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
    raw = 'Here is the JSON:\\n{"role":"context","role_confidence":0.7,"belongs_to_cluster":true,"supports_cluster_claim":false,"reason_codes":["background_only"],"rationale":"Background only","alternate_role":"analysis"}'

    parsed = parse_teacher_json(raw)

    assert parsed["role"] == "context"
    assert parsed["reason_codes"] == ["background_only"]
```

- [ ] **Step 2: Run teacher tests and verify they fail**

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_evidence_role_teacher.py -q
```

Expected: missing module.

- [ ] **Step 3: Implement teacher prompt/parsing plus API stubs**

Create `backend/scripts/evidence_role_teacher.py` with provider selection. The runner must support `--provider deepseek`, `--provider openai`, and `--provider anthropic`. The first implementation should keep network calls behind small functions so tests do not call APIs:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
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
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("teacher response did not contain JSON object")
    return json.loads(match.group(0))


async def call_deepseek(prompt: str, model: str) -> str:
    from openai import AsyncOpenAI

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise SystemExit("DEEPSEEK_API_KEY is required for --provider deepseek")
    client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com", timeout=60.0)
    res = await client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return res.choices[0].message.content or ""


async def call_openai(prompt: str, model: str) -> str:
    from openai import AsyncOpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required for --provider openai")
    client = AsyncOpenAI(api_key=api_key, timeout=60.0)
    res = await client.chat.completions.create(
        model=model,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return res.choices[0].message.content or ""


async def call_anthropic(prompt: str, model: str) -> str:
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("ANTHROPIC_API_KEY is required for --provider anthropic")
    client = anthropic.AsyncAnthropic(api_key=api_key, timeout=60.0)
    res = await client.messages.create(
        model=model,
        max_tokens=500,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in res.content if getattr(block, "type", None) == "text")


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
    rows: list[dict[str, Any]] = []
    for packet in selected:
        rows.append(await label_one(packet, provider=args.provider, model=args.model))
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one teacher model over an evidence-role packet.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provider", choices=["deepseek", "openai", "anthropic"], required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = asyncio.run(run(args))
    write_jsonl(args.output, rows)
    print(json.dumps({"rows": len(rows), "provider": args.provider, "model": args.model, "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run teacher tests and verify they pass**

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_evidence_role_teacher.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Run a 10-row smoke with DeepSeek**

```bash
set -a
source /Users/pedro/AtlasLocalWorker/.env
set +a
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/evidence_role_teacher.py \
  --input docs/research/atlas-paper/phase-1-validation/evidence-role/teacher-packets/2026-06-01-evidence-role-teacher-packet.jsonl \
  --output docs/research/atlas-paper/phase-1-validation/labels/evidence-role-teacher/2026-06-01-deepseek-smoke.jsonl \
  --provider deepseek \
  --model deepseek-chat \
  --limit 10
```

Expected: `rows` equals `10`. Inspect without printing secrets:

```bash
head -1 docs/research/atlas-paper/phase-1-validation/labels/evidence-role-teacher/2026-06-01-deepseek-smoke.jsonl | jq '{role, reason_codes, rationale, teacher_vendor}'
```

- [ ] **Step 6: Commit Task 3**

```bash
git add backend/scripts/evidence_role_teacher.py backend/tests/test_evidence_role_teacher.py docs/research/atlas-paper/phase-1-validation/labels/evidence-role-teacher/2026-06-01-deepseek-smoke.jsonl
git commit -m "feat(validation): add evidence role teacher runner"
```

---

### Task 4: Teacher Consensus and Disagreement Packets

**Files:**
- Create: `backend/scripts/evidence_role_consensus.py`
- Test: `backend/tests/test_evidence_role_consensus.py`

- [ ] **Step 1: Write failing consensus tests**

Create `backend/tests/test_evidence_role_consensus.py`:

```python
from __future__ import annotations

from scripts.evidence_role_consensus import consensus_for_group


def test_consensus_accepts_two_of_three_role_majority():
    group = [
        {"signal_id": 1, "cluster_id": "snap/1", "role": "context", "role_confidence": 0.8, "reason_codes": ["background_only"], "teacher_vendor": "a", "rationale": "A"},
        {"signal_id": 1, "cluster_id": "snap/1", "role": "context", "role_confidence": 0.7, "reason_codes": ["same_actor"], "teacher_vendor": "b", "rationale": "B"},
        {"signal_id": 1, "cluster_id": "snap/1", "role": "reaction", "role_confidence": 0.9, "reason_codes": ["public_reaction"], "teacher_vendor": "c", "rationale": "C"},
    ]

    row = consensus_for_group(group)

    assert row["consensus_role"] == "context"
    assert row["agreement"] == "2_of_3"
    assert row["teacher_count"] == 3
    assert row["reason_codes"] == ["background_only", "same_actor"]


def test_consensus_marks_no_majority_as_disagreement():
    group = [
        {"signal_id": 1, "cluster_id": "snap/1", "role": "context", "role_confidence": 0.8, "reason_codes": [], "teacher_vendor": "a", "rationale": "A"},
        {"signal_id": 1, "cluster_id": "snap/1", "role": "reaction", "role_confidence": 0.7, "reason_codes": [], "teacher_vendor": "b", "rationale": "B"},
        {"signal_id": 1, "cluster_id": "snap/1", "role": "analysis", "role_confidence": 0.9, "reason_codes": [], "teacher_vendor": "c", "rationale": "C"},
    ]

    row = consensus_for_group(group)

    assert row["consensus_role"] is None
    assert row["agreement"] == "no_majority"
```

- [ ] **Step 2: Run consensus tests and verify they fail**

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_evidence_role_consensus.py -q
```

Expected: missing module.

- [ ] **Step 3: Implement consensus builder**

Create `backend/scripts/evidence_role_consensus.py`:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scripts.evidence_role_schema import normalize_reason_codes, read_jsonl, write_jsonl


def consensus_for_group(group: list[dict[str, Any]]) -> dict[str, Any]:
    first = group[0]
    counts = Counter(row["role"] for row in group)
    role, count = counts.most_common(1)[0]
    if count == len(group):
        agreement = f"{count}_of_{len(group)}"
        consensus_role = role
    elif count >= 2:
        agreement = f"{count}_of_{len(group)}"
        consensus_role = role
    else:
        agreement = "no_majority"
        consensus_role = None

    agreeing = [row for row in group if row["role"] == consensus_role] if consensus_role else []
    reason_codes = normalize_reason_codes(
        code for row in agreeing for code in (row.get("reason_codes") or [])
    )
    avg_conf = (
        round(sum(float(row.get("role_confidence") or 0.0) for row in agreeing) / len(agreeing), 4)
        if agreeing else None
    )

    return {
        "schema_version": "atlas-evidence-role-consensus-v1",
        "signal_id": first["signal_id"],
        "cluster_id": first["cluster_id"],
        "headline": first.get("headline"),
        "cluster_label": first.get("cluster_label"),
        "candidate_topic_slug": first.get("candidate_topic_slug"),
        "consensus_role": consensus_role,
        "consensus_confidence": avg_conf,
        "agreement": agreement,
        "teacher_count": len(group),
        "teacher_roles": dict(counts),
        "reason_codes": reason_codes,
        "rationales": [
            {
                "teacher_vendor": row.get("teacher_vendor"),
                "role": row.get("role"),
                "rationale": row.get("rationale"),
            }
            for row in group
        ],
        "is_training_gold": consensus_role is not None,
    }


def build_consensus(paths: list[Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for path in paths:
        for row in read_jsonl(path):
            grouped[(str(row["cluster_id"]), str(row["signal_id"]))].append(row)

    consensus: list[dict[str, Any]] = []
    disagreements: list[dict[str, Any]] = []
    for group in grouped.values():
        row = consensus_for_group(group)
        if row["is_training_gold"]:
            consensus.append(row)
        else:
            disagreements.append(row)
    return consensus, disagreements


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build evidence-role consensus labels from teacher outputs.")
    parser.add_argument("--teacher", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--disagreements", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    consensus, disagreements = build_consensus(args.teacher)
    write_jsonl(args.output, consensus)
    write_jsonl(args.disagreements, disagreements)
    print(json.dumps({"consensus": len(consensus), "disagreements": len(disagreements)}, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run consensus tests and verify they pass**

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_evidence_role_consensus.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Run consensus on available teacher files**

After at least two teacher files exist, run:

```bash
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/evidence_role_consensus.py \
  --teacher docs/research/atlas-paper/phase-1-validation/labels/evidence-role-teacher/2026-06-01-deepseek-smoke.jsonl \
  --teacher docs/research/atlas-paper/phase-1-validation/labels/evidence-role-teacher/2026-06-01-openai-smoke.jsonl \
  --teacher docs/research/atlas-paper/phase-1-validation/labels/evidence-role-teacher/2026-06-01-anthropic-smoke.jsonl \
  --output docs/research/atlas-paper/phase-1-validation/labels/evidence-role-consensus/2026-06-01-smoke-consensus.jsonl \
  --disagreements docs/research/atlas-paper/phase-1-validation/labels/evidence-role-consensus/2026-06-01-smoke-disagreements.jsonl
```

Expected: command prints non-negative `consensus` and `disagreements` counts. If only DeepSeek is available during first execution, skip this run and record the missing providers in `STATUS.md`.

- [ ] **Step 6: Commit Task 4**

```bash
git add backend/scripts/evidence_role_consensus.py backend/tests/test_evidence_role_consensus.py docs/research/atlas-paper/phase-1-validation/labels/evidence-role-consensus/
git commit -m "feat(validation): build evidence role teacher consensus"
```

---

### Task 5: Local Student Training and Tier Report

**Files:**
- Create: `backend/scripts/train_evidence_role_student.py`
- Test: `backend/tests/test_train_evidence_role_student.py`

- [ ] **Step 1: Write failing student report tests**

Create `backend/tests/test_train_evidence_role_student.py`:

```python
from __future__ import annotations

from scripts.train_evidence_role_student import (
    tier_from_roles,
    visible_coverage,
)


def test_tier_from_roles_promotes_verified_when_primary_evidence_is_strong():
    tier = tier_from_roles(
        [
            {"predicted_role": "primary_evidence", "role_score": 0.91},
            {"predicted_role": "primary_evidence", "role_score": 0.87},
            {"predicted_role": "context", "role_score": 0.75},
        ]
    )

    assert tier == "verified"


def test_tier_from_roles_marks_mixed_evidence_as_candidate():
    tier = tier_from_roles(
        [
            {"predicted_role": "primary_evidence", "role_score": 0.72},
            {"predicted_role": "reaction", "role_score": 0.84},
            {"predicted_role": "context", "role_score": 0.81},
        ]
    )

    assert tier == "candidate"


def test_visible_coverage_excludes_suppressed():
    rows = [
        {"tier": "verified"},
        {"tier": "candidate"},
        {"tier": "context_rich"},
        {"tier": "suppressed"},
    ]

    assert visible_coverage(rows) == 0.75
```

- [ ] **Step 2: Run student tests and verify they fail**

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_train_evidence_role_student.py -q
```

Expected: missing module.

- [ ] **Step 3: Implement minimal tiering and student training shell**

Create `backend/scripts/train_evidence_role_student.py` with tier helpers first. The training body can start with scikit-learn logistic regression once there are enough consensus labels, but the helper tests should pass immediately:

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.evidence_role_schema import read_jsonl


VISIBLE_TIERS = {"verified", "candidate", "context_rich"}


def tier_from_roles(rows: list[dict[str, Any]]) -> str:
    primary = [r for r in rows if r.get("predicted_role") == "primary_evidence"]
    non_noise = [r for r in rows if r.get("predicted_role") != "noise"]
    context_like = [
        r for r in rows
        if r.get("predicted_role") in {"context", "reaction", "analysis", "entity_reference"}
    ]

    strong_primary = [r for r in primary if float(r.get("role_score") or 0.0) >= 0.85]
    if len(strong_primary) >= 2:
        return "verified"
    if primary and len(non_noise) >= 2:
        return "candidate"
    if len(context_like) >= 2:
        return "context_rich"
    return "suppressed"


def visible_coverage(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    visible = sum(1 for row in rows if row.get("tier") in VISIBLE_TIERS)
    return round(visible / len(rows), 4)


def summarize_consensus(rows: list[dict[str, Any]]) -> dict[str, Any]:
    role_counts = Counter(row.get("consensus_role") for row in rows)
    training_rows = [row for row in rows if row.get("is_training_gold")]
    return {
        "schema_version": "atlas-evidence-role-student-report-v1",
        "training_rows": len(training_rows),
        "role_counts": dict(role_counts),
        "status": "needs_more_labels" if len(training_rows) < 100 else "ready_for_student_training",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train/evaluate the local evidence-role student.")
    parser.add_argument("--consensus", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_jsonl(args.consensus)
    report = summarize_consensus(rows)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run student tests and verify they pass**

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_train_evidence_role_student.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Produce the first student readiness report**

```bash
PYTHONPATH=backend backend/.venv/bin/python backend/scripts/train_evidence_role_student.py \
  --consensus docs/research/atlas-paper/phase-1-validation/labels/evidence-role-consensus/2026-06-01-smoke-consensus.jsonl \
  --report docs/research/atlas-paper/phase-1-validation/reports/evidence-role/2026-06-01-student-readiness.json
```

Expected: report status is `needs_more_labels` until at least 100 consensus rows exist.

- [ ] **Step 6: Commit Task 5**

```bash
git add backend/scripts/train_evidence_role_student.py backend/tests/test_train_evidence_role_student.py docs/research/atlas-paper/phase-1-validation/reports/evidence-role/
git commit -m "feat(validation): add evidence role student readiness report"
```

---

### Task 6: Obsidian Connections and Operating Docs

**Files:**
- Modify: `docs/000-INDEX.md`
- Modify: `docs/maps/Narrative Intelligence.md`
- Modify: `docs/maps/Validation and Paper Track.md`
- Modify: `SESSION_LOG.md`
- Modify: `STATUS.md`
- Optionally regenerate: `docs/state/PROJECT_INVENTORY.md`

- [ ] **Step 1: Update Obsidian entry point**

Add a bullet under the relevant section of `docs/000-INDEX.md`:

```markdown
- [[2026-06-01-narrative-cluster-evidence-roles-design]] — teacher-student
  role layer for classifying evidence inside narrative clusters.
```

- [ ] **Step 2: Update Narrative Intelligence MOC**

Ensure `docs/maps/Narrative Intelligence.md` links both the design spec and the active artifacts:

```markdown
- [[2026-06-01-narrative-cluster-evidence-roles-design]] — role-aware
  cluster/thread classification design.
- Evidence-role pilot artifacts:
  `docs/research/atlas-paper/phase-1-validation/evidence-role/`.
```

- [ ] **Step 3: Update Validation and Paper Track MOC**

Ensure `docs/maps/Validation and Paper Track.md` includes:

```markdown
- [[2026-06-01-narrative-cluster-evidence-roles-design]] — teacher-student
  design for classifying evidence roles inside narrative clusters.
- Evidence-role teacher/student reports:
  `docs/research/atlas-paper/phase-1-validation/reports/evidence-role/`.
```

- [ ] **Step 4: Update `STATUS.md`**

Add to the current handoff:

```markdown
- Evidence-role teacher-student pilot started from
  `docs/superpowers/specs/2026-06-01-narrative-cluster-evidence-roles-design.md`.
  The goal is to keep `verified` claims at >=90% precision while recovering
  >=80% visible coverage through `candidate` and `context_rich` tiers.
```

- [ ] **Step 5: Update `SESSION_LOG.md`**

Add a 2026-06-01 line:

```markdown
- Started the Narrative Cluster Evidence Roles pilot plan: teacher LLMs provide
  roles, rationales, and reason codes offline; a local student model is the
  intended production classifier.
```

- [ ] **Step 6: Run docs/search verification**

```bash
rg -n "narrative-cluster-evidence-roles|evidence-role|teacher-student|context_rich" \
  docs/000-INDEX.md docs/maps docs/superpowers/specs docs/superpowers/plans STATUS.md SESSION_LOG.md
```

Expected: hits in index, both MOCs, spec, plan, status, and session log.

- [ ] **Step 7: Commit Task 6**

```bash
git add docs/000-INDEX.md docs/maps/Narrative\ Intelligence.md docs/maps/Validation\ and\ Paper\ Track.md STATUS.md SESSION_LOG.md
git commit -m "docs(obsidian): connect evidence role pilot"
```

---

### Task 7: Full Verification Before Promotion

**Files:**
- No new files unless generated reports changed.

- [ ] **Step 1: Run focused unit tests**

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest \
  backend/tests/test_evidence_role_schema.py \
  backend/tests/test_evidence_role_sampler.py \
  backend/tests/test_evidence_role_teacher.py \
  backend/tests/test_evidence_role_consensus.py \
  backend/tests/test_train_evidence_role_student.py \
  -q
```

Expected: all tests pass.

- [ ] **Step 2: Run Python syntax checks**

```bash
backend/.venv/bin/python -m py_compile \
  backend/scripts/evidence_role_schema.py \
  backend/scripts/evidence_role_sampler.py \
  backend/scripts/evidence_role_teacher.py \
  backend/scripts/evidence_role_consensus.py \
  backend/scripts/train_evidence_role_student.py
```

Expected: no output and exit code 0.

- [ ] **Step 3: Verify no secrets were written**

```bash
rg -n "sk-|DEEPSEEK_API_KEY|ANTHROPIC_API_KEY|OPENAI_API_KEY|DATABASE_URL" \
  docs/research/atlas-paper/phase-1-validation/evidence-role \
  docs/research/atlas-paper/phase-1-validation/labels/evidence-role-teacher \
  docs/research/atlas-paper/phase-1-validation/labels/evidence-role-consensus \
  docs/research/atlas-paper/phase-1-validation/reports/evidence-role
```

Expected: no matches.

- [ ] **Step 4: Verify git diff health**

```bash
git diff --check
git status --short
```

Expected: no whitespace errors. Remaining changes should be intentional generated artifacts or docs.

- [ ] **Step 5: Write final implementation note**

Add a short note to `STATUS.md` with:

```markdown
- Evidence-role pilot verification: focused tests pass; no secrets found in
  generated artifacts; current student status is `<status from report>`.
```

- [ ] **Step 6: Commit final verification note**

```bash
git add STATUS.md
git commit -m "docs(status): record evidence role pilot verification"
```

---

## Self-Review

Spec coverage:

- Teacher-student architecture: Tasks 1, 3, 4, 5.
- LLM rationales and reason codes: Tasks 1 and 3.
- File-based pilot before tables: Tasks 2 through 5.
- Local student and no production LLM inference: Task 5.
- Obsidian/MOC documentation path: Task 6.
- Metrics around visible coverage and verified precision: Tasks 5 and 7.

Placeholder scan:

- No placeholder, incomplete, or deferred-implementation markers are present.
- Future table work is explicitly excluded from this plan and remains in the spec as a later candidate.

Type consistency:

- Teacher labels use `role`; consensus labels use `consensus_role`; student report helpers use `predicted_role`.
- Cluster IDs use the stable string format `<snapshot_at>/<cluster_pk>`.
- Artifact paths match the spec's file-based pilot directories.
