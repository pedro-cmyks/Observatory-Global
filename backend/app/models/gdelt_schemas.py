"""
GDELT-Shaped Data Models - Production Schema

This module defines the complete GDELT GKG (Global Knowledge Graph) signal structure
that is structurally identical to real GDELT 2.0 data.

This is a "full dress rehearsal" schema - placeholders generated with this structure
will be drop-in compatible with the real GDELT parser when implemented.

Based on:
- GDELT_SCHEMA_ANALYSIS.md (400+ lines of field documentation)
- DataSignalArchitect validation and refinements
- NarrativeGeopoliticsAnalyst narrative pattern validation

Tier 1 Fields (MVP - This Implementation):
- GKGRECORDID (Column 1)
- V2DATE (Column 2)
- V2SourceCollectionIdentifier (Column 3)
- V2Locations (Column 4)
- V2Tone (Column 7)
- V2Themes (Column 8)
- V2Counts (Column 15)

Tier 2 Expansion (Future - Backward Compatible):
- V2Persons (Column 5)
- V2Organizations (Column 6)
- V2GCAM (Column 9)
- V2SourceCommonName (Column 20)
- V2DocumentIdentifier (Column 21)
"""

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List, Dict, Optional
import hashlib


class GDELTLocation(BaseModel):
    """
    V2Locations field from GDELT GKG (Column 4).

    Parses semicolon-separated location blocks with structure:
    Type#FullName#CountryCode#ADM1Code#Lat#Long#FeatureID#OffsetCharacters

    Example:
    1#United States#US##38#-97#US#1;1#New York#US#USNY#40.7128#-74.006#5128581#234
    """

    country_code: str = Field(..., description="ISO 3166-1 alpha-2 code (e.g., 'US', 'BR', 'GB')")
    country_name: str = Field(..., description="Human-readable country name")
    location_name: Optional[str] = Field(None, description="City/region name if available")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Geographic latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Geographic longitude")
    location_type: int = Field(
        ...,
        ge=1,
        le=5,
        description="1=Country, 2=US State, 3=US City, 4=World City, 5=World State"
    )
    feature_id: Optional[str] = Field(None, description="GeoNames feature ID for precise geocoding")

    # Prominence tracking (for primary_location selection)
    char_offset: Optional[int] = Field(None, description="Character position where location first mentioned in article")
    mention_count: int = Field(default=1, ge=1, description="Number of times location mentioned in article")

    class Config:
        json_schema_extra = {
            "example": {
                "country_code": "US",
                "country_name": "United States",
                "location_name": "New York",
                "latitude": 40.7128,
                "longitude": -74.0060,
                "location_type": 3,
                "feature_id": "5128581",
                "char_offset": 234,
                "mention_count": 3
            }
        }


class GDELTTone(BaseModel):
    """
    V2Tone field from GDELT GKG (Column 7).

    Six comma-separated values:
    Tone,PositiveScore,NegativeScore,Polarity,ActivityDensity,SelfGroupRef

    Example:
    -3.21,2.1,45.2,1.8,12,5

    Typical value ranges (from GDELT_SCHEMA_ANALYSIS.md lines 230-234):
    - Most articles: -10 to +10
    - Crisis/conflict: -30 to -50
    - Diplomatic cooperation: +10 to +30
    """

    overall: float = Field(
        ...,
        ge=-100.0,
        le=100.0,
        description="Overall sentiment score: -100 (very negative) to +100 (very positive)"
    )
    positive_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of positive words in article"
    )
    negative_pct: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Percentage of negative words in article"
    )
    polarity: float = Field(..., ge=0.0, description="Emotional intensity (distance from neutral)")
    activity_density: float = Field(..., ge=0.0, description="Action word density")
    self_reference: float = Field(..., ge=0.0, description="First-person plural references (we, us, our)")

    class Config:
        json_schema_extra = {
            "example": {
                "overall": -3.5,
                "positive_pct": 2.1,
                "negative_pct": 45.2,
                "polarity": 1.8,
                "activity_density": 12.0,
                "self_reference": 5.0
            }
        }


class SourceAttribution(BaseModel):
    """
    Track which data sources contributed to this signal.

    Supports graceful degradation when GDELT API down:
    - gdelt=True, trends=True, wiki=True: confidence = 1.0 (all sources)
    - gdelt=True, trends=False, wiki=False: confidence = 0.7 (GDELT only)
    - gdelt=False, trends=True, wiki=True: confidence = 0.3 (no authoritative source)
    """

    gdelt: bool = Field(default=False, description="GDELT GKG data present")
    google_trends: bool = Field(default=False, description="Google Trends data present")
    wikipedia: bool = Field(default=False, description="Wikipedia data present")

    def confidence_score(self) -> float:
        """Calculate confidence based on source availability."""
        score = 0.0
        if self.gdelt:
            score += 0.7  # GDELT is primary/authoritative
        if self.google_trends:
            score += 0.15
        if self.wikipedia:
            score += 0.15
        return score

    class Config:
        json_schema_extra = {
            "example": {
                "gdelt": True,
                "google_trends": True,
                "wikipedia": False
            }
        }


class GDELTSignal(BaseModel):
    """
    Complete GDELT GKG signal - Tier 1 fields only (Tier 2 expansion fields Optional).

    This schema is production-ready and drop-in compatible with real GDELT parser.
    All placeholders generated with this structure will work seamlessly when
    switching from placeholder data to real GDELT data.

    Refinements from DataSignalArchitect validation:
    - Added source_collection_id (Column 3)
    - Replaced data_source: str with sources: SourceAttribution
    - Added deduplication fields (url_hash, duplicate_count, duplicate_outlets)
    - Added derived fields (intensity, sentiment_label, geographic_precision)
    - Added prominence tracking to GDELTLocation
    - Added SignalsMetadata for API response wrapper
    """

    # ===== IDENTITY (Columns 1, 2, 3) =====
    signal_id: str = Field(..., description="GKGRECORDID format: YYYYMMDDHHMMSS-T##")
    timestamp: datetime = Field(..., description="V2DATE - Article publication time (UTC)")
    bucket_15min: datetime = Field(
        ...,
        description="Rounded to 15-min intervals to match GDELT publish cadence (YYYYMMDDHHMMSS → YYYYMMDDHH{00|15|30|45}00)"
    )
    source_collection_id: int = Field(
        default=1,
        ge=1,
        le=3,
        description="1=Web, 2=CitizenMedia, 3=DiscussionForum (from Column 3)"
    )

    # ===== GEOGRAPHIC (Column 4 - V2Locations) =====
    locations: List[GDELTLocation] = Field(
        ...,
        min_length=1,
        description="All locations mentioned in article (parsed from V2Locations)"
    )
    primary_location: GDELTLocation = Field(
        ...,
        description="Most relevant location (highest mention_count, earliest char_offset, or first in list)"
    )

    # ===== THEMATIC (Column 8 - V2Themes, Column 15 - V2Counts) =====
    themes: List[str] = Field(
        ...,
        description="Raw GDELT taxonomy codes (e.g., ['TAX_TERROR', 'ECON_INFLATION'])"
    )
    theme_labels: List[str] = Field(
        ...,
        description="Human-friendly labels for themes (e.g., ['Terrorism', 'Inflation'])"
    )
    theme_counts: Dict[str, int] = Field(
        ...,
        description="V2Counts parsed: theme → mention frequency (e.g., {'ECON_INFLATION': 52, 'PROTEST': 34})"
    )
    primary_theme: str = Field(..., description="Most mentioned theme (highest count in theme_counts)")

    # ===== SENTIMENT (Column 7 - V2Tone) =====
    tone: GDELTTone = Field(..., description="Complete V2Tone breakdown (6 values)")

    # ===== DERIVED FIELDS (computed during parsing for frontend efficiency) =====
    intensity: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Normalized intensity: sum(theme_counts.values()) / global_max_count (for heatmap visualization)"
    )
    sentiment_label: str = Field(
        ...,
        description="Categorical: 'very_negative' | 'negative' | 'neutral' | 'positive' | 'very_positive'"
    )
    geographic_precision: str = Field(
        ...,
        description="'country' | 'state' | 'city' based on primary_location.location_type"
    )

    # ===== TIER 2 EXPANSION (Optional - backward compatible) =====
    persons: Optional[List[str]] = Field(None, description="V2Persons (Column 5) - Named individuals")
    organizations: Optional[List[str]] = Field(None, description="V2Organizations (Column 6) - Institutions")
    source_url: Optional[str] = Field(None, description="V2DocumentIdentifier (Column 21) - Article URL")
    source_outlet: Optional[str] = Field(None, description="V2SourceCommonName (Column 20) - News outlet")

    # ===== QUALITY & PROVENANCE =====
    sources: SourceAttribution = Field(..., description="Which data sources contributed to this signal")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Composite confidence: source_availability × location_precision × (1 - duplicate_penalty)"
    )

    # ===== DEDUPLICATION (prevents counting same story multiple times) =====
    url_hash: str = Field(..., description="MD5 hash of source_url for deduplication")
    duplicate_count: int = Field(default=1, ge=1, description="Number of duplicate articles merged into this signal")
    duplicate_outlets: List[str] = Field(
        default_factory=list,
        description="Other outlets covering same story (for source diversity metric)"
    )

    @field_validator('sentiment_label', mode='before')
    @classmethod
    def compute_sentiment_label(cls, v, info):
        """Auto-compute sentiment label from tone if not provided."""
        if v is None and 'tone' in info.data:
            tone_obj = info.data['tone']
            tone_val = tone_obj.overall if isinstance(tone_obj, GDELTTone) else tone_obj.get('overall', 0.0)

            if tone_val < -10:
                return "very_negative"
            elif tone_val < -2:
                return "negative"
            elif tone_val < 2:
                return "neutral"
            elif tone_val < 10:
                return "positive"
            else:
                return "very_positive"
        return v

    @field_validator('geographic_precision', mode='before')
    @classmethod
    def compute_geo_precision(cls, v, info):
        """Auto-compute geographic precision from primary_location if not provided."""
        if v is None and 'primary_location' in info.data:
            loc = info.data['primary_location']
            loc_type = loc.location_type if isinstance(loc, GDELTLocation) else loc.get('location_type', 1)

            if loc_type == 1:
                return "country"
            elif loc_type in [2, 5]:
                return "state"
            else:
                return "city"
        return v

    @field_validator('url_hash', mode='before')
    @classmethod
    def compute_url_hash(cls, v, info):
        """Auto-generate URL hash if not provided."""
        if v is None and 'source_url' in info.data:
            source_url = info.data.get('source_url', '')
            if source_url:
                return hashlib.md5(source_url.encode()).hexdigest()
            return "placeholder_hash"
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "signal_id": "20250115120000-T52",
                "timestamp": "2025-01-15T12:00:00Z",
                "bucket_15min": "2025-01-15T12:00:00Z",
                "source_collection_id": 1,
                "locations": [
                    {
                        "country_code": "US",
                        "country_name": "United States",
                        "location_name": "New York",
                        "latitude": 40.7128,
                        "longitude": -74.0060,
                        "location_type": 3,
                        "feature_id": "5128581",
                        "char_offset": 45,
                        "mention_count": 3
                    }
                ],
                "primary_location": {
                    "country_code": "US",
                    "country_name": "United States",
                    "location_name": "New York",
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "location_type": 3,
                    "feature_id": "5128581",
                    "char_offset": 45,
                    "mention_count": 3
                },
                "themes": ["ECON_INFLATION", "PROTEST"],
                "theme_labels": ["Economic Inflation", "Protests"],
                "theme_counts": {
                    "ECON_INFLATION": 52,
                    "PROTEST": 34
                },
                "primary_theme": "ECON_INFLATION",
                "tone": {
                    "overall": -3.5,
                    "positive_pct": 2.1,
                    "negative_pct": 45.2,
                    "polarity": 1.8,
                    "activity_density": 12.0,
                    "self_reference": 5.0
                },
                "intensity": 0.87,
                "sentiment_label": "negative",
                "geographic_precision": "city",
                "persons": None,  # Tier 2
                "organizations": None,  # Tier 2
                "source_url": None,  # Tier 2
                "source_outlet": None,  # Tier 2
                "sources": {
                    "gdelt": True,
                    "google_trends": True,
                    "wikipedia": False
                },
                "confidence": 0.85,
                "url_hash": "a3f5e8b2c1d4e9f7a0b3c6d8e2f5a9b1",
                "duplicate_count": 3,
                "duplicate_outlets": ["nytimes.com", "wsj.com"]
            }
        }


# ===== API RESPONSE WRAPPER =====

class SignalsMetadata(BaseModel):
    """
    Response metadata for context and debugging.

    Provides frontend with:
    - Data quality indicator (placeholder vs real vs degraded)
    - Global max count for heatmap intensity normalization
    - Coverage information (which countries returned)
    - Timestamp range for time-series analysis
    """

    generated_at: datetime = Field(..., description="When this response was generated")
    data_quality: str = Field(
        ...,
        description="'placeholder' | 'real' | 'degraded' - Indicates data source status"
    )
    countries_requested: List[str] = Field(..., description="Countries user requested")
    countries_returned: List[str] = Field(..., description="Countries with data in response (may be fewer if no signals)")
    total_signals: int = Field(..., ge=0, description="Total signals in response")
    signals_deduplicated: int = Field(..., ge=0, description="Number of duplicate signals merged")
    time_window: str = Field(..., description="Time window used (e.g., '6h', '24h')")
    oldest_signal: datetime = Field(..., description="Timestamp of oldest signal in response")
    newest_signal: datetime = Field(..., description="Timestamp of newest signal in response")
    global_max_count: int = Field(
        ...,
        ge=0,
        description="Maximum theme_count sum across all signals (for frontend intensity normalization)"
    )
    avg_confidence: float = Field(..., ge=0.0, le=1.0, description="Average confidence score across all signals")

    class Config:
        json_schema_extra = {
            "example": {
                "generated_at": "2025-01-15T12:05:00Z",
                "data_quality": "placeholder",
                "countries_requested": ["US", "CO", "BR"],
                "countries_returned": ["US", "CO", "BR"],
                "total_signals": 127,
                "signals_deduplicated": 23,
                "time_window": "15m",
                "oldest_signal": "2025-01-15T11:45:00Z",
                "newest_signal": "2025-01-15T12:00:00Z",
                "global_max_count": 156,
                "avg_confidence": 0.87
            }
        }


class GDELTSignalsResponse(BaseModel):
    """
    Complete API response for /api/v1/signals endpoint.

    Wraps signals array with metadata for frontend context.
    This wrapper ensures frontend has all information needed for:
    - Heatmap intensity normalization (global_max_count)
    - Data quality indicators (data_quality badge)
    - Debugging (why is country X missing? check countries_returned)
    """

    signals: List[GDELTSignal] = Field(..., description="Signal records")
    metadata: SignalsMetadata = Field(..., description="Context about this response")

    class Config:
        json_schema_extra = {
            "example": {
                "signals": [
                    {
                        "signal_id": "20250115120000-T52",
                        "timestamp": "2025-01-15T12:00:00Z",
                        "themes": ["ECON_INFLATION", "PROTEST"],
                        "tone": {"overall": -3.5, "positive_pct": 2.1, "negative_pct": 45.2, "polarity": 1.8, "activity_density": 12.0, "self_reference": 5.0},
                        "intensity": 0.87,
                        "primary_location": {"country_code": "US", "latitude": 40.7128, "longitude": -74.0060}
                    }
                ],
                "metadata": {
                    "generated_at": "2025-01-15T12:05:00Z",
                    "data_quality": "placeholder",
                    "total_signals": 127,
                    "global_max_count": 156,
                    "avg_confidence": 0.87
                }
            }
        }


__all__ = [
    "GDELTLocation",
    "GDELTTone",
    "SourceAttribution",
    "GDELTSignal",
    "SignalsMetadata",
    "GDELTSignalsResponse",
]
