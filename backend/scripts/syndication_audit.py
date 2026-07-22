"""Syndication audit (spec 2026-06-29 §4 / §4.4) — MEASURE BEFORE RANKING.

Quantifies how much each LIVE thread is syndicated copy vs genuine diverse
coverage, so we can (a) prove `headline_diversity` separates "Las Vegas Travel
Guide" (one travel article × 25 reprints) from real stories, and (b) eyeball the
false-demote risk (a legitimate wire story IS syndicated — the metric must be a
ranking INPUT, never a gate).

API-driven + read-only: hits the prod serving path (`/api/v2/threads` then
`/api/v2/theme/{id}`) so it measures EXACTLY what users see — atlas + dynamic
threads alike — without re-deriving two membership models. No torch/DB needed.

  headline_diversity = distinct_normalized_headlines / sample_signals   (0..1]

Estimated over the served evidence SAMPLE (enough to separate syndication: a
1-headline cluster reads ~0.04, a diverse story ~0.8). The eventual ranking term
(§4.3) computes this in-SQL over the full serving count — this audit only
measures whether the lever is real and safe.

Run:  python -m backend.scripts.syndication_audit --hours 168 --limit 40
Outputs JSON + Markdown under docs/research/syndication/.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

API = "https://atlas-api-pedro.fly.dev"
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_WS = re.compile(r"\s+")


def _get(path: str) -> dict | list | None:
    try:
        with urllib.request.urlopen(API + path, timeout=30) as r:
            return json.loads(r.read())
    except Exception as e:  # noqa: BLE001 — audit degrades per-thread, never crashes
        print(f"  ! {path}: {e}", file=sys.stderr)
        return None


def _norm(h: str) -> str:
    """Unescape + lowercase + strip punctuation + collapse whitespace.
    (Exact-normalized; near-dup MinHash is a build-time refinement, noted in
    §4.1 — not needed to flag the 1-headline syndication case.)

    The unescape is load-bearing: 46.4% of stored headlines are HTML-entity-
    encoded (measured 2026-07-22), and _PUNCT would otherwise turn "&#xE1;"
    into "xe1" — counting an encoded and a plain copy of one wire story as
    two distinct headlines, i.e. under-reporting syndication. The accent fold
    is the same concern one step further ("Perú" vs "Peru").

    Mirrors app.core.search_normalization.normalize_search_text; kept inline
    because this audit is a standalone API client with no app imports."""
    decomposed = unicodedata.normalize("NFKD", html.unescape(h or ""))
    accentless = "".join(c for c in decomposed if not unicodedata.combining(c))
    return _WS.sub(" ", _PUNCT.sub(" ", accentless.lower())).strip()


def _evidence(detail: dict) -> list[dict]:
    for k in ("evidence", "signals", "evidence_samples", "samples"):
        v = detail.get(k)
        if isinstance(v, list) and v:
            return v
    return []


def _domain(e: dict) -> str:
    return (e.get("source") or e.get("source_name") or e.get("domain")
            or e.get("source_url") or "").lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=168)
    ap.add_argument("--limit", type=int, default=40)
    ap.add_argument("--flag-below", type=float, default=0.35,
                    help="headline_diversity below this = flagged as syndication")
    args = ap.parse_args()

    listing = _get(f"/api/v2/threads?hours={args.hours}&limit={args.limit}")
    threads = listing.get("threads", listing) if isinstance(listing, dict) else listing
    if not threads:
        print("no threads returned", file=sys.stderr)
        sys.exit(2)

    rows = []
    for rank, t in enumerate(threads):
        tid = t.get("thread_id") or t.get("id")
        label = t.get("label") or ""
        serving_count = t.get("signal_count") or t.get("agg_n_signals") or 0
        if not tid:
            continue
        detail = _get(f"/api/v2/theme/{tid}?hours={args.hours}")
        ev = _evidence(detail) if detail else []
        sample_n = len(ev)
        if sample_n == 0:
            rows.append({"rank": rank, "thread_id": tid, "label": label,
                         "serving_count": serving_count, "sample_n": 0,
                         "headline_diversity": None, "distinct_domains": None,
                         "flagged": None})
            continue
        norm_headlines = {_norm(e.get("headline") or e.get("title") or "") for e in ev}
        norm_headlines.discard("")
        domains = {_domain(e) for e in ev}
        domains.discard("")
        div = round(len(norm_headlines) / sample_n, 3)
        rows.append({
            "rank": rank, "thread_id": tid, "label": label,
            "serving_count": serving_count, "sample_n": sample_n,
            "distinct_headlines": len(norm_headlines),
            "headline_diversity": div,
            "distinct_domains": len(domains),
            "flagged": div < args.flag_below,
            "top_headline": (ev[0].get("headline") or ev[0].get("title") or "")[:70],
        })

    scored = [r for r in rows if r["headline_diversity"] is not None]
    flagged = [r for r in scored if r["flagged"]]
    # The Vegas pathology = a LOW-diversity thread ranking HIGH. Surface it.
    flagged_high_rank = sorted(flagged, key=lambda r: r["rank"])[:10]

    out_dir = Path(__file__).resolve().parents[2] / "docs" / "research" / "syndication"
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "params": vars(args), "n_threads": len(rows), "n_scored": len(scored),
        "n_flagged": len(flagged),
        "flagged_pct": round(100 * len(flagged) / max(len(scored), 1), 1),
        "rows": rows,
    }
    (out_dir / "syndication-latest.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    lines = [
        "# Syndication audit (spec §4)", "",
        f"{args.hours}h · {len(scored)}/{len(rows)} threads scored · "
        f"{len(flagged)} flagged (diversity < {args.flag_below}) = {payload['flagged_pct']}%.",
        "Estimated over served evidence sample. headline_diversity = "
        "distinct_normalized_headlines / sample_signals.", "",
        "## Flagged syndication ranking HIGH (the Las Vegas pathology)",
        "| rank | diversity | serving | distinct_hl/sample | domains | label |",
        "|---|---|---|---|---|---|",
    ]
    for r in flagged_high_rank:
        lines.append(
            f"| {r['rank']} | {r['headline_diversity']} | {r['serving_count']} | "
            f"{r['distinct_headlines']}/{r['sample_n']} | {r['distinct_domains']} | {r['label']} |"
        )
    lines += [
        "", "## All threads (diversity ascending — worst first)",
        "| rank | diversity | serving | domains | label |",
        "|---|---|---|---|---|",
    ]
    for r in sorted(scored, key=lambda r: r["headline_diversity"]):
        flag = " ⚠" if r["flagged"] else ""
        lines.append(
            f"| {r['rank']} | {r['headline_diversity']}{flag} | {r['serving_count']} | "
            f"{r['distinct_domains']} | {r['label']} |"
        )
    lines += [
        "", "## False-demote check (READ before ranking)",
        "Eyeball the flagged list: a legitimately important WIRE story (one AP "
        "dispatch, genuinely syndicated) would also flag low. If any flagged thread "
        "is real news, the metric must DAMP (input), never EXCLUDE (gate) — §4.3.",
    ]
    (out_dir / "syndication-latest.md").write_text("\n".join(lines))
    print(json.dumps(payload, indent=2, ensure_ascii=False)[:1500])
    print(f"\nflagged {len(flagged)}/{len(scored)} · wrote {out_dir}/syndication-latest.{{json,md}}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
