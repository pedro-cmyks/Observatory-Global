#!/usr/bin/env python3
"""Label a cluster of headlines with the LOCAL Claude CLI (Max subscription).

Replaces the per-call DeepSeek API for topic (re)labeling: the cron runs on the
M1, which already has the `claude` CLI authenticated against Pedro's Max plan, so
labeling costs $0 marginal instead of a metered external call. Same prompt shape
and JSON contract as the old DeepSeek labeler (scripts/emergent_poc.LABEL_PROMPT)
so downstream readers are unchanged.

Pure helpers (prompt build + response parse) are import-safe and unit-tested; the
subprocess call is isolated in label_via_claude().
"""

from __future__ import annotations

import json
import re
import subprocess

# Same contract as the prior DeepSeek labeler so consumers don't change.
LABEL_PROMPT = """You are labeling a cluster of news headlines for a narrative intelligence brief.

Given these representative headlines:

{headlines}

Return JSON only, no other text:
{{
  "label": "3-5 word topic name in title case",
  "description": "one-line description of what this cluster is about",
  "confidence": 0.0-1.0
}}"""

LABEL_MODEL = "claude-cli"
_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def build_prompt(headlines: list[str]) -> str:
    return LABEL_PROMPT.format(headlines="\n".join(f"- {h}" for h in headlines if h))


def parse_label_response(text: str) -> dict:
    """Extract the JSON label object from raw CLI stdout.

    Tolerant of markdown code fences and surrounding prose: tries a fenced block
    first, then the outermost {...} span. Returns a failure stub (never raises)
    so a single bad response can't crash a batch relabel run.
    """
    if not text or not text.strip():
        return {"label": "(label failed)", "description": "empty response", "confidence": 0.0}
    candidates: list[str] = []
    m = _FENCE.search(text)
    if m:
        candidates.append(m.group(1))
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(text[start:end + 1])
    candidates.append(text.strip())
    for c in candidates:
        try:
            obj = json.loads(c)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(obj, dict) and obj.get("label"):
            return {
                "label": str(obj["label"]).strip(),
                "description": str(obj.get("description") or "").strip(),
                "confidence": float(obj.get("confidence") or 0.0),
            }
    return {"label": "(label failed)", "description": "unparseable response", "confidence": 0.0}


def label_via_claude(headlines: list[str], *, timeout: float = 60.0, model: str | None = None) -> dict:
    """Run the local `claude` CLI once to label a headline cluster.

    Uses `claude -p` (non-interactive, prints the response to stdout). Returns a
    failure stub on any CLI / parse error — labeling must never abort the cron.
    """
    prompt = build_prompt(headlines)
    cmd = ["claude", "-p", prompt]
    if model:
        cmd += ["--model", model]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False,
        )
    except FileNotFoundError:
        return {"label": "(label failed)", "description": "claude CLI not found", "confidence": 0.0}
    except subprocess.TimeoutExpired:
        return {"label": "(label failed)", "description": "claude CLI timeout", "confidence": 0.0}
    if proc.returncode != 0:
        return {
            "label": "(label failed)",
            "description": (proc.stderr or "claude CLI nonzero exit")[:120],
            "confidence": 0.0,
        }
    return parse_label_response(proc.stdout)
