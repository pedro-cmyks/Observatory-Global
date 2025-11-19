"""
GDELT GKG v2.1 Parser

This module provides streaming parsers for GDELT Global Knowledge Graph data files.
The parser handles the tab-delimited CSV format with 27 columns per row.

GDELT GKG 2.1 Column Mapping:
    Index 0:  GKGRECORDID - Unique record identifier
    Index 1:  V2DATE - Publication timestamp (YYYYMMDDHHMMSS)
    Index 2:  V2SourceCollectionIdentifier - Source type (1=web, 2=broadcast)
    Index 3:  V2SourceCommonName - Source domain name
    Index 4:  V2DocumentIdentifier - Full article URL
    Index 5:  V2Counts - Event counts with geographic context
    Index 6:  V2EnhancedCounts - Extended count data
    Index 7:  V2Themes - Semicolon-separated theme codes
    Index 8:  V2EnhancedThemes - Theme,CharOffset pairs
    Index 9:  V2Locations - Simplified location data
    Index 10: V2EnhancedLocations - Full geographic data
    Index 11: V2Persons - Semicolon-separated person names
    Index 12: V2EnhancedPersons - Person,CharOffset pairs
    Index 13: V2Organizations - Semicolon-separated org names
    Index 14: V2EnhancedOrganizations - Org,CharOffset pairs
    Index 15: V2Tone - 7 comma-separated sentiment metrics
    Index 16: V2EnhancedDates - Date mentions
    Index 17: V2GCAM - Global Content Analysis Measures
    Index 18: V2SharingImage - Article thumbnail URL
    Index 19-26: Additional metadata fields

API Quotas and Limits:
    - GDELT has no rate limits for file downloads
    - Files update every 15 minutes (96 files/day)
    - Typical file size: 5-15 MB compressed, 50-150 MB uncompressed
    - Articles per file: 10,000-30,000
    - Recommended polling: Every 15 minutes via lastupdate.txt

Usage:
    >>> from app.services.gdelt_parser import GDELTParser
    >>> parser = GDELTParser()
    >>> for record in parser.parse_file('/path/to/gkg.csv'):
    ...     print(record.themes, record.locations)

Author: Observatory Global Team
Version: 1.0.0
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterator, List, Optional, Dict, Tuple, Any
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes for Parsed GKG Records
# =============================================================================

@dataclass
class GKGLocation:
    """
    Parsed location from V2Locations or V2EnhancedLocations field.

    V2Locations Format (semicolon-separated blocks):
        Type#FullName#CountryCode#ADM1Code#Lat#Long#FeatureID

    V2EnhancedLocations Format:
        Type#FullName#CountryCode#ADM1Code#ADM2Code#Lat#Long#FeatureID#CharOffset

    Example:
        3#Los Angeles, California, United States#US#USCA#CA037#34.0522#-118.244#1662328#1325

    Location Types:
        1 = Country
        2 = US State
        3 = US City
        4 = World City
        5 = World State/Province

    Attributes:
        location_type: Geographic granularity (1-5)
        full_name: Full location name (e.g., "Los Angeles, California, United States")
        country_code: ISO 3166-1 alpha-2 code (e.g., "US")
        adm1_code: Administrative division 1 (e.g., "USCA" for California)
        adm2_code: Administrative division 2 (e.g., "CA037" for LA County)
        latitude: Decimal latitude
        longitude: Decimal longitude
        feature_id: GeoNames ID for lookup
        char_offset: Character position in source article (enhanced only)
    """
    location_type: int
    full_name: str
    country_code: str
    adm1_code: str = ""
    adm2_code: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    feature_id: str = ""
    char_offset: int = 0


@dataclass
class GKGTone:
    """
    Parsed sentiment data from V2Tone field.

    V2Tone Format (7 comma-separated values):
        Tone,PositiveScore,NegativeScore,Polarity,ActivityDensity,SelfGroupRef,WordCount

    Example:
        -3.5,2.1,5.6,7.7,21.3,2.5,523

    Value Ranges:
        - tone: -100 (very negative) to +100 (very positive), typical: -10 to +10
        - positive_pct: 0-100, typical: 1-10
        - negative_pct: 0-100, typical: 1-15
        - polarity: 0-100, distance from neutral
        - activity_density: Action word percentage
        - self_group_ref: First-person plural references (we, us, our)
        - word_count: Total words in article

    Interpretation:
        - Most articles: tone between -10 and +10
        - Crisis/conflict: tone -30 to -50
        - Diplomatic cooperation: tone +10 to +30
        - Extreme outliers: -80 (atrocities) to +80 (celebration)

    Attributes:
        tone: Overall sentiment score (-100 to +100)
        positive_pct: Percentage of positive words
        negative_pct: Percentage of negative words
        polarity: Emotional intensity (distance from neutral)
        activity_density: Action word density
        self_group_ref: First-person plural reference count
        word_count: Total article word count
    """
    tone: float = 0.0
    positive_pct: float = 0.0
    negative_pct: float = 0.0
    polarity: float = 0.0
    activity_density: float = 0.0
    self_group_ref: float = 0.0
    word_count: int = 0


@dataclass
class GKGCount:
    """
    Parsed count entry from V2Counts field.

    V2Counts Format (semicolon-separated blocks):
        CountType#Number#ObjectType#LocationType#LocationName#CountryCode#ADM1#Lat#Long#FeatureID

    Example:
        KILL#12##3#Pacific Palisades, California, United States#US#USCA#34.0481#-118.526#1661169

    Count Types:
        - KILL: Deaths
        - WOUND: Injuries
        - ARREST: Arrests
        - AFFECT: People affected
        - Theme codes (e.g., CRISISLEX_T03_DEAD)

    Attributes:
        count_type: Type of count (KILL, WOUND, ARREST, etc.)
        number: Numeric count value
        object_type: What was counted (e.g., "officers", "civilians")
        location: Associated GKGLocation if geographic context provided
    """
    count_type: str
    number: int
    object_type: str = ""
    location: Optional[GKGLocation] = None


@dataclass
class GKGRecord:
    """
    Complete parsed GKG record from a single row.

    Contains all critical fields needed for Observatory Global signal processing.
    Non-critical fields can be added as needed.

    Attributes:
        record_id: Unique identifier (GKGRECORDID)
        timestamp: Publication datetime (V2DATE)
        source_collection: Source type ID (1=web, 2=broadcast)
        source_name: Domain name (V2SourceCommonName)
        source_url: Full article URL (V2DocumentIdentifier)
        themes: List of theme codes (V2Themes)
        enhanced_themes: Theme codes with character offsets
        locations: List of parsed locations (V2EnhancedLocations)
        persons: List of person names (V2Persons)
        organizations: List of organization names (V2Organizations)
        tone: Parsed sentiment data (V2Tone)
        counts: List of parsed counts (V2Counts)
        gcam: Raw GCAM data string (for future advanced analysis)
        sharing_image: Article thumbnail URL
        raw_line: Original CSV line for debugging
        line_number: Line number in source file
    """
    record_id: str
    timestamp: datetime
    source_collection: int = 1
    source_name: str = ""
    source_url: str = ""
    themes: List[str] = field(default_factory=list)
    enhanced_themes: List[Tuple[str, int]] = field(default_factory=list)
    locations: List[GKGLocation] = field(default_factory=list)
    persons: List[str] = field(default_factory=list)
    organizations: List[str] = field(default_factory=list)
    tone: GKGTone = field(default_factory=GKGTone)
    counts: List[GKGCount] = field(default_factory=list)
    gcam: str = ""
    sharing_image: str = ""
    raw_line: str = ""
    line_number: int = 0


# =============================================================================
# Parser Exception Classes
# =============================================================================

class GKGParseError(Exception):
    """Base exception for GKG parsing errors."""
    pass


class GKGColumnCountError(GKGParseError):
    """Raised when row has incorrect number of columns."""
    pass


class GKGDateParseError(GKGParseError):
    """Raised when V2DATE cannot be parsed."""
    pass


# =============================================================================
# Main Parser Class
# =============================================================================

class GDELTParser:
    """
    Streaming parser for GDELT GKG v2.1 files.

    Parses tab-delimited CSV files and yields GKGRecord objects.
    Handles malformed rows gracefully with skip-and-log strategy.

    Example:
        >>> parser = GDELTParser()
        >>> records = list(parser.parse_file('/path/to/gkg.csv'))
        >>> print(f"Parsed {len(records)} records")
    """

    # Column indices for GKG v2.1 schema
    COL_RECORD_ID = 0
    COL_DATE = 1
    COL_SOURCE_COLLECTION = 2
    COL_SOURCE_NAME = 3
    COL_SOURCE_URL = 4
    COL_COUNTS = 5
    COL_ENHANCED_COUNTS = 6
    COL_THEMES = 7
    COL_ENHANCED_THEMES = 8
    COL_LOCATIONS = 9
    COL_ENHANCED_LOCATIONS = 10
    COL_PERSONS = 11
    COL_ENHANCED_PERSONS = 12
    COL_ORGANIZATIONS = 13
    COL_ENHANCED_ORGANIZATIONS = 14
    COL_TONE = 15
    COL_ENHANCED_DATES = 16
    COL_GCAM = 17
    COL_SHARING_IMAGE = 18

    EXPECTED_COLUMNS = 27

    def __init__(self):
        """Initialize the parser."""
        self.parse_errors = 0
        self.parse_successes = 0

    def parse_file(self, filepath: str) -> Iterator[GKGRecord]:
        """
        Parse a GKG CSV file and yield records.

        Streams through the file line by line to minimize memory usage.
        Malformed rows are skipped and logged.

        Args:
            filepath: Path to the GKG CSV file

        Yields:
            GKGRecord objects for each valid row

        Raises:
            FileNotFoundError: If file does not exist
            PermissionError: If file cannot be read
        """
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"GKG file not found: {filepath}")

        self.parse_errors = 0
        self.parse_successes = 0

        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    record = self._parse_row(line, line_num)
                    if record:
                        self.parse_successes += 1
                        yield record
                except GKGParseError as e:
                    self.parse_errors += 1
                    logger.warning({
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "level": "WARNING",
                        "source": "gdelt_parser",
                        "file": path.name,
                        "line_number": line_num,
                        "error_type": type(e).__name__,
                        "message": str(e),
                        "action": "skipped"
                    })
                except Exception as e:
                    self.parse_errors += 1
                    logger.error({
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                        "level": "ERROR",
                        "source": "gdelt_parser",
                        "file": path.name,
                        "line_number": line_num,
                        "error_type": type(e).__name__,
                        "message": str(e),
                        "action": "skipped"
                    })

        # Log summary
        total = self.parse_successes + self.parse_errors
        error_rate = (self.parse_errors / total * 100) if total > 0 else 0
        logger.info({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": "INFO",
            "source": "gdelt_parser",
            "file": path.name,
            "total_rows": total,
            "successes": self.parse_successes,
            "errors": self.parse_errors,
            "error_rate_pct": round(error_rate, 2)
        })

        if error_rate > 10:
            logger.error({
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": "ERROR",
                "source": "gdelt_parser",
                "file": path.name,
                "message": f"High error rate: {error_rate:.1f}%",
                "action": "alert"
            })

    def _parse_row(self, line: str, line_num: int) -> Optional[GKGRecord]:
        """
        Parse a single CSV row into a GKGRecord.

        Args:
            line: Raw CSV line
            line_num: Line number for error reporting

        Returns:
            GKGRecord if valid, None if empty line

        Raises:
            GKGColumnCountError: If column count is wrong
            GKGDateParseError: If date cannot be parsed
        """
        line = line.strip()
        if not line:
            return None

        columns = line.split('\t')

        if len(columns) != self.EXPECTED_COLUMNS:
            raise GKGColumnCountError(
                f"Expected {self.EXPECTED_COLUMNS} columns, got {len(columns)}"
            )

        # Parse required fields
        record_id = columns[self.COL_RECORD_ID]
        timestamp = self.parse_v2_date(columns[self.COL_DATE])

        # Parse optional fields with defaults
        source_collection = self._parse_int_safe(columns[self.COL_SOURCE_COLLECTION], 1)

        # Build record
        record = GKGRecord(
            record_id=record_id,
            timestamp=timestamp,
            source_collection=source_collection,
            source_name=columns[self.COL_SOURCE_NAME],
            source_url=columns[self.COL_SOURCE_URL],
            themes=self.parse_v2_themes(columns[self.COL_THEMES]),
            enhanced_themes=self._parse_enhanced_themes(columns[self.COL_ENHANCED_THEMES]),
            locations=self.parse_v2_locations(columns[self.COL_ENHANCED_LOCATIONS]),
            persons=self._parse_list(columns[self.COL_PERSONS]),
            organizations=self._parse_list(columns[self.COL_ORGANIZATIONS]),
            tone=self.parse_v2_tone(columns[self.COL_TONE]),
            counts=self.parse_v2_counts(columns[self.COL_COUNTS]),
            gcam=columns[self.COL_GCAM],
            sharing_image=columns[self.COL_SHARING_IMAGE] if len(columns) > self.COL_SHARING_IMAGE else "",
            raw_line=line,
            line_number=line_num
        )

        return record

    # =========================================================================
    # Field Parsers
    # =========================================================================

    def parse_v2_date(self, date_str: str) -> datetime:
        """
        Parse V2DATE timestamp field.

        Format: YYYYMMDDHHMMSS (14 digits)
        Example: 20251119031500 -> 2025-11-19 03:15:00 UTC

        Args:
            date_str: Raw date string from column

        Returns:
            datetime object in UTC

        Raises:
            GKGDateParseError: If format is invalid
        """
        # TODO: Implement actual parsing
        # Placeholder implementation
        date_str = date_str.strip()

        if not date_str or len(date_str) != 14:
            raise GKGDateParseError(f"Invalid date format: '{date_str}' (expected 14 digits)")

        try:
            dt = datetime.strptime(date_str, "%Y%m%d%H%M%S")
            return dt.replace(tzinfo=timezone.utc)
        except ValueError as e:
            raise GKGDateParseError(f"Cannot parse date '{date_str}': {e}")

    def parse_v2_themes(self, themes_str: str) -> List[str]:
        """
        Parse V2Themes field into list of theme codes.

        Format: Semicolon-separated theme codes
        Example: TAX_FNCACT;ECON_INFLATION;PROTEST;LEADER

        Common Theme Prefixes:
            - TAX_: GDELT Thematic Taxonomy
            - WB_: World Bank SDGs
            - UNGP_: UN Global Pulse
            - CRISISLEX_: Crisis events
            - ENV_: Environment
            - ECON_: Economics

        Args:
            themes_str: Raw themes string from column

        Returns:
            List of theme code strings, empty list if no themes
        """
        # TODO: Implement actual parsing
        # Placeholder implementation
        if not themes_str or not themes_str.strip():
            return []

        themes = [t.strip() for t in themes_str.split(';') if t.strip()]
        return themes

    def parse_v2_tone(self, tone_str: str) -> GKGTone:
        """
        Parse V2Tone field into GKGTone object.

        Format: 7 comma-separated numeric values
        Example: -3.5,2.1,5.6,7.7,21.3,2.5,523

        Values:
            [0] tone: Overall sentiment (-100 to +100)
            [1] positive_pct: Positive word percentage
            [2] negative_pct: Negative word percentage
            [3] polarity: Emotional intensity
            [4] activity_density: Action word density
            [5] self_group_ref: First-person plural refs
            [6] word_count: Total words

        Args:
            tone_str: Raw tone string from column

        Returns:
            GKGTone object with parsed values
        """
        # TODO: Implement actual parsing
        # Placeholder implementation
        if not tone_str or not tone_str.strip():
            return GKGTone()

        values = tone_str.split(',')
        if len(values) < 7:
            logger.debug(f"Incomplete tone data: {len(values)} values")
            return GKGTone()

        try:
            return GKGTone(
                tone=float(values[0]),
                positive_pct=float(values[1]),
                negative_pct=float(values[2]),
                polarity=float(values[3]),
                activity_density=float(values[4]),
                self_group_ref=float(values[5]),
                word_count=int(float(values[6]))
            )
        except (ValueError, IndexError) as e:
            logger.debug(f"Error parsing tone '{tone_str}': {e}")
            return GKGTone()

    def parse_v2_locations(self, locations_str: str) -> List[GKGLocation]:
        """
        Parse V2EnhancedLocations field into list of GKGLocation objects.

        Format: Semicolon-separated location blocks
        Block format: Type#FullName#CountryCode#ADM1#ADM2#Lat#Long#FeatureID#CharOffset

        Example:
            3#Los Angeles, California, United States#US#USCA#CA037#34.0522#-118.244#1662328#1325

        Location Types:
            1 = Country (e.g., "United States")
            2 = US State (e.g., "California, United States")
            3 = US City (e.g., "Los Angeles, California, United States")
            4 = World City (e.g., "London, England, United Kingdom")
            5 = World State/Province (e.g., "Ontario, Canada")

        Args:
            locations_str: Raw locations string from column

        Returns:
            List of GKGLocation objects, empty list if no locations
        """
        # TODO: Implement actual parsing
        # Placeholder implementation
        if not locations_str or not locations_str.strip():
            return []

        locations = []
        blocks = locations_str.split(';')

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            parts = block.split('#')
            if len(parts) < 7:
                continue

            try:
                location = GKGLocation(
                    location_type=int(parts[0]) if parts[0] else 0,
                    full_name=parts[1],
                    country_code=parts[2],
                    adm1_code=parts[3] if len(parts) > 3 else "",
                    adm2_code=parts[4] if len(parts) > 4 else "",
                    latitude=float(parts[5]) if len(parts) > 5 and parts[5] else 0.0,
                    longitude=float(parts[6]) if len(parts) > 6 and parts[6] else 0.0,
                    feature_id=parts[7] if len(parts) > 7 else "",
                    char_offset=int(parts[8]) if len(parts) > 8 and parts[8] else 0
                )
                locations.append(location)
            except (ValueError, IndexError) as e:
                logger.debug(f"Error parsing location block '{block}': {e}")
                continue

        return locations

    def parse_v2_counts(self, counts_str: str) -> List[GKGCount]:
        """
        Parse V2Counts field into list of GKGCount objects.

        Format: Semicolon-separated count blocks
        Block format: CountType#Number#ObjectType#LocType#LocName#Country#ADM1#Lat#Long#FeatureID

        Example:
            KILL#12##3#Pacific Palisades, California, United States#US#USCA#34.0481#-118.526#1661169

        Common Count Types:
            - KILL: Deaths
            - WOUND: Injuries
            - ARREST: Arrests
            - AFFECT: People affected
            - CRISISLEX_T03_DEAD: Crisis deaths
            - CRISISLEX_T02_INJURED: Crisis injuries

        Args:
            counts_str: Raw counts string from column

        Returns:
            List of GKGCount objects, empty list if no counts
        """
        # TODO: Implement actual parsing
        # Placeholder implementation
        if not counts_str or not counts_str.strip():
            return []

        counts = []
        blocks = counts_str.split(';')

        for block in blocks:
            block = block.strip()
            if not block:
                continue

            parts = block.split('#')
            if len(parts) < 2:
                continue

            try:
                count_type = parts[0]
                number = int(parts[1]) if parts[1] else 0
                object_type = parts[2] if len(parts) > 2 else ""

                # Parse embedded location if present
                location = None
                if len(parts) >= 10:
                    try:
                        location = GKGLocation(
                            location_type=int(parts[3]) if parts[3] else 0,
                            full_name=parts[4] if len(parts) > 4 else "",
                            country_code=parts[5] if len(parts) > 5 else "",
                            adm1_code=parts[6] if len(parts) > 6 else "",
                            latitude=float(parts[7]) if len(parts) > 7 and parts[7] else 0.0,
                            longitude=float(parts[8]) if len(parts) > 8 and parts[8] else 0.0,
                            feature_id=parts[9] if len(parts) > 9 else ""
                        )
                    except (ValueError, IndexError):
                        location = None

                count = GKGCount(
                    count_type=count_type,
                    number=number,
                    object_type=object_type,
                    location=location
                )
                counts.append(count)
            except (ValueError, IndexError) as e:
                logger.debug(f"Error parsing count block '{block}': {e}")
                continue

        return counts

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _parse_list(self, field_str: str) -> List[str]:
        """
        Parse semicolon-separated list field.

        Args:
            field_str: Raw field string

        Returns:
            List of strings, empty list if empty
        """
        if not field_str or not field_str.strip():
            return []
        return [item.strip() for item in field_str.split(';') if item.strip()]

    def _parse_enhanced_themes(self, themes_str: str) -> List[Tuple[str, int]]:
        """
        Parse V2EnhancedThemes into list of (theme, char_offset) tuples.

        Format: Theme,CharOffset pairs separated by semicolons
        Example: TAX_FNCACT,123;ECON_INFLATION,456

        Args:
            themes_str: Raw enhanced themes string

        Returns:
            List of (theme_code, char_offset) tuples
        """
        if not themes_str or not themes_str.strip():
            return []

        result = []
        for pair in themes_str.split(';'):
            pair = pair.strip()
            if ',' in pair:
                parts = pair.rsplit(',', 1)
                theme = parts[0]
                try:
                    offset = int(parts[1])
                    result.append((theme, offset))
                except ValueError:
                    result.append((theme, 0))
            elif pair:
                result.append((pair, 0))

        return result

    def _parse_int_safe(self, value: str, default: int = 0) -> int:
        """
        Safely parse integer with default fallback.

        Args:
            value: String to parse
            default: Default value if parsing fails

        Returns:
            Parsed integer or default
        """
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def _parse_float_safe(self, value: str, default: float = 0.0) -> float:
        """
        Safely parse float with default fallback.

        Args:
            value: String to parse
            default: Default value if parsing fails

        Returns:
            Parsed float or default
        """
        try:
            return float(value)
        except (ValueError, TypeError):
            return default


# =============================================================================
# Utility Functions
# =============================================================================

def filter_by_country(records: Iterator[GKGRecord], country_code: str) -> Iterator[GKGRecord]:
    """
    Filter GKG records by country code.

    Args:
        records: Iterator of GKGRecord objects
        country_code: ISO 3166-1 alpha-2 code (e.g., "US", "BR")

    Yields:
        Records with at least one location matching country_code
    """
    country_code = country_code.upper()
    for record in records:
        if any(loc.country_code == country_code for loc in record.locations):
            yield record


def get_primary_location(record: GKGRecord, country_code: Optional[str] = None) -> Optional[GKGLocation]:
    """
    Get the primary location from a record.

    Priority:
        1. First location matching country_code (if specified)
        2. Most specific location (highest location_type)
        3. First location

    Args:
        record: GKGRecord to extract location from
        country_code: Preferred country code (optional)

    Returns:
        GKGLocation or None if no locations
    """
    if not record.locations:
        return None

    if country_code:
        country_code = country_code.upper()
        for loc in record.locations:
            if loc.country_code == country_code:
                return loc

    # Return most specific location
    return max(record.locations, key=lambda x: x.location_type)


def get_top_themes(records: List[GKGRecord], limit: int = 50) -> List[Tuple[str, int]]:
    """
    Get most common themes across records.

    Args:
        records: List of GKGRecord objects
        limit: Maximum themes to return

    Returns:
        List of (theme, count) tuples sorted by count descending
    """
    from collections import Counter
    theme_counts: Counter = Counter()

    for record in records:
        theme_counts.update(record.themes)

    return theme_counts.most_common(limit)


# =============================================================================
# Module Entry Point
# =============================================================================

if __name__ == "__main__":
    # Quick test with a sample file
    import sys

    if len(sys.argv) < 2:
        print("Usage: python gdelt_parser.py <gkg_file.csv>")
        sys.exit(1)

    filepath = sys.argv[1]
    parser = GDELTParser()

    records = []
    for record in parser.parse_file(filepath):
        records.append(record)
        if len(records) >= 5:  # Just show first 5
            break

    print(f"\nParsed {len(records)} sample records:")
    for r in records:
        print(f"\n  ID: {r.record_id}")
        print(f"  Date: {r.timestamp}")
        print(f"  Source: {r.source_name}")
        print(f"  Themes: {r.themes[:5]}...")
        print(f"  Locations: {[l.country_code for l in r.locations]}")
        print(f"  Tone: {r.tone.tone:.2f}")
