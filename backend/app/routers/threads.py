from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.services.thread_intelligence import fetch_thread_detail, fetch_threads

router = APIRouter(prefix="/api/v2", tags=["threads"])


@router.get("/threads")
async def get_threads(
    hours: int = Query(24, ge=1, le=720),
    limit: int = Query(10, ge=1, le=50),
) -> dict:
    return {
        "beta": True,
        "hours": hours,
        "contract": "living-narrative-threads-v0",
        "threads": await fetch_threads(hours=hours, limit=limit),
    }


@router.get("/threads/{thread_id}")
async def get_thread_detail(
    thread_id: str,
    hours: int = Query(24, ge=1, le=720),
) -> dict:
    thread = await fetch_thread_detail(thread_id=thread_id, hours=hours)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {
        "beta": True,
        "hours": hours,
        "contract": "living-narrative-threads-v0",
        "thread": thread,
    }
