"""
GDELT Signal to Topic Adapter

Converts GDELTSignal objects to Topic objects for backward compatibility
with the FlowDetector system.

This adapter is shared between flows.py and hexmap.py endpoints to eliminate
code duplication and ensure consistent conversion logic.

Also provides GKGRecord → GDELTSignal conversion for the real GDELT pipeline.
"""

import logging
import hashlib
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone

from app.models.schemas import Topic
from app.models.gdelt_schemas import (
    GDELTSignal,
    GDELTLocation,
    GDELTTone,
    SourceAttribution
)

logger = logging.getLogger(__name__)


# =============================================================================
# Country Centroid Mapping
# =============================================================================

COUNTRY_CENTROIDS: Dict[str, Tuple[float, float, str]] = {
    # Format: "ISO_CODE": (latitude, longitude, "Country Name")
    # Top 50 countries by news coverage
    "US": (37.0902, -95.7129, "United States"),
    "GB": (55.3781, -3.4360, "United Kingdom"),
    "CA": (56.1304, -106.3468, "Canada"),
    "AU": (-25.2744, 133.7751, "Australia"),
    "DE": (51.1657, 10.4515, "Germany"),
    "FR": (46.2276, 2.2137, "France"),
    "IT": (41.8719, 12.5674, "Italy"),
    "ES": (40.4637, -3.7492, "Spain"),
    "NL": (52.1326, 5.2913, "Netherlands"),
    "BE": (50.5039, 4.4699, "Belgium"),
    "CH": (46.8182, 8.2275, "Switzerland"),
    "AT": (47.5162, 14.5501, "Austria"),
    "SE": (60.1282, 18.6435, "Sweden"),
    "NO": (60.4720, 8.4689, "Norway"),
    "DK": (56.2639, 9.5018, "Denmark"),
    "FI": (61.9241, 25.7482, "Finland"),
    "PL": (51.9194, 19.1451, "Poland"),
    "CZ": (49.8175, 15.4730, "Czech Republic"),
    "RU": (61.5240, 105.3188, "Russia"),
    "UA": (48.3794, 31.1656, "Ukraine"),
    "TR": (38.9637, 35.2433, "Turkey"),
    "CN": (35.8617, 104.1954, "China"),
    "JP": (36.2048, 138.2529, "Japan"),
    "KR": (35.9078, 127.7669, "South Korea"),
    "IN": (20.5937, 78.9629, "India"),
    "PK": (30.3753, 69.3451, "Pakistan"),
    "BD": (23.6850, 90.3563, "Bangladesh"),
    "ID": (-0.7893, 113.9213, "Indonesia"),
    "TH": (15.8700, 100.9925, "Thailand"),
    "VN": (14.0583, 108.2772, "Vietnam"),
    "PH": (12.8797, 121.7740, "Philippines"),
    "MY": (4.2105, 101.9758, "Malaysia"),
    "SG": (1.3521, 103.8198, "Singapore"),
    "BR": (-14.2350, -51.9253, "Brazil"),
    "AR": (-38.4161, -63.6167, "Argentina"),
    "MX": (23.6345, -102.5528, "Mexico"),
    "CO": (4.5709, -74.2973, "Colombia"),
    "CL": (-35.6751, -71.5430, "Chile"),
    "PE": (-9.1900, -75.0152, "Peru"),
    "VE": (6.4238, -66.5897, "Venezuela"),
    "ZA": (-30.5595, 22.9375, "South Africa"),
    "EG": (26.8206, 30.8025, "Egypt"),
    "NG": (9.0820, 8.6753, "Nigeria"),
    "KE": (-0.0236, 37.9062, "Kenya"),
    "IL": (31.0461, 34.8516, "Israel"),
    "SA": (23.8859, 45.0792, "Saudi Arabia"),
    "AE": (23.4241, 53.8478, "United Arab Emirates"),
    "IR": (32.4279, 53.6880, "Iran"),
    "IQ": (33.2232, 43.6793, "Iraq"),
    "SY": (34.8021, 38.9968, "Syria"),
}

def get_country_centroid(country_code: str) -> Tuple[float, float, str]:
    """
    Get centroid coordinates for a country by ISO code.

    Args:
        country_code: ISO 3166-1 alpha-2 code (e.g., "US", "BR")

    Returns:
        Tuple of (latitude, longitude, country_name)
        Returns (0.0, 0.0, country_code) if country not in mapping
    """
    if country_code in COUNTRY_CENTROIDS:
        return COUNTRY_CENTROIDS[country_code]

    logger.warning(f"Country centroid not found for '{country_code}', using (0, 0)")
    return (0.0, 0.0, country_code)


def normalize_theme_label(theme_code: str) -> str:
    """
    Convert GDELT theme code to human-readable label.

    Examples:
        "WB_632_WOMEN_IN_POLITICS" → "Women in Politics"
        "TAX_TERROR" → "Terrorism"
        "ECON_INFLATION" → "Economic Inflation"

    Args:
        theme_code: Raw GDELT theme code

    Returns:
        Human-friendly label
    """
    # Simple normalization: remove prefix, replace underscores, title case
    # More sophisticated mapping can be added later

    # Remove common prefixes
    for prefix in ["WB_", "TAX_", "ECON_", "ENV_", "UNGP_", "CRISISLEX_"]:
        if theme_code.startswith(prefix):
            theme_code = theme_code[len(prefix):]
            break

    # Replace underscores with spaces and title case
    label = theme_code.replace("_", " ").title()

    # Handle numeric codes (e.g., "632 Women In Politics" → "Women In Politics")
    parts = label.split()
    if parts and parts[0].isdigit():
        label = " ".join(parts[1:])

    return label if label else theme_code


# =============================================================================
# GKGRecord → GDELTSignal Converter (Real GDELT Pipeline)
# =============================================================================

def convert_gkg_to_signals(record) -> List[GDELTSignal]:
    """
    Convert a single GKGRecord to multiple GDELTSignal objects (one per theme).

    This is the critical function that bridges the GDELT parser to the signal schema.

    Strategy (based on user decisions):
    - Create ONE signal per theme (not per record)
    - Use country centroid if no location data available
    - Preserve all GKGCount data in theme_counts dict

    Args:
        record: GKGRecord from gdelt_parser.py

    Returns:
        List of GDELTSignal objects (one for each theme)
        Returns empty list if record has no themes or is invalid

    Raises:
        ValueError: If record is missing critical fields
    """
    from app.services.gdelt_parser import GKGRecord, GKGLocation as ParserLocation, GKGTone as ParserTone

    if not isinstance(record, GKGRecord):
        raise ValueError(f"Expected GKGRecord, got {type(record)}")

    # === Validate Required Fields ===
    if not record.themes:
        logger.debug(f"Skipping record {record.record_id}: no themes")
        return []

    # === Prepare Locations ===
    locations_list: List[GDELTLocation] = []
    primary_location: Optional[GDELTLocation] = None

    if record.locations:
        # Convert parser locations to signal locations
        for loc in record.locations:
            locations_list.append(
                GDELTLocation(
                    country_code=loc.country_code,
                    country_name=loc.country_name,
                    location_name=loc.location_name,
                    latitude=loc.latitude,
                    longitude=loc.longitude,
                    location_type=loc.location_type,
                    feature_id=loc.feature_id,
                    char_offset=loc.char_offset,
                    mention_count=1  # Parser doesn't track mention count yet
                )
            )
        primary_location = locations_list[0]  # First location is primary
    else:
        # No location data - use country centroid fallback
        # Try to extract country from source_name or use default
        country_code = "US"  # Default fallback
        logger.debug(f"Record {record.record_id} has no locations, using centroid for {country_code}")

        lat, lon, country_name = get_country_centroid(country_code)
        primary_location = GDELTLocation(
            country_code=country_code,
            country_name=country_name,
            location_name=None,
            latitude=lat,
            longitude=lon,
            location_type=1,  # Country-level
            feature_id=None,
            char_offset=None,
            mention_count=1
        )
        locations_list = [primary_location]

    # === Convert Tone ===
    tone = GDELTTone(
        overall=record.tone.overall,
        positive_pct=record.tone.positive_pct,
        negative_pct=record.tone.negative_pct,
        polarity=record.tone.polarity,
        activity_density=record.tone.activity_density,
        self_reference=record.tone.self_group_ref
    )

    # === Build Theme Counts Dictionary ===
    theme_counts: Dict[str, int] = {}
    for count_entry in record.counts:
        # Aggregate by count_type (theme)
        if count_entry.count_type in theme_counts:
            theme_counts[count_entry.count_type] += count_entry.number
        else:
            theme_counts[count_entry.count_type] = count_entry.number

    # If no counts available, default to 1 for each theme
    if not theme_counts:
        theme_counts = {theme: 1 for theme in record.themes}

    # === Calculate Intensity (normalized by max possible count) ===
    total_count = sum(theme_counts.values())
    max_possible = 500  # Calibration: 500 mentions = max intensity
    intensity = min(total_count / max_possible, 1.0)

    # === Round timestamp to 15-minute bucket ===
    bucket_15min = record.timestamp.replace(
        minute=(record.timestamp.minute // 15) * 15,
        second=0,
        microsecond=0
    )

    # === Source Attribution ===
    sources = SourceAttribution(
        gdelt=True,
        google_trends=False,
        wikipedia=False
    )

    # === URL Hash for Deduplication ===
    url_hash = hashlib.md5(record.source_url.encode()).hexdigest() if record.source_url else "no_url"

    # === Create One Signal Per Theme ===
    signals: List[GDELTSignal] = []

    for theme in record.themes:
        # Determine primary theme (highest count)
        primary_theme = max(theme_counts, key=theme_counts.get) if theme_counts else theme

        # Generate theme labels
        theme_labels = [normalize_theme_label(t) for t in record.themes]

        # Unique signal ID per theme
        signal_id = f"{record.record_id}_{theme}"

        try:
            signal = GDELTSignal(
                # Identity
                signal_id=signal_id,
                timestamp=record.timestamp,
                bucket_15min=bucket_15min,
                source_collection_id=record.source_collection,

                # Geographic
                locations=locations_list,
                primary_location=primary_location,

                # Thematic
                themes=record.themes,
                theme_labels=theme_labels,
                theme_counts=theme_counts,
                primary_theme=primary_theme,

                # Sentiment
                tone=tone,

                # Derived fields (auto-computed by validators)
                intensity=intensity,
                sentiment_label="neutral",  # Auto-computed by validator
                geographic_precision="country",  # Auto-computed by validator

                # Tier 2 fields (optional)
                persons=record.persons if record.persons else None,
                organizations=record.organizations if record.organizations else None,
                source_url=record.source_url if record.source_url else None,
                source_outlet=record.source_name if record.source_name else None,

                # Quality & Provenance
                sources=sources,
                confidence=sources.confidence_score(),

                # Deduplication
                url_hash=url_hash,
                duplicate_count=1,
                duplicate_outlets=[]
            )
            signals.append(signal)

        except Exception as e:
            logger.error(f"Error creating signal for theme '{theme}' in record {record.record_id}: {e}")
            continue

    logger.info(f"Converted GKGRecord {record.record_id} → {len(signals)} signals ({len(record.themes)} themes)")
    return signals


# =============================================================================
# GDELTSignal → Topic Converter (Backward Compatibility)
# =============================================================================

def gdelt_signal_to_topic(signal: GDELTSignal) -> Topic:
    """
    Convert GDELT signal to Topic for flow detector compatibility.

    This adapter ensures backward compatibility with the existing FlowDetector
    which expects Topic objects. Uses human-readable theme_labels (not raw GDELT codes).

    Args:
        signal: GDELTSignal object from fetch_gdelt_signals()

    Returns:
        Topic object compatible with FlowDetector
    """
    # Sum all theme counts to get total mention volume
    total_count = sum(signal.theme_counts.values()) if signal.theme_counts else 1

    # Use human-readable theme_labels (e.g., "Terrorism") not GDELT codes (e.g., "TAX_TERROR")
    primary_label = signal.theme_labels[0] if signal.theme_labels else signal.primary_theme

    return Topic(
        id=signal.signal_id,
        label=primary_label,
        count=total_count,
        sample_titles=[],  # GDELTSignal doesn't have sample_titles, leave empty
        sources=["gdelt"],
        confidence=signal.confidence
    )


def convert_gdelt_to_topics(
    signals_by_country: Dict[str, Tuple[List[GDELTSignal], datetime]]
) -> Tuple[Dict[str, Tuple[List[Topic], datetime]], Dict[str, List[GDELTSignal]]]:
    """
    Convert GDELT signals to Topics for all countries.

    Args:
        signals_by_country: Dict mapping country code to (signals, timestamp)

    Returns:
        Tuple of:
        - Dict mapping country code to (topics, timestamp) for FlowDetector
        - Dict mapping country code to original signals (for intensity calculation)
    """
    topics_by_country = {}
    signals_only = {}

    for country, (signals, timestamp) in signals_by_country.items():
        topics = [gdelt_signal_to_topic(signal) for signal in signals]
        topics_by_country[country] = (topics, timestamp)
        signals_only[country] = signals
        logger.debug(f"Converted {len(signals)} GDELT signals to Topics for {country}")

    return topics_by_country, signals_only
