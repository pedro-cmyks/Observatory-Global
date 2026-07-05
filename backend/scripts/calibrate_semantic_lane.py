#!/usr/bin/env python
"""tau_sem calibration for the semantic assignment lane (v1).

Spec: docs/specs/2026-07-04-semantic-assignment-lane.md (threshold discipline:
measure, never guess).

v0 finding (2026-07-04, e5 absolute-cosine): FAILED — pos/neg medians 0.789
vs 0.765, global AUC 0.735, cross-fire 3169/3186 positives firing foreign
anchors above their taus. Raw absolute cosine in e5 headline space cannot be
a candidate rule (same noise floor as the 2026-06-29 ablations; text-rich
anchors do not fix it).

v1 therefore measures TWO candidate rules x TWO embedding engines:
  rule=absolute : candidate (row, T) iff cos(row, anchor_T) >= tau_T
  rule=argmax   : candidate iff T == argmax_T' cos AND cos >= tau_T
                  (max one candidate per row -> cross-fire impossible)
  engine=e5     : intfloat/multilingual-e5-base, substrate conventions
  engine=openai : text-embedding-3-small, bare text (no prefix) — the same
                  space that beat e5 for the gate (0.843 vs 0.749 @90%)

Caveat reported in output: the gold corpus is a lexicon-biased sample, so
precision measured here is an UPPER bound for wild-corpus behavior.

Usage:
  mlvenv/bin/python backend/scripts/calibrate_semantic_lane.py \
      --corpus /tmp/goldgrowth/mega2-corpus.jsonl \
      --taxonomy docs/research/taxonomy-revision/candidate-v2.json \
      --engine e5 \
      --out docs/research/semantic-lane/2026-07-04-tau-sem-e5
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys
from pathlib import Path

import numpy as np

E5_MODEL = "intfloat/multilingual-e5-base"
OPENAI_MODEL = "text-embedding-3-small"
PRECISION_FLOORS = (0.5, 0.6, 0.7)
PRIMARY_FLOOR = 0.6
MIN_KEPT = 5


def build_e5_embedder(max_length: int):
    import torch
    from transformers import AutoModel, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(E5_MODEL)
    model = AutoModel.from_pretrained(E5_MODEL)
    model.eval()
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    model.to(device)

    @torch.no_grad()
    def embed(texts: list[str], batch: int = 64) -> np.ndarray:
        out: list[list[float]] = []
        for i in range(0, len(texts), batch):
            chunk = texts[i : i + batch]
            enc = tok(chunk, padding=True, truncation=True,
                      max_length=max_length, return_tensors="pt").to(device)
            hs = model(**enc).last_hidden_state
            mask = enc["attention_mask"].unsqueeze(-1).float()
            pooled = (hs * mask).sum(1) / mask.sum(1).clamp(min=1e-9)
            pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
            out.extend([[float(x) for x in row] for row in pooled.cpu()])
        return np.array(out, dtype=np.float32)

    return embed


def openai_embed(texts: list[str]) -> np.ndarray:
    import openai
    client = openai.OpenAI(timeout=120.0)
    vecs: list[list[float]] = []
    for i in range(0, len(texts), 512):
        chunk = [t[:2000] for t in texts[i : i + 512]]
        for attempt in range(1, 6):
            try:
                resp = client.embeddings.create(model=OPENAI_MODEL, input=chunk)
                break
            except Exception:  # noqa: BLE001
                if attempt == 5:
                    raise
                import time
                time.sleep(2.0 * attempt)
        vecs.extend(d.embedding for d in resp.data)
        print(f"  openai embedded {min(i + 512, len(texts))}/{len(texts)}",
              file=sys.stderr)
    a = np.asarray(vecs, dtype=np.float32)
    return a / np.linalg.norm(a, axis=1, keepdims=True)


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    all_ = np.concatenate([pos, neg])
    ranks = all_.argsort().argsort().astype(np.float64) + 1
    rp = ranks[: len(pos)].sum()
    return float((rp - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def threshold_at_floor(sims: np.ndarray, y: np.ndarray, floor: float):
    """Lowest tau with kept-precision >= floor and >= MIN_KEPT kept."""
    if len(sims) == 0:
        return None
    order = np.argsort(-sims)
    s_sorted, y_sorted = sims[order], y[order]
    tp = np.cumsum(y_sorted)
    kept = np.arange(1, len(y_sorted) + 1)
    prec = tp / kept
    total_pos = int(y.sum())
    best = None
    for i in range(len(s_sorted)):
        if kept[i] < MIN_KEPT:
            continue
        if prec[i] >= floor:
            best = (float(s_sorted[i]), float(prec[i]),
                    float(tp[i] / total_pos) if total_pos else 0.0, int(kept[i]))
    return best


def sweep_rule(slugs, idx, sims_all, topic_i, y, mask_fn):
    """Per-topic floor sweep where eligibility is defined by mask_fn(i, j):
    absolute rule -> always True; argmax rule -> j == top1(i)."""
    per_topic = {}
    for s in slugs:
        j = idx[s]
        elig = np.array([mask_fn(i, j) for i in range(len(topic_i))])
        m = (topic_i == j) & elig
        ts, ty = sims_all[m, j], y[m]
        entry = {
            "n_eligible": int(m.sum()), "n_positive": int(ty.sum()),
            "auc": auc(ts[ty == 1], ts[ty == 0]),
            "floors": {},
        }
        for floor in PRECISION_FLOORS:
            hit = threshold_at_floor(ts, ty, floor)
            entry["floors"][str(floor)] = (
                None if hit is None else
                {"tau": hit[0], "precision": hit[1], "recall_eligible": hit[2],
                 "kept": hit[3],
                 # recall vs ALL positives of the topic, not just eligible —
                 # the argmax rule loses positives whose top-1 is elsewhere
                 "recall_all": float(hit[3] * hit[1] /
                                     max(1, int(y[topic_i == j].sum())))})
        per_topic[s] = entry
    return per_topic


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--taxonomy", required=True)
    ap.add_argument("--engine", choices=["e5", "openai"], default="e5")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.corpus) if l.strip()]
    tax = json.load(open(args.taxonomy))
    cats = {c["slug"]: c for c in tax["categories"]}
    corpus_slugs = sorted({r["assigned_topic_slug"] for r in rows})
    slugs = [s for s in corpus_slugs if s in cats]
    missing = [s for s in corpus_slugs if s not in cats]
    rows = [r for r in rows if r["assigned_topic_slug"] in cats]
    idx = {s: i for i, s in enumerate(slugs)}

    anchor_texts = [
        f"{cats[s]['label']}. {cats[s]['definition']} {cats[s]['includes']}"
        for s in slugs
    ]
    headlines_raw = [html.unescape(r["headline"]) for r in rows]

    print(f"{len(rows)} rows, {len(slugs)} topics, engine={args.engine}",
          file=sys.stderr)

    if args.engine == "e5":
        A = build_e5_embedder(256)([f"passage: {t}" for t in anchor_texts])
        H = build_e5_embedder(96)([f"passage: {h}" for h in headlines_raw])
        model_name = E5_MODEL
    else:
        A = openai_embed(anchor_texts)
        H = openai_embed(headlines_raw)
        model_name = OPENAI_MODEL

    y = np.array([bool(r["is_evidence"]) for r in rows], dtype=int)
    topic_i = np.array([idx[r["assigned_topic_slug"]] for r in rows])
    sims_all = H @ A.T
    top1 = sims_all.argmax(axis=1)
    assigned_sims = sims_all[np.arange(len(rows)), topic_i]

    global_stats = {
        "auc_assigned_pair": auc(assigned_sims[y == 1], assigned_sims[y == 0]),
        "pos_p50": float(np.median(assigned_sims[y == 1])),
        "neg_p50": float(np.median(assigned_sims[y == 0])),
        "top1_hits_assigned_pct": float((top1 == topic_i).mean()),
        "top1_hits_assigned_pos_pct": float((top1[y == 1] == topic_i[y == 1]).mean()),
    }

    rules = {
        "absolute": sweep_rule(slugs, idx, sims_all, topic_i, y,
                               lambda i, j: True),
        "argmax": sweep_rule(slugs, idx, sims_all, topic_i, y,
                             lambda i, j: top1[i] == j),
    }

    # cross-fire load for the absolute rule (argmax is 0 by construction):
    # positive rows firing a FOREIGN anchor above that anchor's primary tau
    fk = str(PRIMARY_FLOOR)
    tau_abs = {s: (rules["absolute"][s]["floors"][fk] or {}).get("tau")
               for s in slugs}
    fired = 0
    for i in np.where(y == 1)[0]:
        for s in slugs:
            j = idx[s]
            t = tau_abs.get(s)
            if j != topic_i[i] and t is not None and sims_all[i, j] >= t:
                fired += 1
                break
    crossfire = {"n_positive": int(y.sum()), "rows_firing_foreign": fired}

    result = {
        "schema": "tau-sem-calibration-v1",
        "corpus": args.corpus, "engine": args.engine, "model": model_name,
        "n_rows": len(rows), "n_topics": len(slugs), "n_positive": int(y.sum()),
        "primary_floor": PRIMARY_FLOOR,
        "global": global_stats,
        "rules": rules,
        "crossfire_absolute": crossfire,
        "skipped_topics": missing,
        "caveat": "gold corpus is a lexicon-biased sample; precision here is "
                  "an upper bound for wild-corpus candidate generation",
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(result, indent=1))

    fmt = lambda v: "—" if v is None or v != v else f"{v:.3f}"  # noqa: E731
    lines = [
        f"# tau_sem calibration v1 — engine {args.engine} ({model_name})",
        "",
        f"Corpus: `{args.corpus}` ({len(rows)} rows, {int(y.sum())} pos, "
        f"{len(slugs)} topics). Caveat: lexicon-biased sample; precision = "
        "upper bound.",
        "",
        f"Global: assigned-pair AUC {fmt(global_stats['auc_assigned_pair'])}, "
        f"pos p50 {fmt(global_stats['pos_p50'])} vs neg p50 "
        f"{fmt(global_stats['neg_p50'])}; top-1 hits assigned topic on "
        f"{global_stats['top1_hits_assigned_pct']:.1%} of rows "
        f"({global_stats['top1_hits_assigned_pos_pct']:.1%} of positives).",
        "",
        f"Cross-fire (absolute rule): {crossfire['rows_firing_foreign']}/"
        f"{crossfire['n_positive']} positives fire a foreign anchor. "
        "Argmax rule: 0 by construction.",
    ]
    for rule in ("absolute", "argmax"):
        lines += [
            "", f"## rule = {rule}", "",
            "| topic | elig | pos | AUC | tau@0.6 | P | R(elig) | R(all) | kept |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for s in slugs:
            e = rules[rule][s]
            f = e["floors"][fk]
            lines.append(
                f"| {s} | {e['n_eligible']} | {e['n_positive']} | "
                f"{fmt(e['auc'])} | "
                + ("— | — | — | — | — |" if f is None else
                   f"{f['tau']:.4f} | {f['precision']:.2f} | "
                   f"{f['recall_eligible']:.2f} | {f['recall_all']:.2f} | "
                   f"{f['kept']} |"))
    out.with_suffix(".md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"engine": args.engine, "global": global_stats,
                      "crossfire_absolute": crossfire}, indent=1))
    print(f"wrote {out.with_suffix('.json')} + .md", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
