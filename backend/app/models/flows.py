"""Pydantic models for flows API."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict


class TopicSummary(BaseModel):
    """Summary of a topic within a flow or hotspot."""

    label: str = Field(..., description="Topic label")
    count: int = Field(..., description="Topic count/frequency", ge=0)
    confidence: float = Field(..., description="Topic confidence score", ge=0.0, le=1.0)


class GDELTSignalSummary(BaseModel):
    """
    Lightweight summary of GDELT signal for Hotspot display.

    Preserves essential narrative context without full signal payload.
    **Phase 3.5 Enhancement:** Now includes actor data (persons, organizations, outlets)
    """
    signal_id: str = Field(..., description="GKGRECORDID")
    timestamp: datetime = Field(..., description="When signal was captured")

    # Thematic context (preserve ALL themes, not just primary)
    themes: List[str] = Field(..., description="All GDELT theme codes")
    theme_labels: List[str] = Field(..., description="Human-readable theme names")
    theme_counts: Dict[str, int] = Field(..., description="Mention frequency per theme")
    primary_theme: str = Field(..., description="Most mentioned theme")

    # Sentiment context
    sentiment_label: str = Field(..., description="very_negative | negative | neutral | positive | very_positive")
    sentiment_score: float = Field(..., ge=-100, le=100, description="Tone score")

    # Geographic precision
    country_code: str = Field(..., description="ISO country code")
    location_name: Optional[str] = Field(None, description="City/region if available")

    # **NEW: Actor context (Phase 3.5 - Narrative Intelligence Enhancement)**
    persons: Optional[List[str]] = Field(default=None, description="Key persons mentioned (V2Persons)")
    organizations: Optional[List[str]] = Field(default=None, description="Key organizations mentioned (V2Organizations)")
    source_outlet: Optional[str] = Field(default=None, description="News outlet (e.g., 'reuters.com', 'bbc.com')")

    class Config:
        json_schema_extra = {
            "example": {
                "signal_id": "20250119120000-T52",
                "timestamp": "2025-01-19T12:00:00Z",
                "themes": ["ECON_INFLATION", "PROTEST", "TAX_FNCACT"],
                "theme_labels": ["Economic Inflation", "Protests", "Financial Crisis"],
                "theme_counts": {"ECON_INFLATION": 52, "PROTEST": 34, "TAX_FNCACT": 18},
                "primary_theme": "ECON_INFLATION",
                "sentiment_label": "negative",
                "sentiment_score": -8.5,
                "country_code": "AR",
                "location_name": "Buenos Aires",
                "persons": ["Javier Milei", "Sergio Massa"],
                "organizations": ["Central Bank of Argentina", "IMF"],
                "source_outlet": "reuters.com"
            }
        }


class Hotspot(BaseModel):
    """A country with high topic intensity."""

    country_code: str = Field(..., description="ISO 3166-1 alpha-2 country code")
    country_name: str = Field(..., description="Human-readable country name")
    latitude: float = Field(..., description="Country centroid latitude", ge=-90.0, le=90.0)
    longitude: float = Field(..., description="Country centroid longitude", ge=-180.0, le=180.0)
    intensity: float = Field(
        ...,
        description="Hotspot intensity weighted by volume, velocity, and confidence [0,1]",
        ge=0.0,
        le=1.0,
    )
    topic_count: int = Field(..., description="Number of trending topics", ge=0)
    confidence: float = Field(
        ...,
        description="Average confidence score of topics",
        ge=0.0,
        le=1.0,
    )
    top_topics: List[TopicSummary] = Field(
        default_factory=list,
        description="Top topics contributing to the hotspot",
    )

    # NEW FIELDS - Preserve signal context
    signals: List[GDELTSignalSummary] = Field(
        default_factory=list,
        description="Full signal summaries with narrative context"
    )

    dominant_sentiment: str = Field(
        default="neutral",
        description="Most common sentiment_label across signals"
    )

    avg_sentiment_score: float = Field(
        default=0.0,
        ge=-100.0,
        le=100.0,
        description="Average tone score across all signals"
    )

    theme_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Aggregated theme counts across all signals (e.g., {'Terrorism': 120, 'Protests': 85})"
    )

    # **NEW: Source diversity metrics (Phase 3.5)**
    source_count: int = Field(
        default=0,
        ge=0,
        description="Number of unique news outlets covering this hotspot"
    )

    source_diversity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Source diversity ratio: unique_outlets / total_signals (0=concentrated, 1=highly diverse)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "country_code": "US",
                "country_name": "United States",
                "latitude": 37.09,
                "longitude": -95.71,
                "intensity": 0.85,
                "topic_count": 47,
                "confidence": 0.89,
                "top_topics": [
                    {"label": "election results", "count": 123, "confidence": 0.92},
                    {"label": "climate summit", "count": 89, "confidence": 0.88},
                ],
            }
        }


class Flow(BaseModel):
    """Information flow between two countries."""

    from_country: str = Field(..., description="Source country (ISO alpha-2)")
    to_country: str = Field(..., description="Destination country (ISO alpha-2)")
    heat: float = Field(
        ...,
        description="Flow heat score: similarity × time_proximity [0,1]",
        ge=0.0,
        le=1.0,
    )
    similarity: float = Field(
        ...,
        description="TF-IDF cosine similarity between topics [0,1]",
        ge=0.0,
        le=1.0,
    )
    time_delta_minutes: float = Field(
        ...,
        description="Time difference between topic appearances (minutes)",
        ge=0.0,
    )
    shared_topics: List[str] = Field(
        default_factory=list,
        description="Topics shared between countries",
    )
    from_coords: List[float] = Field(
        ...,
        description="Source country coordinates [longitude, latitude]",
        min_length=2,
        max_length=2,
    )
    to_coords: List[float] = Field(
        ...,
        description="Destination country coordinates [longitude, latitude]",
        min_length=2,
        max_length=2,
    )

    class Config:
        json_schema_extra = {
            "example": {
                "from_country": "US",
                "to_country": "CO",
                "heat": 0.72,
                "similarity": 0.85,
                "time_delta_minutes": 180.0,
                "shared_topics": ["election fraud claims", "voting irregularities"],
                "from_coords": [-95.71, 37.09],
                "to_coords": [-74.30, 4.57],
            }
        }


class FlowsMetadata(BaseModel):
    """Metadata about the flow detection computation."""

    formula: str = Field(
        default="heat = similarity × exp(-Δt / 6h)",
        description="Heat calculation formula",
    )
    threshold: float = Field(..., description="Minimum heat threshold applied")
    time_window_hours: float = Field(..., description="Time window used for analysis (hours)")
    total_flows_computed: int = Field(..., description="Total flows computed before filtering")
    flows_returned: int = Field(..., description="Flows returned after threshold filter")
    countries_analyzed: List[str] = Field(..., description="Countries included in analysis")

    # **NEW: Data quality indicators (Phase 3.5)**
    data_source: str = Field(
        default="real_gdelt",
        description="Data source type: 'real_gdelt' | 'placeholder' | 'mixed'"
    )
    data_quality: str = Field(
        default="production",
        description="Quality tier: 'production' | 'dev_placeholder' | 'test'"
    )
    placeholder_reason: Optional[str] = Field(
        default=None,
        description="Explanation if using placeholder data (e.g., 'GDELT download unavailable')"
    )


class FlowsResponse(BaseModel):
    """Response model for flows endpoint."""

    hotspots: List[Hotspot] = Field(
        default_factory=list,
        description="Countries with high topic intensity",
    )
    flows: List[Flow] = Field(
        default_factory=list,
        description="Information flows between countries",
    )
    metadata: FlowsMetadata = Field(..., description="Computation metadata")
    generated_at: datetime = Field(..., description="Timestamp when data was generated")

    class Config:
        json_schema_extra = {
            "example": {
                "hotspots": [
                    {
                        "country": "US",
                        "intensity": 0.85,
                        "topic_count": 47,
                        "top_topics": [
                            {"label": "election results", "count": 123, "confidence": 0.92}
                        ],
                    }
                ],
                "flows": [
                    {
                        "from_country": "US",
                        "to_country": "CO",
                        "heat": 0.72,
                        "similarity_score": 0.85,
                        "time_delta_hours": 3.0,
                        "shared_topics": ["election fraud claims"],
                    }
                ],
                "metadata": {
                    "formula": "heat = similarity × exp(-Δt / 6h)",
                    "threshold": 0.5,
                    "time_window_hours": 24.0,
                    "total_flows_computed": 45,
                    "flows_returned": 12,
                    "countries_analyzed": ["US", "CO", "BR"],
                },
                "generated_at": "2025-01-12T10:30:00Z",
            }
        }
