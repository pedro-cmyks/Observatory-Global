#!/usr/bin/env python3
"""Archive gold miner (Day 1 of the 3-day route, 2026-07-04).

The hot DB holds only 7 days; the external archive holds ~2 months of raw
headlines (May 3+ — the whole Peru electoral arc). This mines it for
hard-topic gold candidates so the gate retrain doesn't wait 2 weeks for the
nightly accumulator:

  1. Stream every archive partition (gzip jsonl, signals/ + incremental/).
  2. Offline lexicon match — the SAME rule as theme-hint-lex-v2's lex lane
     (distinct lexicon terms substring-matching the lowercased, HTML-unescaped
     headline). No DB writes, no gate scores needed (labels don't depend on
     scores; stratification uses matched-term count instead).
  3. Per-topic stratified sample (by lex_count 1 / 2 / 3+), dedup vs
     everything ever labeled (accumulated ids + the frozen 5k corpus) AND by
     normalized headline (syndication kills gold diversity).
  4. Attach candidate-v2 category boundaries (the #204 wiring) so the
     annotators judge against sharp includes/excludes.

Output: a candidates jsonl ready for llm_annotator (sharded by the caller).
Read-only on the archive; CPU-light streaming (~1.5GB gz).
"""
from __future__ import annotations

import argparse
import gzip
import html
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from goldgrowth_accumulate import load_category_boundaries  # noqa: E402

ARCHIVE = Path("/Volumes/Ext/Atlas/Archive")


def norm_headline(h: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(h or "").lower()).strip()


def load_lexicons(path: Path) -> list[dict]:
    topics = json.loads(path.read_text(encoding="utf-8"))
    for t in topics:
        t["terms_lc"] = [term.lower() for term in (t["terms"] or [])]
    return topics


def already_labeled_ids(state_dir: Path, corpus_5k: Path) -> set[int]:
    seen: set[int] = set()
    f = state_dir / "labeled-ids.txt"
    if f.exists():
        seen |= {int(x) for x in f.read_text().split() if x.strip()}
    if corpus_5k.exists():
        for line in corpus_5k.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    seen.add(int(json.loads(line)["signal_id"]))
                except Exception:
                    pass
    return seen


def iter_archive_rows():
    files = sorted(ARCHIVE.rglob("part-*.jsonl.gz"))
    print(f"[miner] {len(files)} partition files", file=sys.stderr)
    for i, fp in enumerate(files):
        try:
            with gzip.open(fp, "rt", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.strip():
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            continue
        except OSError:
            continue
        if (i + 1) % 100 == 0:
            print(f"[miner] {i+1} files scanned", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lexicons", type=Path, default=Path("/tmp/goldgrowth/hard-topic-lexicons.json"))
    ap.add_argument("--state-dir", type=Path, default=Path.home() / "AtlasLocalWorker" / "goldgrowth")
    ap.add_argument("--corpus-5k", type=Path, default=Path(
        "/Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/docs/research/atlas-paper/"
        "phase-1-validation/labels/consensus/2026-05-28-3vendor-5k-consensus-corpus.jsonl"))
    ap.add_argument("--per-topic", type=int, default=520)
    ap.add_argument("--out", type=Path, default=Path("/tmp/goldgrowth/archive-candidates.jsonl"))
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    topics = load_lexicons(args.lexicons)
    boundaries = load_category_boundaries()
    labeled = already_labeled_ids(args.state_dir, args.corpus_5k)
    print(f"[miner] dedup base: {len(labeled)} labeled ids", file=sys.stderr)

    # per topic → per stratum (lex_count 1, 2, 3+) → list of rows
    pools: dict[str, dict[int, list[dict]]] = {t["slug"]: defaultdict(list) for t in topics}
    seen_headlines: set[str] = set()
    n_rows = 0
    for r in iter_archive_rows():
        n_rows += 1
        h = r.get("headline") or ""
        if len(h) < 25:
            continue
        hl = norm_headline(h)
        for t in topics:
            matched = [term for term in t["terms_lc"] if term in hl]
            if not matched:
                continue
            try:
                sid = int(r.get("id") or -1)
            except (TypeError, ValueError):
                continue
            if sid in labeled or (t["slug"] + "|" + hl) in seen_headlines:
                continue
            seen_headlines.add(t["slug"] + "|" + hl)
            stratum = min(len(matched), 3)
            themes = r.get("themes")
            if isinstance(themes, str):
                try:
                    themes = json.loads(themes.replace("'", '"'))
                except Exception:
                    themes = []
            b = boundaries.get(t["slug"], {})
            pools[t["slug"]][stratum].append({
                "signal_id": sid,
                "headline": html.unescape(h),
                "source_lang": r.get("source_lang"),
                "country_code": r.get("country_code"),
                "source_family": r.get("source_family") or "gdelt",
                "source_name": r.get("source_name"),
                "themes": (themes or [])[:6],
                "assigned_topic_slug": t["slug"],
                "assigned_topic_label": t["label"],
                "atlas_confidence": 0.55 + 0.10 * min(len(matched), 3),
                "atlas_matched_terms": float(len(matched)),
                "archive_origin": str(r.get("timestamp") or "")[:10],
                **({"category_definition": b.get("definition"),
                    "category_includes": b.get("includes"),
                    "category_excludes": b.get("excludes")} if b else {}),
            })
    print(f"[miner] scanned {n_rows} rows", file=sys.stderr)

    rng = random.Random(args.seed)
    out_rows: list[dict] = []
    print(f"{'topic':32} {'s1':>6} {'s2':>5} {'s3+':>5} {'sampled':>8}")
    for slug, strata in pools.items():
        total_avail = sum(len(v) for v in strata.values())
        # favor multi-term matches (higher prior of true positives) but keep
        # single-term majority — the boundary zone lives there
        want = args.per_topic
        take3 = min(len(strata[3]), want // 4)
        take2 = min(len(strata[2]), want // 4)
        take1 = min(len(strata[1]), want - take3 - take2)
        picked = (rng.sample(strata[3], take3) + rng.sample(strata[2], take2)
                  + rng.sample(strata[1], take1))
        out_rows.extend(picked)
        print(f"{slug:32} {len(strata[1]):>6} {len(strata[2]):>5} {len(strata[3]):>5} {len(picked):>8}"
              + (f"  (avail {total_avail})" if total_avail < want else ""))

    rng.shuffle(out_rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for r in out_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"[miner] {len(out_rows)} candidates -> {args.out}")


if __name__ == "__main__":
    main()
