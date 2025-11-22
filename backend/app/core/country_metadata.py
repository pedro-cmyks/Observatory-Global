"""
Centralized Country Metadata

This module provides a single source of truth for country information
used throughout the application. Previously, this data was duplicated
in multiple locations (flow_detector.py, hexmap_generator.py).

Each country is represented by:
- ISO 3166-1 alpha-2 code (e.g., "US", "CO")
- Full country name
- Geographic centroid (latitude, longitude)

The centroids are used for:
- Map visualization positioning
- H3 hexagon generation
- Flow line drawing
- Country-level aggregations
"""

from typing import Dict, Tuple


# Country metadata: ISO code -> (name, latitude, longitude)
COUNTRY_METADATA: Dict[str, Tuple[str, float, float]] = {
    # Americas
    'US': ('United States', 37.0902, -95.7129),
    'CO': ('Colombia', 4.5709, -74.2973),
    'BR': ('Brazil', -14.2350, -51.9253),
    'MX': ('Mexico', 23.6345, -102.5528),
    'AR': ('Argentina', -38.4161, -63.6167),
    'CA': ('Canada', 56.1304, -106.3468),

    # Europe
    'GB': ('United Kingdom', 55.3781, -3.4360),
    'FR': ('France', 46.2276, 2.2137),
    'DE': ('Germany', 51.1657, 10.4515),
    'ES': ('Spain', 40.4637, -3.7492),
    'IT': ('Italy', 41.8719, 12.5674),
    'RU': ('Russia', 61.5240, 105.3188),
    'NL': ('Netherlands', 52.1326, 5.2913),
    'BE': ('Belgium', 50.5039, 4.4699),
    'SE': ('Sweden', 60.1282, 18.6435),
    'NO': ('Norway', 60.4720, 8.4689),
    'PL': ('Poland', 51.9194, 19.1451),
    'CH': ('Switzerland', 46.8182, 8.2275),
    'AT': ('Austria', 47.5162, 14.5501),
    'UA': ('Ukraine', 48.3794, 31.1656),

    # Asia-Pacific
    'CN': ('China', 35.8617, 104.1954),
    'IN': ('India', 20.5937, 78.9629),
    'JP': ('Japan', 36.2048, 138.2529),
    'AU': ('Australia', -25.2744, 133.7751),
    'KR': ('South Korea', 35.9078, 127.7669),

    # Middle East
    'IL': ('Israel', 31.0461, 34.8516),
    'SA': ('Saudi Arabia', 23.8859, 45.0792),
    'TR': ('Turkey', 38.9637, 35.2433),

    # Africa
    'ZA': ('South Africa', -30.5595, 22.9375),
    'EG': ('Egypt', 26.8206, 30.8025),
    'NG': ('Nigeria', 9.0820, 8.6753),
}


def get_country_name(country_code: str) -> str:
    """
    Get full country name from ISO code.

    Args:
        country_code: ISO 3166-1 alpha-2 code (e.g., "US")

    Returns:
        Full country name (e.g., "United States")

    Raises:
        KeyError: If country code is not found
    """
    return COUNTRY_METADATA[country_code][0]


def get_country_coordinates(country_code: str) -> Tuple[float, float]:
    """
    Get country centroid coordinates.

    Args:
        country_code: ISO 3166-1 alpha-2 code (e.g., "US")

    Returns:
        Tuple of (latitude, longitude)

    Raises:
        KeyError: If country code is not found
    """
    return COUNTRY_METADATA[country_code][1], COUNTRY_METADATA[country_code][2]


def get_supported_countries() -> list[str]:
    """
    Get list of all supported country codes.

    Returns:
        List of ISO 3166-1 alpha-2 country codes
    """
    return list(COUNTRY_METADATA.keys())


def is_country_supported(country_code: str) -> bool:
    """
    Check if a country code is supported.

    Args:
        country_code: ISO 3166-1 alpha-2 code

    Returns:
        True if country is supported, False otherwise
    """
    return country_code in COUNTRY_METADATA
