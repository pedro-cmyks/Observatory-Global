#!/usr/bin/env python
"""L4 M0 — event study: do Atlas narrative spikes lead market moves? (#226)

The evidence gate for the whole L4 idea (docs/research/
2026-06-12-atlas-markets-layer-l4.md). Runs INSIDE the repo's markets/
folder (Pedro 2026-06-12), consumes Atlas-derived data only.

Substrate (2026-07-06): archive story units (6,473 daily clusters,
May-03→Jul-04) with OpenAI content centroids → assigned to atlas categories
by argmax anchor cosine (same rule as the semantic lane) → category-day
intensity series. Markets: Yahoo daily closes (free chart API).

Method (honest, small-sample):
  events   = category-day z-score >= Z (vs trailing 21d mean/std, min 10d)
  study    = mean log-return of mapped instruments at t0 / t+1 / t+2
             (event on non-trading day rolls to next trading day)
  inference= permutation test (10k shuffles of event days within the
             sample) — NOT asymptotic CIs; n is tiny (~44 trading days)
  leakage  = Atlas day is the UTC NEWS day; same-day close already contains
             the reaction, so t0 is REACTION not lead. Any lead claim rests
             on t+1/t+2 ONLY.

Gate (issue #226): no exploitable lead with honest timestamps → L4 stops;
the result still feeds #219/#151 and the paper line either way.

Usage:
  mlvenv/bin/python markets/m0_event_study.py \
      [--units /Volumes/Ext/Atlas/Embeddings/archive-story-units.jsonl] \
      [--z 2.0] [--out docs/research/markets-l4/2026-07-06-m0-event-study.md]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np

OPENAI_MODEL = "text-embedding-3-small"

# category slug -> Yahoo instruments (the domain->instrument map from #226)
INSTRUMENT_MAP = {
    "oil-gas-supply-risk": ["CL=F", "NG=F"],
    "armed-conflict-escalation": ["CL=F", "GC=F", "ITA"],
    "sanctions-diplomatic-pressure": ["GC=F", "CL=F"],
    "agriculture-crop-risk": ["ZW=F"],
    "food-price-stress": ["ZW=F"],
    "currency-debt-stress": ["GC=F"],
    "gang-control-urban-security": ["COP=X", "MXN=X"],
    "migration-border-pressure": ["MXN=X"],
    "cyberattack-infrastructure": ["ITA"],
}
INSTRUMENTS = sorted({t for ts in INSTRUMENT_MAP.values() for t in ts})


def yahoo_daily(symbol: str) -> dict[str, float]:
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.request.quote(symbol)}?range=4mo&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.loads(r.read())
            res = d["chart"]["result"][0]
            closes = {}
            for ts, c in zip(res["timestamp"],
                             res["indicators"]["quote"][0]["close"]):
                if c is not None:
                    closes[date.fromtimestamp(ts).isoformat()] = float(c)
            return closes
        except Exception:  # noqa: BLE001
            if attempt == 3:
                raise
            time.sleep(3 * (attempt + 1))
    return {}


def openai_embed(texts: list[str]) -> np.ndarray:
    import openai
    client = openai.OpenAI(timeout=120.0)
    vecs = []
    for i in range(0, len(texts), 512):
        resp = client.embeddings.create(model=OPENAI_MODEL,
                                        input=texts[i:i+512])
        vecs.extend(d.embedding for d in resp.data)
    a = np.asarray(vecs, dtype=np.float32)
    return a / np.linalg.norm(a, axis=1, keepdims=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--units",
                    default="/Volumes/Ext/Atlas/Embeddings/archive-story-units.jsonl")
    ap.add_argument("--taxonomy",
                    default="docs/research/taxonomy-revision/candidate-v2.json")
    ap.add_argument("--z", type=float, default=2.0)
    ap.add_argument("--assign-tau", type=float, default=0.30,
                    help="min anchor cosine for a unit to count (wild-"
                         "calibrated range from the semantic lane)")
    ap.add_argument("--out",
                    default="docs/research/markets-l4/2026-07-06-m0-event-study.md")
    args = ap.parse_args()

    # ── 1. category-day intensity from archive units ──────────────────────
    tax = json.load(open(args.taxonomy))
    cats = [c for c in tax["categories"] if c["slug"] in INSTRUMENT_MAP]
    slugs = [c["slug"] for c in cats]
    A = openai_embed([f"{c['label']}. {c['definition']} {c['includes']}"
                      for c in cats])

    units = [json.loads(l) for l in open(args.units) if '"centroid"' in l]
    V = np.asarray([u["centroid"] for u in units], dtype=np.float32)
    V /= np.linalg.norm(V, axis=1, keepdims=True)
    sims = V @ A.T
    top = sims.argmax(axis=1)
    top_sim = sims[np.arange(len(units)), top]

    series: dict[str, dict[str, float]] = defaultdict(dict)  # slug -> day -> intensity
    for u, j, s in zip(units, top, top_sim):
        if s < args.assign_tau:
            continue
        slug = slugs[int(j)]
        day = u["day"]
        series[slug][day] = series[slug].get(day, 0.0) + float(u["n"])
    print(f"{len(units)} units → assigned "
          f"{sum(len(v) for v in series.values())} category-days "
          f"across {len(series)} mapped categories", file=sys.stderr)

    # ── 2. markets ─────────────────────────────────────────────────────────
    closes = {}
    for sym in INSTRUMENTS:
        closes[sym] = yahoo_daily(sym)
        print(f"  {sym}: {len(closes[sym])} closes", file=sys.stderr)
        time.sleep(1)
    trading_days = sorted(set().union(*[set(c) for c in closes.values()]))

    def log_ret(sym: str, day: str) -> float | None:
        days = sorted(closes[sym])
        if day not in closes[sym]:
            return None
        i = days.index(day)
        if i == 0:
            return None
        return float(np.log(closes[sym][day] / closes[sym][days[i - 1]]))

    def next_trading(day: str) -> str | None:
        for d in trading_days:
            if d >= day:
                return d
        return None

    def shift_trading(day: str, k: int) -> str | None:
        if day not in trading_days:
            return None
        i = trading_days.index(day)
        return trading_days[i + k] if 0 <= i + k < len(trading_days) else None

    # ── 3. events + study ──────────────────────────────────────────────────
    rng = np.random.default_rng(7)
    rows = []
    for slug, sd in sorted(series.items()):
        days = sorted(sd)
        vals = np.array([sd[d] for d in days])
        events = []
        for i, d in enumerate(days):
            hist = vals[max(0, i - 21):i]
            if len(hist) < 10:
                continue
            mu, sig = hist.mean(), hist.std()
            if sig > 0 and (vals[i] - mu) / sig >= args.z:
                events.append(d)
        if not events:
            rows.append((slug, 0, None))
            continue
        for sym in INSTRUMENT_MAP[slug]:
            for lag in (0, 1, 2):
                ev_rets = []
                for e in events:
                    t0 = next_trading(e)
                    tl = shift_trading(t0, lag) if t0 else None
                    r = log_ret(sym, tl) if tl else None
                    if r is not None:
                        ev_rets.append(abs(r))  # |move|: direction-agnostic
                        # (a narrative spike predicts VOLATILITY first;
                        # signed tests need a stance model L4 doesn't have)
                if len(ev_rets) < 3:
                    continue
                all_rets = [abs(log_ret(sym, d) or 0) for d in trading_days[1:]]
                all_rets = [r for r in all_rets if r > 0]
                obs = float(np.mean(ev_rets))
                # permutation: mean |ret| of len(ev_rets) random days, 10k×
                perm = np.array([
                    np.mean(rng.choice(all_rets, size=len(ev_rets),
                                       replace=False))
                    for _ in range(10_000)])
                p = float((perm >= obs).mean())
                rows.append((f"{slug} → {sym} @t+{lag}", len(ev_rets),
                             {"mean_abs_move": round(obs, 5),
                              "baseline": round(float(np.mean(all_rets)), 5),
                              "ratio": round(obs / np.mean(all_rets), 2),
                              "perm_p": round(p, 4)}))

    # ── 4. artifact ────────────────────────────────────────────────────────
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# L4 M0 — event study (#226): Atlas narrative spikes vs market |moves|",
        "",
        f"Substrate: archive story units {min(min(s) for s in series.values() if s)}"
        f" → {max(max(s) for s in series.values() if s)} · "
        f"events = category-day z>={args.z} vs trailing 21d · "
        "returns = Yahoo daily closes · inference = 10k permutations.",
        "",
        "**HONESTY HEADER — pilot power only**: ~44 trading days, single "
        "regime (May-Jul 2026), |return| (volatility) not signed direction, "
        "UTC-day alignment. t0 = REACTION (same-day close contains the news);"
        " a LEAD claim is only t+1/t+2. Nothing here is tradeable evidence; "
        "it is the go/no-go for collecting MORE evidence.",
        "",
        "| category → instrument @lag | n events | mean \\|ret\\| | baseline | ratio | perm p |",
        "|---|---|---|---|---|---|",
    ]
    findings = 0
    for name, n, stats in rows:
        if stats is None:
            lines.append(f"| {name} | 0 (no spikes) | — | — | — | — |")
            continue
        mark = " **←**" if stats["perm_p"] < 0.10 and "t+0" not in name else ""
        if stats["perm_p"] < 0.10 and "@t+0" not in name:
            findings += 1
        lines.append(
            f"| {name} | {n} | {stats['mean_abs_move']} | {stats['baseline']} "
            f"| {stats['ratio']} | {stats['perm_p']}{mark} |")
    lines += [
        "",
        f"Candidate leads (p<0.10 at t+1/t+2): **{findings}**",
        "",
        "## Reading",
        "- ratio > 1 = market moves MORE than baseline after an Atlas spike.",
        "- t+0 rows measure REACTION (sanity check that the categories are "
        "market-relevant at all); only t+1/t+2 rows can support the L4 gate.",
        "- With ~44 trading days, even p<0.10 is fragile — the honest verdict "
        "space is {collect-more, stop}, never {trade}.",
    ]
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")
    print(f"candidate leads (t+1/t+2, p<0.10): {findings}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
