"""AI cost report (2026-07-07) — roll up ai_cost_events into the numbers that
let us price Atlas on MEASURED cost, not guesses.

    python -m backend.scripts.ai_cost_report --hours 168
    python -m backend.scripts.ai_cost_report --days 30

Prints:
  * cost + tokens per SURFACE (calls, in/out tokens, tokens-per-call p50/p95, USD)
  * PER-USER vs AMORTIZED split — the per-interaction hypothesis (~$0.005-0.01 per
    full investigation) is confirmed/refuted against the per-user surfaces; the
    background lanes (typing, gate, embeddings) are reported separately.
  * cost per interaction (joined to telemetry_events when present)
  * projected cost per active user per month

M1 NER + clustering are $0 (local compute) and are not in the ledger by design.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

import asyncpg

# Surfaces the user directly triggers (scale with usage / per active user) vs
# background lanes (a fixed nightly/steady-state cost, amortized over all users).
PER_USER = {"brief", "theme-insight", "dossier-synthesis", "translate", "dossier-embed"}
AMORTIZED = {"typing", "gate", "archive-embed", "cluster"}


def _pct(sorted_vals: list[int], q: float) -> int:
    if not sorted_vals:
        return 0
    idx = min(len(sorted_vals) - 1, int(q * (len(sorted_vals) - 1) + 0.5))
    return sorted_vals[idx]


def _fmt_usd(x: float) -> str:
    if x == 0:
        return "$0"
    if x < 0.01:
        return f"${x:.6f}"
    return f"${x:,.4f}"


async def _run(hours: int) -> int:
    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL required", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(db)
    try:
        rows = await conn.fetch(
            "SELECT surface, provider, model, input_tokens, output_tokens, usd "
            "FROM ai_cost_events WHERE created_at >= NOW() - ($1 || ' hours')::interval",
            str(hours),
        )
    except asyncpg.UndefinedTableError:
        print("ai_cost_events table not found — apply migration 073 first.", file=sys.stderr)
        await conn.close()
        return 2

    window_label = f"{hours}h" if hours < 48 else f"{hours / 24:.0f}d"
    print(f"\n=== AI COST REPORT · last {window_label} ({len(rows)} logged calls) ===\n")
    if not rows:
        print("No AI cost events in window. Trigger a brief insight / dossier synthesis,")
        print("or wait for the typing cron, then re-run.")
        await conn.close()
        return 0

    # ---- per-surface rollup ----
    by_surface: dict[str, dict] = {}
    for r in rows:
        s = by_surface.setdefault(r["surface"], {
            "calls": 0, "in": 0, "out": 0, "usd": 0.0,
            "tok_per_call": [], "provider": r["provider"], "model": r["model"],
        })
        s["calls"] += 1
        s["in"] += r["input_tokens"]
        s["out"] += r["output_tokens"]
        s["usd"] += float(r["usd"])
        s["tok_per_call"].append(r["input_tokens"] + r["output_tokens"])

    hdr = f"{'surface':<20}{'calls':>7}{'in_tok':>11}{'out_tok':>10}{'tok/call p50/p95':>20}{'usd':>14}"
    print(hdr)
    print("-" * len(hdr))
    total_usd = 0.0
    for surface in sorted(by_surface, key=lambda k: -by_surface[k]["usd"]):
        s = by_surface[surface]
        total_usd += s["usd"]
        tpc = sorted(s["tok_per_call"])
        p50, p95 = _pct(tpc, 0.50), _pct(tpc, 0.95)
        print(f"{surface:<20}{s['calls']:>7}{s['in']:>11,}{s['out']:>10,}"
              f"{f'{p50}/{p95}':>20}{_fmt_usd(s['usd']):>14}")
    print("-" * len(hdr))
    print(f"{'TOTAL':<20}{sum(s['calls'] for s in by_surface.values()):>7}"
          f"{'':>41}{_fmt_usd(total_usd):>14}\n")

    # ---- per-user vs amortized ----
    per_user_usd = sum(s["usd"] for k, s in by_surface.items() if k in PER_USER)
    amortized_usd = sum(s["usd"] for k, s in by_surface.items() if k in AMORTIZED)
    other_usd = total_usd - per_user_usd - amortized_usd
    print("SPLIT")
    print(f"  per-user surfaces   {_fmt_usd(per_user_usd)}  ({', '.join(sorted(PER_USER & by_surface.keys())) or '—'})")
    print(f"  amortized/background {_fmt_usd(amortized_usd)}  ({', '.join(sorted(AMORTIZED & by_surface.keys())) or '—'})")
    if other_usd > 0:
        print(f"  unclassified        {_fmt_usd(other_usd)}")
    print()

    # ---- interactions (telemetry join, best-effort) ----
    active_users = investigations = None
    try:
        tel = await conn.fetchrow(
            "SELECT COUNT(DISTINCT session_id) AS users, "
            "COUNT(*) FILTER (WHERE event ILIKE '%investigation%' "
            "                    OR event ILIKE '%dossier%' "
            "                    OR event = 'first_value_moment') AS investigations "
            "FROM telemetry_events "
            "WHERE created_at >= NOW() - ($1 || ' hours')::interval",
            str(hours),
        )
        active_users = tel["users"] or 0
        investigations = tel["investigations"] or 0
    except asyncpg.UndefinedTableError:
        pass

    print("PER-INTERACTION (measure-first: hypothesis ~$0.005-0.01 per full investigation)")
    if investigations:
        cost_per_inv = per_user_usd / investigations
        print(f"  investigations (telemetry): {investigations}")
        print(f"  per-user cost / investigation: {_fmt_usd(cost_per_inv)}  "
              f"→ hypothesis {'CONFIRMED' if cost_per_inv <= 0.01 else 'REFUTED'}")
    else:
        print("  no investigation telemetry in window — reporting total per-user cost only.")

    # ---- projected $/active user/month ----
    months = (hours / 24.0) / 30.4375
    if active_users and months > 0:
        monthly_per_user = (per_user_usd / active_users) / months
        print(f"\nPROJECTED $/active-user/month")
        print(f"  active users (telemetry): {active_users}")
        print(f"  per-user AI cost / active user / month: {_fmt_usd(monthly_per_user)}")
        if months > 0:
            print(f"  amortized/background / month (fixed, not per-user): {_fmt_usd(amortized_usd / months)}")
    else:
        print("\nPROJECTED $/active-user/month: no active-user telemetry in window.")

    print()
    await conn.close()
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="AI cost rollup over a window.")
    ap.add_argument("--hours", type=int, default=None)
    ap.add_argument("--days", type=int, default=None)
    args = ap.parse_args()
    hours = args.hours if args.hours is not None else (args.days * 24 if args.days else 168)
    sys.exit(asyncio.run(_run(hours)))


if __name__ == "__main__":
    main()
