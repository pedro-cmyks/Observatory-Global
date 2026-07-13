#!/usr/bin/env python3
"""Build one sealed Atlas daily PublicationPackage on the M1.

Heavy traversal and receipt reads run here under the existing heavy-job mutex,
never in the L1 request. Dry-run is the default; `--execute` upserts one compact
JSON artifact into `atlas_daily_editions`.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timedelta
import json
import os
from typing import Any

import asyncpg
from pydantic import TypeAdapter

from app import db
from app.services.daily_publication import fetch_daily_publication


_JSON_ADAPTER = TypeAdapter(Any)


def _edition_status(result: dict[str, Any]) -> str:
    package = result.get("package")
    readiness = package.readiness if hasattr(package, "readiness") else {}
    required = ("who", "what", "when", "where", "how")
    if not all(readiness.get(key) and readiness[key].status == "ready" for key in required):
        return "degraded"
    completion = result.get("completion") or {}
    if completion.get("receipt_fetch_error") or not completion.get("cursor_exhausted"):
        return "degraded"
    if float(completion.get("data_lag_hours") or 0) > 6:
        return "degraded"
    return "ready"


async def _run(*, execute: bool) -> dict[str, Any]:
    db.pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"],
        min_size=1,
        max_size=2,
        command_timeout=120,
    )
    try:
        result = await fetch_daily_publication(hours=24, serving_budget=False)
        encoded = _JSON_ADAPTER.dump_python(result, mode="json")
        completion = encoded["completion"]
        edition_end = datetime.fromisoformat(completion["edition_end"])
        edition_start = edition_end - timedelta(hours=24)
        status = _edition_status(result)
        if execute:
            async with db.pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO atlas_daily_editions
                        (edition_date, edition_start, edition_end, generated_at,
                         contract, status, package, graph, selection, completion,
                         updated_at)
                    VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb,$8::jsonb,$9::jsonb,$10::jsonb,now())
                    ON CONFLICT (edition_date) DO UPDATE SET
                        edition_start = EXCLUDED.edition_start,
                        edition_end = EXCLUDED.edition_end,
                        generated_at = EXCLUDED.generated_at,
                        contract = EXCLUDED.contract,
                        status = EXCLUDED.status,
                        package = EXCLUDED.package,
                        graph = EXCLUDED.graph,
                        selection = EXCLUDED.selection,
                        completion = EXCLUDED.completion,
                        updated_at = now()
                    """,
                    edition_end.date(), edition_start, edition_end,
                    datetime.fromisoformat(completion["generated_at"]),
                    encoded["contract"], status,
                    json.dumps(encoded["package"]),
                    json.dumps(encoded["graph"]),
                    json.dumps(encoded["selection"]),
                    json.dumps(completion),
                )
        return {
            "execute": execute,
            "status": status,
            "edition_end": completion["edition_end"],
            "candidate_count": completion.get("candidate_count"),
            "selected_count": len(encoded.get("selection", {}).get("selected_ids", [])),
            "receipt_count": len(encoded.get("package", {}).get("receipts", [])),
            "data_lag_hours": completion.get("data_lag_hours"),
            "receipt_fetch_error": completion.get("receipt_fetch_error"),
        }
    finally:
        await db.pool.close()
        db.pool = None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="upsert compact edition row")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(_run(execute=args.execute)), indent=2))


if __name__ == "__main__":
    main()
