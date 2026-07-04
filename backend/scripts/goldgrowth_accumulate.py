#!/usr/bin/env python3
"""Nightly gold-growth accumulator (2026-07-04 finding follow-through).

Round 1 proved per-topic gate thresholds are HIGH-VARIANCE at 40-60 positives
(election-legit recall@90 swung 0.39→0.55→0.24 across corpus variants). The
fix is VOLUME: accumulate 2-vendor consensus labels nightly until each hard
topic holds >=TARGET_POS positives, THEN retrain once with variance-aware
calibration. This driver does one night's increment:

  1. sample up to N_PER_TOPIC decision-band candidates per under-target topic
     (7d window, stratified over gate_score, excluding already-labeled ids),
  2. label with DeepSeek + gpt-4o-mini (llm_annotator.py, sequential, mindful),
  3. keep 2-vendor unanimous rows (build_goldgrowth_corpus.py),
  4. append to the accumulating corpus + report per-topic positive counts.

Cost: ~$0.10-0.30/night. API-bound, CPU-trivial — safe on the M1 off-peak.
State lives in --state-dir (default ~/AtlasLocalWorker/goldgrowth/):
  accumulated-corpus.jsonl   the growing consensus gold
  labeled-ids.txt            every signal_id ever sent to annotators
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HARD_TOPICS = [
    "election-legitimacy-dispute", "oil-gas-supply-risk", "currency-debt-stress",
    "telecom-internet-shutdown", "sanctions-diplomatic-pressure",
    "agriculture-crop-risk", "gang-control-urban-security", "fuel-subsidy-unrest",
]
TARGET_POS = 200          # stop sampling a topic once it holds this many positives
N_PER_TOPIC = 20          # nightly increment per topic (4 score bands x 5)
BASE_POS = {              # positives already in the frozen 5k corpus (2026-05-28)
    "election-legitimacy-dispute": 38, "oil-gas-supply-risk": 30,
    "currency-debt-stress": 38, "telecom-internet-shutdown": 44,
    "sanctions-diplomatic-pressure": 36, "agriculture-crop-risk": 62,
    "gang-control-urban-security": 0, "fuel-subsidy-unrest": 0,
}

SCRIPTS = Path(__file__).resolve().parent


def accumulated_positives(corpus: Path) -> dict[str, int]:
    pos: dict[str, int] = {}
    if corpus.exists():
        for line in corpus.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("is_evidence") == 1:
                pos[r["assigned_topic_slug"]] = pos.get(r["assigned_topic_slug"], 0) + 1
    return pos


async def sample(state_dir: Path, out: Path, topics: list[str], seen: set[int]) -> int:
    import asyncpg
    conn = await asyncpg.connect(os.environ["DATABASE_URL"], statement_cache_size=0)
    n_out = 0
    try:
        with out.open("w", encoding="utf-8") as f:
            for slug in topics:
                rows = await conn.fetch("""
                  WITH pool AS (
                    SELECT s.id AS signal_id, s.headline, s.source_lang, s.country_code,
                           s.source_name, s.themes, t.slug, t.label,
                           a.confidence, a.evidence,
                           width_bucket(a.gate_score, 0.10, 0.999, 4) AS band,
                           row_number() OVER (PARTITION BY width_bucket(a.gate_score, 0.10, 0.999, 4)
                                              ORDER BY random()) AS rn
                    FROM signal_topic_assignments a
                    JOIN atlas_topics t ON t.id=a.topic_id
                    JOIN signals_v2 s ON s.id=a.signal_id
                    WHERE t.slug=$1 AND a.model_version='theme-hint-lex-v2'
                      AND a.gate_score BETWEEN 0.10 AND 0.999
                      AND s.headline IS NOT NULL AND length(s.headline)>=25
                      AND s.timestamp > now()-interval '7 days'
                  )
                  SELECT * FROM pool WHERE rn <= $2 ORDER BY band, rn
                """, slug, max(5, N_PER_TOPIC // 4 + 4))
                taken = 0
                for r in rows:
                    sid = int(r["signal_id"])
                    if sid in seen or taken >= N_PER_TOPIC:
                        continue
                    ev = r["evidence"]
                    if isinstance(ev, str):
                        try:
                            ev = json.loads(ev)
                        except Exception:
                            ev = {}
                    f.write(json.dumps({
                        "signal_id": sid, "headline": r["headline"],
                        "source_lang": r["source_lang"], "country_code": r["country_code"],
                        "source_family": "gdelt", "source_name": r["source_name"],
                        "themes": list(r["themes"] or [])[:6],
                        "assigned_topic_slug": r["slug"],
                        "assigned_topic_label": r["label"],
                        "atlas_confidence": float(r["confidence"] or 0),
                        "atlas_matched_terms": float(len((ev or {}).get("matched_terms") or [])),
                    }, ensure_ascii=False) + "\n")
                    seen.add(sid)
                    taken += 1
                    n_out += 1
    finally:
        await conn.close()
    return n_out


def annotate(py: str, cands: Path, out: Path, model: str, prov: str) -> None:
    subprocess.run([py, str(SCRIPTS / "llm_annotator.py"),
                    "--input", str(cands), "--output", str(out),
                    "--model", model, "--provenance", prov, "--resume"],
                   check=True, timeout=3600)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", type=Path,
                    default=Path.home() / "AtlasLocalWorker" / "goldgrowth")
    args = ap.parse_args()
    sd = args.state_dir
    sd.mkdir(parents=True, exist_ok=True)
    corpus = sd / "accumulated-corpus.jsonl"
    labeled = sd / "labeled-ids.txt"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    py = sys.executable

    # which topics still need positives?
    acc = accumulated_positives(corpus)
    open_topics = [t for t in HARD_TOPICS
                   if BASE_POS.get(t, 0) + acc.get(t, 0) < TARGET_POS]
    if not open_topics:
        print("[goldgrowth] all topics at target — nothing to do")
        return
    print(f"[goldgrowth] topics under target: {open_topics}")

    seen: set[int] = set()
    if labeled.exists():
        seen = {int(x) for x in labeled.read_text().split() if x.strip()}

    cands = sd / f"candidates-{stamp}.jsonl"
    n = asyncio.run(sample(sd, cands, open_topics, seen))
    if n == 0:
        print("[goldgrowth] no fresh candidates in the decision band tonight")
        return
    print(f"[goldgrowth] sampled {n} candidates")

    va = sd / f"votes-ds-{stamp}.jsonl"
    vb = sd / f"votes-gpt-{stamp}.jsonl"
    annotate(py, cands, va, "deepseek-chat", f"deepseek_goldgrowth_{stamp}")
    annotate(py, cands, vb, "gpt-4o-mini", f"gpt4omini_goldgrowth_{stamp}")

    merged = sd / f"consensus-{stamp}.jsonl"
    subprocess.run([py, str(SCRIPTS / "build_goldgrowth_corpus.py"),
                    "--candidates", str(cands), "--votes-a", str(va),
                    "--votes-b", str(vb), "--out", str(merged)],
                   check=True, timeout=600)

    # append to the accumulating corpus + persist labeled ids
    with corpus.open("a", encoding="utf-8") as f:
        f.write(merged.read_text(encoding="utf-8"))
    with labeled.open("w", encoding="utf-8") as f:
        f.write("\n".join(str(s) for s in sorted(seen)))

    acc = accumulated_positives(corpus)
    print("[goldgrowth] per-topic positives (base + accumulated / target):")
    for t in HARD_TOPICS:
        print(f"  {t:34} {BASE_POS.get(t, 0):3d} + {acc.get(t, 0):3d} / {TARGET_POS}")


if __name__ == "__main__":
    main()
