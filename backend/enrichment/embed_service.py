"""Internal e5 embedding service, hosted inside the nlp_worker process (#223).

Why here: the Fly api-runtime image has no torch (kept light on a 1GB box),
while nlp_worker ships torch+transformers on a 4GB box with ~3GB headroom.
This service exposes the snapshot-identical e5 embedding
(`app.services.research_semantic._build_embed_fn`) over Fly private 6PN
networking so the research plan's semantic lane works in production.

Private only: no [services] entry in fly.toml for this port, so it is
reachable exclusively at
``http://nlp_worker.process.<app>.internal:<EMBED_SERVICE_PORT>``.

Runs as a daemon thread next to the worker loop; failures here must never
take down NLP enrichment.

NOTE: no `from __future__ import annotations` here — postponed annotations
break FastAPI's type resolution for the locally-defined request model.
"""
import logging
import os
import threading

logger = logging.getLogger(__name__)

EMBED_SERVICE_PORT = int(os.getenv("EMBED_SERVICE_PORT", "8090"))
EMBED_MAX_TEXTS = int(os.getenv("EMBED_SERVICE_MAX_TEXTS", "64"))


def _build_app():
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field

    from app.services.research_semantic import embed_texts, embedder_available

    service = FastAPI(title="atlas-embed-internal", docs_url=None, redoc_url=None)

    class EmbedRequest(BaseModel):
        texts: list[str] = Field(..., min_length=1, max_length=EMBED_MAX_TEXTS)

    @service.get("/healthz")
    def healthz() -> dict:
        return {"ok": True, "embedder_available": embedder_available()}

    @service.post("/embed")
    def embed(body: EmbedRequest) -> dict:
        vectors = embed_texts(body.texts)
        if vectors is None:
            raise HTTPException(status_code=503, detail="embedder unavailable")
        return {"vectors": vectors, "dim": len(vectors[0]) if vectors else 0}

    return service


def _serve() -> None:
    import uvicorn

    uvicorn.run(
        _build_app(),
        host="0.0.0.0",
        port=EMBED_SERVICE_PORT,
        log_level="warning",
        access_log=False,
    )


def start_embed_service_thread() -> threading.Thread | None:
    """Start the embed service if the model stack is present. Returns the
    thread, or None when disabled/unavailable."""
    if os.getenv("EMBED_SERVICE_ENABLED", "true").lower() in {"0", "false", "no"}:
        return None
    try:
        from app.services.research_semantic import embedder_available
        if not embedder_available():
            logger.info("embed service skipped: torch/transformers not present")
            return None
    except Exception as exc:
        logger.warning("embed service skipped: %s", exc)
        return None

    thread = threading.Thread(target=_serve, name="embed-service", daemon=True)
    thread.start()
    logger.info("embed service listening on :%d (private 6PN only)", EMBED_SERVICE_PORT)
    return thread
