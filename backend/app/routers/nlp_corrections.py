"""
Analyst NLP correction loop (issue #166).

Two surfaces:
  POST /api/v2/nlp/corrections          — capture an analyst override.
  GET  /api/v2/nlp/calibration?days=N   — per-language correction rates.

Authentication is intentionally minimal in v1: an `X-Analyst-Id` header.
Production should layer on a session JWT before exposing the POST surface
to anyone outside the maintainer.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel, Field

from app import db

logger = logging.getLogger(__name__)
router = APIRouter()


class CorrectionPayload(BaseModel):
    signal_id: int = Field(..., gt=0)
    corrected_sentiment: float | None = Field(default=None, ge=-5.0, le=5.0)
    corrected_framing: str | None = Field(default=None, max_length=30)
    corrected_persons: list[dict[str, Any]] | None = None
    notes: str | None = Field(default=None, max_length=2000)


@router.post("/api/v2/nlp/corrections")
async def submit_correction(
    payload: CorrectionPayload,
    x_analyst_id: str | None = Header(default=None, alias="X-Analyst-Id"),
):
    """Record an analyst correction against a signal's NLP output."""
    if not x_analyst_id or not x_analyst_id.strip():
        raise HTTPException(status_code=401, detail="X-Analyst-Id header required")

    async with db.pool.acquire() as conn:
        original = await conn.fetchrow(
            """
            SELECT nlp_sentiment, nlp_framing, nlp_persons
            FROM signals_v2 WHERE id = $1
            """,
            payload.signal_id,
        )
        if original is None:
            raise HTTPException(status_code=404, detail="signal_id not found")

        try:
            await conn.execute(
                """
                INSERT INTO nlp_corrections
                    (signal_id, analyst_id, original_sentiment, corrected_sentiment,
                     original_framing, corrected_framing,
                     original_persons, corrected_persons, notes)
                VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, $9)
                """,
                payload.signal_id,
                x_analyst_id.strip(),
                original["nlp_sentiment"],
                payload.corrected_sentiment,
                original["nlp_framing"],
                payload.corrected_framing,
                json.dumps(original["nlp_persons"]) if original["nlp_persons"] is not None else None,
                json.dumps(payload.corrected_persons) if payload.corrected_persons is not None else None,
                payload.notes,
            )
        except Exception as exc:
            logger.exception("nlp_corrections insert failed")
            raise HTTPException(status_code=503, detail="insert failed — is migration 018 applied?") from exc

    return {"ok": True, "signal_id": payload.signal_id, "recorded_at": datetime.now(timezone.utc).isoformat()}


@router.get("/api/v2/nlp/calibration")
async def calibration_report(
    days: int = Query(7, ge=1, le=90),
):
    """Per-language correction rates and disagreement summaries."""
    async with db.pool.acquire() as conn:
        try:
            rows = await conn.fetch(
                """
                WITH recent AS (
                    SELECT
                        c.id,
                        c.original_sentiment,
                        c.corrected_sentiment,
                        c.original_framing,
                        c.corrected_framing,
                        s.source_lang,
                        s.nlp_method
                    FROM nlp_corrections c
                    JOIN signals_v2 s ON s.id = c.signal_id
                    WHERE c.created_at > NOW() - ($1 || ' days')::INTERVAL
                )
                SELECT
                    COALESCE(source_lang, 'unknown') AS source_lang,
                    COUNT(*) AS corrections,
                    AVG(
                        CASE WHEN corrected_sentiment IS NOT NULL
                                  AND original_sentiment IS NOT NULL
                             THEN ABS(corrected_sentiment - original_sentiment) END
                    ) AS avg_sentiment_delta,
                    AVG(
                        CASE WHEN corrected_framing IS NOT NULL
                                  AND original_framing IS NOT NULL
                                  AND corrected_framing <> original_framing
                             THEN 1 ELSE 0 END
                    ) AS framing_disagree_rate,
                    nlp_method
                FROM recent
                GROUP BY source_lang, nlp_method
                ORDER BY corrections DESC
                """,
                str(days),
            )
        except Exception as exc:
            logger.exception("nlp_corrections aggregate failed")
            raise HTTPException(status_code=503, detail="aggregate failed — is migration 018 applied?") from exc

    return {
        "days": days,
        "items": [
            {
                "source_lang": r["source_lang"],
                "nlp_method": r["nlp_method"],
                "corrections": int(r["corrections"] or 0),
                "avg_sentiment_delta": (
                    round(float(r["avg_sentiment_delta"]), 3)
                    if r["avg_sentiment_delta"] is not None else None
                ),
                "framing_disagree_rate": (
                    round(float(r["framing_disagree_rate"]), 3)
                    if r["framing_disagree_rate"] is not None else None
                ),
            }
            for r in rows
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
