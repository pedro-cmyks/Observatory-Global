#!/usr/bin/env python3
"""Iran heterogeneous forcing case — L3 composition gate (matrix gate 6).

Composes a real, heterogeneous Iran investigation out of production pins
(story + story + evidence/signal + country + subject/actor + event + anomaly),
resolves them through ``/investigation/resolve-nodes``, assembles the typed
``/investigation/graph``, and builds the ``/investigation/publication-package``.
It then GRADES the end-to-end composition against the deployed contracts.

This answers the reliability-matrix gap: "no current production run has
demonstrated story + actor + signal + country + event/anomaly pins connected,
time-remeasured, inspected and exported as one portable package."

Read-only. Repeatable. No LLM, no DB credentials — it exercises the deployed
HTTP contracts only. It is a diagnostic: it reports whatever the system does
(ready / partial / missing, degraded relations, metadata-only pins) instead of
forcing a green result. Exit code is 0 when the full compose chain returns
contract-honest artifacts, 1 when a contract breaks.

Usage:
    python scripts/iran_forcing_case_smoke.py
    ATLAS_API_BASE=http://localhost:8000 python scripts/iran_forcing_case_smoke.py
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

BASE = os.environ.get("ATLAS_API_BASE", "https://atlas-api-pedro.fly.dev").rstrip("/")
PREFIX = "/api/v2/investigation"
WINDOW_HOURS = 168


def _post(path: str, body: dict, timeout: int = 40) -> tuple[int, dict]:
    req = urllib.request.Request(
        BASE + PREFIX + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:400]
        return exc.code, {"_http_error": detail}


def _window() -> dict:
    end = datetime.now(timezone.utc).replace(microsecond=0)
    start = end - timedelta(hours=WINDOW_HOURS)
    return {
        "range_start": start.isoformat(),
        "range_end": end.isoformat(),
        "mode": "live",
    }


def _pin(node_type: str, subtype: str, ref_id: str, label: str,
         snapshot: dict | None = None, analyst_note: str | None = None) -> dict:
    pin: dict = {
        "node_type": node_type,
        "subtype": subtype,
        "ref_id": ref_id,
        "label": label,
        "observation_window": _window(),
        "snapshot": snapshot or {},
    }
    if analyst_note:
        pin["analyst_note"] = analyst_note
    return pin


# Heterogeneous Iran pins built from live production ids (verified 2026-07-13).
PINS = [
    _pin("story", "thread", "dynamic-topic-1594", "Israel Plot to Kill Iran Negotiators",
         analyst_note="Israeli intelligence claims of an Iranian plot; frozen."),
    _pin("story", "thread", "dynamic-topic-867", "Iran Military Posturing",
         analyst_note="Regional military-posture coverage; frozen."),
    _pin("evidence", "signal", "12614774",
         "Terrifying Iran 'revenge' warning as Donald Trump assassination plot alleged",
         snapshot={"source": "frozen-receipt", "frozen": True}),
    _pin("country", "iso", "IR", "Iran", snapshot={"name": "Iran"}),
    _pin("subject", "person", "Donald Trump", "Donald Trump",
         snapshot={"name": "Donald Trump", "type": "person"}),
    _pin("event", "conflict", "ir-posture-2026-07",
         "Iran military-posture event (metadata-only pin)"),
    _pin("anomaly", "spike", "ir-attention-spike-2026-07",
         "Iran attention spike (metadata-only pin)"),
]


def main() -> int:
    print(f"# Iran heterogeneous forcing case — {BASE}")
    print(f"# pins requested: {len(PINS)} "
          f"({', '.join(sorted({p['node_type'] for p in PINS}))})\n")

    defects: list[str] = []

    # --- 1. resolve ---------------------------------------------------------
    status, resolved = _post("/resolve-nodes", {"nodes": PINS})
    if status != 200 or "nodes" not in resolved:
        print(f"FATAL resolve-nodes HTTP {status}: {resolved}")
        return 1
    nodes = resolved["nodes"]
    comp = resolved.get("completion", {})
    by_status: dict[str, int] = {}
    for n in nodes:
        by_status[n["resolution_status"]] = by_status.get(n["resolution_status"], 0) + 1
    print("## resolve")
    print(f"   requested={comp.get('requested')} processed={comp.get('processed')} "
          f"truncated={comp.get('truncated')}")
    print(f"   status mix: {by_status}")
    if comp.get("processed") != len(PINS):
        defects.append("resolve dropped pins (processed != requested)")
    if comp.get("truncated"):
        defects.append("resolve silently truncated")

    # --- 2. graph -----------------------------------------------------------
    status, graph = _post("/graph", {"nodes": nodes}, timeout=40)
    if status != 200 or "edges" not in graph:
        print(f"FATAL graph HTTP {status}: {graph}")
        return 1
    edges = graph["edges"]
    gcomp = graph.get("completion", {})
    tiers: dict[str, int] = {}
    self_edges = 0
    for e in edges:
        tiers[e.get("truth_tier", "?")] = tiers.get(e.get("truth_tier", "?"), 0) + 1
        if e.get("source_node_id") == e.get("target_node_id"):
            self_edges += 1
    print("\n## graph")
    print(f"   requested_pairs={gcomp.get('requested_pairs')} "
          f"processed_pairs={gcomp.get('processed_pairs')}")
    print(f"   edges={len(edges)} by tier: {tiers}")
    print(f"   relation_types: {sorted({e.get('relation_type') for e in edges})}")
    unresolved = graph.get("unresolved_ledger", [])
    if unresolved:
        print(f"   unresolved_ledger: {unresolved}")
    if gcomp.get("requested_pairs") != gcomp.get("processed_pairs"):
        defects.append("graph silently capped pairs")
    if self_edges:
        defects.append(f"tautological self-edge present ({self_edges})")

    # --- 3. publication package --------------------------------------------
    status, pkg = _post("/publication-package", {
        "title": "Iran — plot allegations, posture and US talks",
        "authorship": "analyst",
        "graph": graph,
    }, timeout=40)
    if status != 200 or pkg.get("contract") != "atlas-publication-package-v1":
        print(f"FATAL publication-package HTTP {status}: {pkg}")
        return 1
    readiness = pkg.get("readiness", {})
    receipts = pkg.get("receipts", [])
    gaps = pkg.get("gaps", [])
    print("\n## publication package")
    print(f"   contract: {pkg.get('contract')}")
    for dim in ("who", "what", "when", "where", "why", "how"):
        item = readiness.get(dim, {})
        st = item.get("status", "missing")
        rc = item.get("reason_codes", [])
        # The fraction IS the row now (T3.2): a bare 'partial' hides whether
        # the dimension covered 1 story node or 11.
        m = item.get("measured") or {}
        frac = f"  {m['ready']}/{m['total']} {m.get('basis', '')}" if m.get("total") else ""
        print(f"   {dim:5} -> {st}{frac}"
              + (f"  ({', '.join(rc)})" if rc else ""))
    print(f"   receipts: {len(receipts)}   spine_nodes: {len(pkg.get('narrative_spine', []))}")
    print(f"   gaps: {gaps}")
    print(f"   reproducibility: {json.dumps(pkg.get('reproducibility', {}))[:200]}")

    ready_dims = [d for d in ("who", "what", "when", "where", "how")
                  if readiness.get(d, {}).get("status") == "ready"]
    print(f"\n## grade")
    print(f"   promotion dims ready (who/what/when/where/how): "
          f"{len(ready_dims)}/5 -> {ready_dims}")
    print(f"   why (causal): {readiness.get('why', {}).get('status')} "
          f"(structurally partial by design)")

    if defects:
        print("\n## DEFECTS")
        for d in defects:
            print(f"   - {d}")
    else:
        print("\n## compose chain contract-honest: resolve -> graph -> package OK")

    print("\n## interpretation")
    print("   Heterogeneous compose runs end-to-end and returns honest contracts.")
    print("   Ready<5 or thin receipts are the real editorial gap, not a crash.")
    return 1 if defects else 0


if __name__ == "__main__":
    sys.exit(main())
