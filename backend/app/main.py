"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1 import health, trends

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title="Observatory Global API",
    description="Global Narrative Observatory - Real-time trends aggregation and analysis",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(trends.router, prefix="/v1/trends", tags=["Trends"])


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Starting Observatory Global API in {settings.APP_ENV} mode")
    logger.info(f"API listening on port {settings.APP_PORT}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info("Shutting down Observatory Global API")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.APP_PORT,
        reload=settings.APP_ENV == "development",
    )
