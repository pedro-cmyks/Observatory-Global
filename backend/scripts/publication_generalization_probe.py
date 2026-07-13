#!/usr/bin/env python3
"""Publication generalization probe — does the L3/L1 package work for ALL topics?

The Iran/Senegal/NATO forcing cases are fixtures, not the goal. The real bar is
that ANY current thread composes into an honest publication package. This probe
pulls the live top threads (diverse topics), runs each single story through
resolve-nodes -> graph -> publication-package against the deployed contracts,
and reports the 5W+H readiness distribution.

It is read-only and repeatable. It measures generalization; it does not force a
result. A story that abstains on who/where is a real coverage/label gap, not a
crash — the probe surfaces the count so the gap is visible.

Usage:
    python scripts/publication_generalization_probe.py
    ATLAS_API_BASE=http://localhost:8000 python scripts/publication_generalization_probe.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = os.environ.get("ATLAS_API_BASE", "https://atlas-api-pedro.fly.dev").rstrip("/")
WINDOW_HOURS = 168
LIMIT = int(os.environ.get("PROBE_LIMIT", "15"))
PROMOTION_DIMS = ("who", "what", "when", "where", "how")


def _get(path: str, timeout: int = 30) -> dict | list | None:
    try:
        with urllib.request.urlopen(BASE + path, timeout=timeout) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None


def _post(path: str, body: dict, timeout: int = 40) -> tuple[int, dict]:
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, {"_err": exc.read().decode(errors="replace")[:200]}
    except (urllib.error.URLError, TimeoutError) as exc:
        return 0, {"_err": str(exc)}


def _window() -> dict:
    end = datetime.now(timezone.utc).replace(microsecond=0)
    return {
        "range_start": (end - timedelta(hours=WINDOW_HOURS)).isoformat(),
        "range_end": end.isoformat(),
        "mode": "live",
    }


def _package_for_thread(thread_id: str, label: str) -> dict | None:
    pin = {
        "node_type": "story", "subtype": "thread", "ref_id": thread_id,
        "label": label or thread_id, "observation_window": _window(), "snapshot": {},
    }
    status, resolved = _post("/api/v2/investigation/resolve-nodes", {"nodes": [pin]})
    if status != 200 or not resolved.get("nodes"):
        return None
    status, graph = _post("/api/v2/investigation/graph", {"nodes": resolved["nodes"]})
    if status != 200 or "edges" not in graph:
        return None
    status, pkg = _post("/api/v2/investigation/publication-package", {
        "title": label or thread_id, "authorship": "analyst", "graph": graph,
    })
    if status != 200 or pkg.get("contract") != "atlas-publication-package-v1":
        return None
    return pkg


def main() -> int:
    print(f"# Publication generalization probe — {BASE}\n")
    threads = _get(f"/api/v2/threads?hours={WINDOW_HOURS}&limit={LIMIT}")
    rows = (threads or {}).get("threads") if isinstance(threads, dict) else threads
    if not rows:
        print("no threads returned")
        return 1

    print(f"{'topic':<38} {'who':<5}{'what':<5}{'when':<5}{'where':<6}{'how':<5} 5/5 subject_geo")
    print("-" * 92)
    ready_counts = {dim: 0 for dim in PROMOTION_DIMS}
    full = 0
    measured = 0
    for t in rows[:LIMIT]:
        tid = t.get("thread_id") or t.get("id")
        label = (t.get("label") or "")[:36]
        if not tid:
            continue
        pkg = _package_for_thread(str(tid), label)
        if not pkg:
            print(f"{label:<38} (package unavailable)")
            continue
        measured += 1
        r = pkg.get("readiness", {})
        marks = {}
        for dim in PROMOTION_DIMS:
            ok = r.get(dim, {}).get("status") == "ready"
            marks[dim] = ok
            if ok:
                ready_counts[dim] += 1
        n_ready = sum(marks.values())
        if n_ready == 5:
            full += 1
        geo = ", ".join(r.get("where", {}).get("values", [])[:6]) or "—"
        cell = lambda ok: " Y   " if ok else " .   "
        print(f"{label:<38}{cell(marks['who'])}{cell(marks['what'])}{cell(marks['when'])}"
              f"{cell(marks['where'])[:6]}{cell(marks['how'])} {n_ready}/5 {geo}")

    print("-" * 92)
    print(f"\nmeasured {measured} topics")
    if measured:
        for dim in PROMOTION_DIMS:
            pct = 100 * ready_counts[dim] / measured
            print(f"  {dim:<6} ready: {ready_counts[dim]}/{measured} ({pct:.0f}%)")
        print(f"  full 5/5: {full}/{measured} ({100 * full / measured:.0f}%)")
    print("\nInterpretation: high who/where % = the receipt-derived subject-geography "
          "and actor lanes\ngeneralize across topics. Low where on a topic = its "
          "receipts do not independently\nname a country (oblique/non-English headlines) — a real recall gap, not a crash.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
