"""Unified Engine F3.2b — LLM-judged recall confirmation (spec §11, the F4 gate).

The embedding-coherence surplus test (engine_ab_report.py) shows v1's surplus
members are looser than its shared members — evidence that v2's lower member
count is avoided over-assignment, not lost signal. This script confirms that with
an INDEPENDENT modality: an LLM judges, for a stratified sample, whether each
signal is genuinely on-topic for the topic its engine assigned it to.

Strata:
  v1_only  — assigned by v1-compat, NOT by unified-v2 (the disputed surplus)
  shared   — assigned by BOTH (judged against v1's atlas label)
  v2_only  — assigned by unified-v2, NOT by v1 (v2's distinctive picks)

If v1_only on-topic rate < shared and < v2_only, v1's surplus is over-assignment
→ v2's effective recall does not regress → strengthens the F4 cutover case.
Conservative by design: v1's atlas labels are BROAD categories (easier to be
"on-topic" for) than v2's specific dynamic-topic labels, so a v1_only deficit is
a lower bound on the effect.

Run (worker, DEEPSEEK_API_KEY in env): python -m backend.scripts.engine_recall_judge --n 40
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

import asyncpg
import httpx

DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
MODEL = os.getenv("DEEPSEEK_JUDGE_MODEL", "deepseek-chat")

_V1_ONLY = """
SELECT s.id, s.headline, at.label AS topic_label
FROM topic_members tm
JOIN signals_v2 s ON s.id = tm.signal_id
JOIN atlas_topics at ON at.slug = tm.topic_id
WHERE tm.engine_version='v1-compat' AND tm.role='evidence'
  AND s.headline IS NOT NULL AND length(s.headline) >= 20
  AND NOT EXISTS (SELECT 1 FROM topic_members v2
                  WHERE v2.signal_id=tm.signal_id AND v2.engine_version='unified-v2'
                    AND v2.role='evidence')
ORDER BY random() LIMIT $1
"""

_SHARED = """
SELECT s.id, s.headline, at.label AS topic_label
FROM topic_members tm
JOIN signals_v2 s ON s.id = tm.signal_id
JOIN atlas_topics at ON at.slug = tm.topic_id
WHERE tm.engine_version='v1-compat' AND tm.role='evidence'
  AND s.headline IS NOT NULL AND length(s.headline) >= 20
  AND EXISTS (SELECT 1 FROM topic_members v2
              WHERE v2.signal_id=tm.signal_id AND v2.engine_version='unified-v2'
                AND v2.role='evidence')
ORDER BY random() LIMIT $1
"""

_V2_ONLY = """
SELECT s.id, s.headline, dt.label AS topic_label
FROM topic_members tm
JOIN signals_v2 s ON s.id = tm.signal_id
JOIN dynamic_topics dt ON ('dynamic-topic-' || dt.id) = tm.topic_id
WHERE tm.engine_version='unified-v2' AND tm.role='evidence'
  AND s.headline IS NOT NULL AND length(s.headline) >= 20
  AND NOT EXISTS (SELECT 1 FROM topic_members v1
                  WHERE v1.signal_id=tm.signal_id AND v1.engine_version='v1-compat'
                    AND v1.role='evidence')
ORDER BY random() LIMIT $1
"""


async def _judge(client: httpx.AsyncClient, api_key: str, headline: str, label: str) -> bool | None:
    prompt = (
        "You judge whether a news headline is genuinely ABOUT a given topic.\n"
        f'Headline: "{headline}"\n'
        f'Topic: "{label}"\n'
        'Reply ONLY JSON: {"on_topic": true} or {"on_topic": false}. '
        "true only if the headline is substantively about that topic."
    )
    try:
        r = await client.post(
            DEEPSEEK_API_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": MODEL, "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.0, "max_tokens": 20,
                  "response_format": {"type": "json_object"}},
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        return bool(json.loads(content).get("on_topic"))
    except Exception as exc:  # noqa: BLE001
        print(f"  judge error: {str(exc)[:80]}", file=sys.stderr)
        return None


async def _score_stratum(client, api_key, rows, sem) -> tuple[int, int]:
    async def one(row):
        async with sem:
            return await _judge(client, api_key, row["headline"], row["topic_label"])
    verdicts = await asyncio.gather(*[one(r) for r in rows])
    valid = [v for v in verdicts if v is not None]
    return sum(valid), len(valid)


async def run(n: int) -> int:
    dsn = os.environ.get("DATABASE_URL")
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not dsn or not api_key:
        print("need DATABASE_URL and DEEPSEEK_API_KEY", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(dsn)
    try:
        strata = {
            "v1_only": await conn.fetch(_V1_ONLY, n),
            "shared": await conn.fetch(_SHARED, n),
            "v2_only": await conn.fetch(_V2_ONLY, n),
        }
    finally:
        await conn.close()

    sem = asyncio.Semaphore(6)
    results = {}
    async with httpx.AsyncClient(timeout=30.0) as client:
        for name, rows in strata.items():
            on, tot = await _score_stratum(client, api_key, rows, sem)
            rate = on / tot if tot else 0.0
            results[name] = {"on_topic": on, "judged": tot, "rate": rate}
            print(f"  {name:9s}: {on}/{tot} on-topic = {rate:.1%}")

    v1o = results["v1_only"]["rate"]
    sh = results["shared"]["rate"]
    v2o = results["v2_only"]["rate"]
    print("\n=== verdict ===")
    # CONFOUND CHECK FIRST: 'shared' members were assigned by BOTH engines (highest
    # confidence). If even they score low on-topic, the judge is measuring LABEL /
    # taxonomy precision, not engine recall — the strata are not comparable because
    # v1 uses BROAD atlas labels and v2 uses SPECIFIC (sometimes stale) dynamic
    # labels. In that regime this test cannot arbitrate the cutover.
    if sh < 0.65:
        print(f"  CONFOUNDED — shared on-topic is only {sh:.0%}. Members BOTH engines "
              f"assigned still miss their label, so this measures label/taxonomy "
              f"precision (broad atlas vs specific dynamic), not recall. Do NOT use "
              f"to arbitrate F4. Finding: topical precision vs the current taxonomy "
              f"is ~{sh:.0%} for both engines → the dominant lever is taxonomy/label "
              f"quality (#204) + the gate, NOT the engine architecture. The "
              f"label-INDEPENDENT coherence/black-hole A/B remains the primary evidence.")
    elif v1o < sh and v1o <= v2o:
        print(f"  CONFIRMS over-assignment: v1_only ({v1o:.0%}) < shared ({sh:.0%}) "
              f"and <= v2_only ({v2o:.0%}). v2's member gap is avoided noise — LLM "
              f"judge agrees with the coherence test. F4 case strengthened.")
    else:
        print(f"  INCONCLUSIVE/contra: v1_only={v1o:.0%} shared={sh:.0%} v2_only={v2o:.0%}.")
    print(json.dumps(results, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40, help="sample size per stratum")
    args = ap.parse_args()
    return asyncio.run(run(args.n))


if __name__ == "__main__":
    raise SystemExit(main())
