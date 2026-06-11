"""Live walkthrough smoke for the research workflow (#213).

Runs both forcing cases against a deployed API and asserts the route a user
takes: plan → openable anchors → thread detail non-empty → pin events
accepted. Read-only except for smoke rows in research_pin_events
(investigation_id 'inv-walkthrough-smoke').

Usage:
    .venv/bin/python -m scripts.research_walkthrough_smoke \
        [--base https://atlas-api-pedro.fly.dev]
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.request

CASES = [
    ("topic-research", "Iran climate water drought"),
    ("claim-verification",
     "manipulación de clima Irán y ataques a bases estadounidenses satélite"),
]


def _post(base: str, path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as res:
        return json.loads(res.read())


def _get(base: str, path: str) -> dict:
    with urllib.request.urlopen(f"{base}{path}", timeout=30) as res:
        return json.loads(res.read())


def run_case(base: str, name: str, query: str) -> list[str]:
    failures: list[str] = []
    plan = _post(base, "/api/v2/research/plan", {"query": query, "hours": 168})

    anchors = plan.get("anchors") or []
    if not anchors:
        return [f"{name}: no anchors"]
    if not plan.get("plan_id"):
        failures.append(f"{name}: missing plan_id")
    if not all(a.get("evidence_label") for a in anchors):
        failures.append(f"{name}: anchor without evidence_label")

    ledger = plan.get("downranking_ledger") or {}
    if ledger and ledger["candidate_count"] != (
        ledger["shown_count"] + ledger["downranked_count"] + ledger["omitted_count"]
    ):
        failures.append(f"{name}: ledger does not reconcile")

    # open the best thread anchor -> detail must not be an empty surprise
    thread = next((a for a in anchors if a["anchor_type"] == "thread"
                   and (a.get("open") or {}).get("surface") == "thread_detail"), None)
    if thread:
        params = thread["open"]["params"]
        detail = _get(base, f"/api/v2/threads/{params['thread_id']}?hours=168")
        inner = detail.get("thread") or detail  # contract nests under "thread"
        listed = int(thread.get("signal_count") or 0)
        detailed = inner.get("signal_count") or inner.get("total") or 0
        if listed > 0 and not detailed and not inner.get("quality"):
            failures.append(
                f"{name}: list/detail mismatch without explanation "
                f"({thread['open']['params']['thread_id']}: list {listed}, detail 0)"
            )
    else:
        failures.append(f"{name}: no openable thread anchor")

    if name == "claim-verification":
        if not any(a["anchor_type"] == "related_branch" for a in anchors):
            failures.append(f"{name}: missing related branch")
        if not any(a["evidence_label"] == "gap" for a in anchors):
            failures.append(f"{name}: gap not surfaced")

    # pin-event round trip
    events = _post(base, "/api/v2/research/events", {
        "plan_id": plan["plan_id"],
        "investigation_id": "inv-walkthrough-smoke",
        "query_text": query,
        "events": [{"anchor_id": anchors[0]["id"], "event_type": "impression",
                    "rank_shown": 0}],
    })
    if not events.get("accepted"):
        failures.append(f"{name}: pin events not accepted ({events})")

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="https://atlas-api-pedro.fly.dev")
    args = parser.parse_args()

    all_failures: list[str] = []
    for name, query in CASES:
        failures = run_case(args.base, name, query)
        status = "PASS" if not failures else "FAIL"
        print(f"[{status}] {name}: {query[:60]}")
        for failure in failures:
            print(f"   - {failure}")
        all_failures.extend(failures)

    return 1 if all_failures else 0


if __name__ == "__main__":
    sys.exit(main())
