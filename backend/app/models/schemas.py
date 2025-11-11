"""Pydantic models for API requests and responses."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


class Topic(BaseModel):
    """A trending topic."""

    id: str = Field(..., description="Unique topic identifier")
    label: str = Field(..., description="Topic label or title")
    count: int = Field(..., description="Topic frequency/popularity count", ge=0)
    sample_titles: List[str] = Field(
        default_factory=list,
        description="Sample article titles related to this topic"
    )
    sources: List[str] = Field(
        default_factory=list,
        description="Data sources for this topic (e.g., 'gdelt', 'trends', 'wikipedia')"
    )
    confidence: float = Field(
        ...,
        description="Confidence score for topic extraction",
        ge=0.0,
        le=1.0
    )


class TrendsResponse(BaseModel):
    """Response model for trends endpoint."""

    country: str = Field(..., description="ISO 3166-1 alpha-2 country code")
    generated_at: datetime = Field(..., description="Timestamp when data was generated")
    topics: List[Topic] = Field(..., description="List of trending topics")

    class Config:
        json_schema_extra = {
            "example": {
                "country": "CO",
                "generated_at": "2025-01-11T10:30:00Z",
                "topics": [
                    {
                        "id": "topic-1",
                        "label": "Economic Reform",
                        "count": 156,
                        "sample_titles": [
                            "Government announces new economic measures",
                            "Economic reform debate continues"
                        ],
                        "sources": ["gdelt", "trends"],
                        "confidence": 0.87
                    }
                ]
            }
        }
