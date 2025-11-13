"""
PROOF OF CONCEPT: Hexagonal Heatmap Backend

This demonstrates the backend implementation for generating hexagonal
heatmaps from country-level trending data.

Dependencies needed:
pip install h3 shapely geopandas fastapi
"""

from typing import List, Dict, Optional, Set
from datetime import datetime
from dataclasses import dataclass
from collections import defaultdict
import json
import math

import h3
from shapely.geometry import shape, Polygon
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field


# ============================================================================
# MODELS
# ============================================================================

class Hexagon(BaseModel):
    """Single hexagon with intensity value."""
    h3_index: str = Field(..., description="H3 hexagon identifier")
    intensity: float = Field(..., ge=0.0, le=1.0, description="Heat intensity (0-1)")
    country: str = Field(..., description="Country code(s) covering this hex")
    top_topic: Optional[str] = Field(None, description="Most trending topic in this hex")


class HexmapMetadata(BaseModel):
    """Metadata about the hexmap generation."""
    total_hexagons: int
    filtered_hexagons: int
    max_intensity: float
    countries_included: List[str]
    avg_intensity: float


class HexmapResponse(BaseModel):
    """Complete hexmap API response."""
    resolution: int = Field(..., ge=0, le=15, description="H3 resolution level")
    time_window: str
    generated_at: datetime
    hexagons: List[Hexagon]
    metadata: HexmapMetadata


@dataclass
class CountryHotspot:
    """Country-level intensity data (from existing flow detector)."""
    country_code: str
    intensity: float
    top_topics: List[str]


# ============================================================================
# HEX GENERATOR SERVICE
# ============================================================================

class HexGenerator:
    """
    Converts country-level intensity data to hexagonal grid.

    Methods:
    - country_to_hexes: Polyfill country with hexagons
    - aggregate_hexes: Combine overlapping hexagons
    - smooth_hexes: Apply k-ring smoothing for blob effect
    """

    def __init__(self, country_geojson_path: str = "data/countries.geojson"):
        """
        Initialize with country geometries.

        Download countries.geojson from:
        https://github.com/datasets/geo-countries/blob/master/data/countries.geojson
        """
        self.country_geometries = self._load_country_geometries(country_geojson_path)

    def country_to_hexes(
        self,
        country_code: str,
        intensity: float,
        resolution: int,
        top_topic: Optional[str] = None
    ) -> List[Hexagon]:
        """
        Convert a country's intensity to hexagons covering that country.

        Args:
            country_code: ISO 2-letter country code (e.g., 'US', 'BR')
            intensity: Heat intensity (0.0 - 1.0)
            resolution: H3 resolution level (0-15)
            top_topic: Most trending topic (optional)

        Returns:
            List of Hexagon objects covering the country
        """
        # Get country polygon
        geom = self.country_geometries.get(country_code)
        if not geom:
            print(f"Warning: No geometry found for country {country_code}")
            return []

        # Convert Shapely polygon to GeoJSON format for h3.polyfill
        geojson = self._shapely_to_geojson(geom)

        try:
            # Get all H3 cells covering the polygon
            hex_ids = h3.polyfill_geojson(geojson, resolution)

            # Create Hexagon objects
            hexagons = [
                Hexagon(
                    h3_index=hex_id,
                    intensity=intensity,
                    country=country_code,
                    top_topic=top_topic
                )
                for hex_id in hex_ids
            ]

            return hexagons

        except Exception as e:
            print(f"Error polyfilling {country_code}: {e}")
            return []

    def aggregate_hexes(self, hexagons: List[Hexagon]) -> List[Hexagon]:
        """
        Aggregate overlapping hexagons (when multiple countries share a hex).

        Strategy:
        - Sum intensities (capped at 1.0)
        - Combine country codes
        - Take the most intense topic

        Args:
            hexagons: List of potentially overlapping hexagons

        Returns:
            List of unique hexagons with aggregated intensities
        """
        aggregated: Dict[str, Dict] = defaultdict(lambda: {
            "intensity": 0.0,
            "countries": set(),
            "topics": []
        })

        for hex_obj in hexagons:
            h3_index = hex_obj.h3_index

            # Sum intensities
            aggregated[h3_index]["intensity"] += hex_obj.intensity

            # Collect countries
            aggregated[h3_index]["countries"].add(hex_obj.country)

            # Collect topics
            if hex_obj.top_topic:
                aggregated[h3_index]["topics"].append((hex_obj.top_topic, hex_obj.intensity))

        # Convert back to Hexagon objects
        result = []
        for h3_index, data in aggregated.items():
            # Cap intensity at 1.0
            final_intensity = min(data["intensity"], 1.0)

            # Join country codes
            country_str = ",".join(sorted(data["countries"]))

            # Select top topic (by intensity)
            top_topic = None
            if data["topics"]:
                data["topics"].sort(key=lambda x: x[1], reverse=True)
                top_topic = data["topics"][0][0]

            result.append(
                Hexagon(
                    h3_index=h3_index,
                    intensity=final_intensity,
                    country=country_str,
                    top_topic=top_topic
                )
            )

        return result

    def smooth_hexes(
        self,
        hexagons: List[Hexagon],
        k: int = 2,
        decay_factor: float = 0.5
    ) -> List[Hexagon]:
        """
        Apply k-ring smoothing to create blob effect.

        Spreads each hexagon's intensity to its k-ring neighbors
        with distance-based decay.

        Args:
            hexagons: Input hexagons
            k: K-ring distance (1 = immediate neighbors, 2 = neighbors of neighbors)
            decay_factor: Intensity decay per distance step (0-1)

        Returns:
            Smoothed hexagons
        """
        # Convert to dict for fast lookup
        hex_dict = {hex.h3_index: hex.intensity for hex in hexagons}
        smoothed: Dict[str, float] = defaultdict(float)

        # For each hexagon, distribute intensity to k-ring
        for hex_obj in hexagons:
            try:
                # Get k-ring neighbors (includes self)
                neighbors = h3.k_ring(hex_obj.h3_index, k)

                for neighbor in neighbors:
                    # Calculate distance
                    distance = h3.h3_distance(hex_obj.h3_index, neighbor)

                    # Apply decay based on distance
                    weight = decay_factor ** distance

                    # Add weighted intensity
                    smoothed[neighbor] += hex_obj.intensity * weight

            except Exception as e:
                print(f"Error smoothing hex {hex_obj.h3_index}: {e}")
                continue

        # Normalize to [0, 1]
        max_intensity = max(smoothed.values()) if smoothed else 1.0

        # Convert back to Hexagon objects
        # Keep original country/topic metadata where available
        original_data = {hex.h3_index: hex for hex in hexagons}

        result = []
        for h3_index, intensity in smoothed.items():
            normalized_intensity = min(intensity / max_intensity, 1.0)

            # Use original metadata if available, otherwise generic
            if h3_index in original_data:
                original = original_data[h3_index]
                country = original.country
                topic = original.top_topic
            else:
                country = "INTERPOLATED"
                topic = None

            result.append(
                Hexagon(
                    h3_index=h3_index,
                    intensity=normalized_intensity,
                    country=country,
                    top_topic=topic
                )
            )

        return result

    # ========================================================================
    # PRIVATE METHODS
    # ========================================================================

    def _load_country_geometries(self, geojson_path: str) -> Dict[str, Polygon]:
        """Load country polygons from GeoJSON file."""
        geometries = {}

        try:
            with open(geojson_path, "r", encoding="utf-8") as f:
                geojson_data = json.load(f)

            for feature in geojson_data["features"]:
                # Use ISO_A2 code (e.g., 'US', 'BR')
                country_code = feature["properties"].get("ISO_A2")
                if not country_code or country_code == "-99":
                    continue

                # Convert to Shapely geometry
                geom = shape(feature["geometry"])
                geometries[country_code] = geom

            print(f"Loaded {len(geometries)} country geometries")

        except FileNotFoundError:
            print(f"Warning: Country GeoJSON not found at {geojson_path}")
            print("Download from: https://github.com/datasets/geo-countries")

        except Exception as e:
            print(f"Error loading country geometries: {e}")

        return geometries

    def _shapely_to_geojson(self, geom: Polygon) -> dict:
        """Convert Shapely polygon to GeoJSON dict."""
        return {
            "type": "Polygon",
            "coordinates": [list(geom.exterior.coords)]
        }


# ============================================================================
# API ENDPOINT
# ============================================================================

router = APIRouter()

# Singleton instance (initialize on startup)
hex_generator: Optional[HexGenerator] = None


def get_hex_generator() -> HexGenerator:
    """Get or create HexGenerator instance."""
    global hex_generator
    if hex_generator is None:
        hex_generator = HexGenerator()
    return hex_generator


@router.get("/hexmap", response_model=HexmapResponse)
async def get_hexmap(
    resolution: int = Query(4, ge=0, le=15, description="H3 resolution level"),
    time_window: str = Query("24h", regex="^(1h|6h|12h|24h)$"),
    countries: Optional[str] = Query(None, description="Comma-separated country codes"),
    threshold: float = Query(0.1, ge=0.0, le=1.0, description="Minimum intensity to include"),
    smooth: bool = Query(False, description="Apply k-ring smoothing for blob effect")
):
    """
    Generate hexagonal heatmap of information flow intensity.

    **Example Request:**
    ```
    GET /v1/hexmap?resolution=4&time_window=24h&countries=US,BR,CO&threshold=0.2&smooth=true
    ```

    **Response:**
    - `resolution`: H3 resolution level used
    - `hexagons`: Array of hexagons with intensity values
    - `metadata`: Statistics about the generated heatmap
    """
    gen = get_hex_generator()

    # ========================================================================
    # STEP 1: Get country-level intensities
    # ========================================================================
    # NOTE: In production, this would call FlowDetector.get_hotspots()
    # For this POC, we use mock data

    hotspots = _get_mock_hotspots(time_window, countries)

    if not hotspots:
        raise HTTPException(status_code=404, detail="No hotspot data available")

    # ========================================================================
    # STEP 2: Convert countries to hexagons
    # ========================================================================

    all_hexagons = []
    for hotspot in hotspots:
        country_hexes = gen.country_to_hexes(
            country_code=hotspot.country_code,
            intensity=hotspot.intensity,
            resolution=resolution,
            top_topic=hotspot.top_topics[0] if hotspot.top_topics else None
        )
        all_hexagons.extend(country_hexes)

    # ========================================================================
    # STEP 3: Aggregate overlapping hexagons
    # ========================================================================

    aggregated_hexes = gen.aggregate_hexes(all_hexagons)

    # ========================================================================
    # STEP 4: Apply smoothing (optional)
    # ========================================================================

    if smooth:
        aggregated_hexes = gen.smooth_hexes(aggregated_hexes, k=2, decay_factor=0.5)

    # ========================================================================
    # STEP 5: Filter by threshold
    # ========================================================================

    filtered_hexes = [h for h in aggregated_hexes if h.intensity >= threshold]

    # ========================================================================
    # STEP 6: Calculate metadata
    # ========================================================================

    countries_included = list(set(hotspot.country_code for hotspot in hotspots))

    if aggregated_hexes:
        max_intensity = max(h.intensity for h in aggregated_hexes)
        avg_intensity = sum(h.intensity for h in aggregated_hexes) / len(aggregated_hexes)
    else:
        max_intensity = 0.0
        avg_intensity = 0.0

    metadata = HexmapMetadata(
        total_hexagons=len(aggregated_hexes),
        filtered_hexagons=len(filtered_hexes),
        max_intensity=max_intensity,
        countries_included=countries_included,
        avg_intensity=avg_intensity
    )

    # ========================================================================
    # STEP 7: Return response
    # ========================================================================

    return HexmapResponse(
        resolution=resolution,
        time_window=time_window,
        generated_at=datetime.utcnow(),
        hexagons=filtered_hexes,
        metadata=metadata
    )


# ============================================================================
# MOCK DATA (for POC testing)
# ============================================================================

def _get_mock_hotspots(time_window: str, countries: Optional[str]) -> List[CountryHotspot]:
    """
    Generate mock hotspot data for testing.

    In production, this would fetch from database/FlowDetector.
    """
    mock_data = [
        CountryHotspot("US", 0.92, ["election fraud claims", "voting irregularities"]),
        CountryHotspot("BR", 0.78, ["Amazon deforestation", "climate protests"]),
        CountryHotspot("CO", 0.65, ["peace talks", "government negotiations"]),
        CountryHotspot("GB", 0.54, ["Brexit impact", "trade deals"]),
        CountryHotspot("FR", 0.49, ["pension reform", "labor strikes"]),
        CountryHotspot("DE", 0.43, ["energy crisis", "renewable transition"]),
        CountryHotspot("JP", 0.38, ["earthquake preparedness", "infrastructure"]),
        CountryHotspot("IN", 0.71, ["election campaigns", "political rallies"]),
        CountryHotspot("CN", 0.62, ["economic growth", "trade policies"]),
        CountryHotspot("AU", 0.35, ["bushfire season", "climate adaptation"])
    ]

    # Filter by countries if specified
    if countries:
        country_list = [c.strip().upper() for c in countries.split(",")]
        mock_data = [h for h in mock_data if h.country_code in country_list]

    return mock_data


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def estimate_hex_count(resolution: int, country_codes: List[str]) -> int:
    """
    Estimate number of hexagons for given resolution and countries.

    Useful for:
    - Warning users about large payloads
    - Setting timeout expectations
    - Cache sizing
    """
    # Approximate hex counts per country at different resolutions
    # (Based on average country size)

    avg_country_size_km2 = 500000  # ~500k km² average

    # H3 hex area at each resolution (km²)
    hex_areas = {
        0: 4250000,
        1: 607000,
        2: 86700,
        3: 12400,
        4: 1770,
        5: 253,
        6: 36.1,
        7: 5.16,
        8: 0.737,
        9: 0.105,
        10: 0.015,
        11: 0.002,
        12: 0.0003
    }

    hex_area = hex_areas.get(resolution, 1.0)
    hexes_per_country = int(avg_country_size_km2 / hex_area)

    total_estimate = hexes_per_country * len(country_codes)

    return total_estimate


def hex_to_geojson(hexagons: List[Hexagon]) -> dict:
    """
    Convert hexagons to GeoJSON FeatureCollection.

    Useful for:
    - Debugging (visualize in geojson.io)
    - Alternative rendering approaches
    - Export functionality
    """
    features = []

    for hex_obj in hexagons:
        # Get hexagon boundary
        boundary = h3.h3_to_geo_boundary(hex_obj.h3_index, geo_json=True)

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [boundary]
            },
            "properties": {
                "h3_index": hex_obj.h3_index,
                "intensity": hex_obj.intensity,
                "country": hex_obj.country,
                "top_topic": hex_obj.top_topic
            }
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features
    }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    """
    Test the hex generator locally without FastAPI.
    """
    print("Testing HexGenerator...")

    # Initialize
    gen = HexGenerator("../../data/countries.geojson")

    # Test 1: Convert single country
    print("\n[Test 1] Convert US to hexagons (resolution 3)")
    us_hexes = gen.country_to_hexes("US", intensity=0.9, resolution=3, top_topic="election")
    print(f"Generated {len(us_hexes)} hexagons for US")

    # Test 2: Aggregate multiple countries
    print("\n[Test 2] Aggregate US + BR + CO")
    br_hexes = gen.country_to_hexes("BR", intensity=0.7, resolution=3, top_topic="climate")
    co_hexes = gen.country_to_hexes("CO", intensity=0.5, resolution=3, top_topic="peace")

    combined = us_hexes + br_hexes + co_hexes
    aggregated = gen.aggregate_hexes(combined)
    print(f"Total hexagons before aggregation: {len(combined)}")
    print(f"Total hexagons after aggregation: {len(aggregated)}")

    # Test 3: Apply smoothing
    print("\n[Test 3] Apply k-ring smoothing")
    smoothed = gen.smooth_hexes(aggregated, k=2, decay_factor=0.5)
    print(f"Hexagons after smoothing: {len(smoothed)}")

    # Test 4: Convert to GeoJSON
    print("\n[Test 4] Export to GeoJSON")
    geojson = hex_to_geojson(smoothed[:100])  # First 100 hexes
    with open("hexmap_test.geojson", "w") as f:
        json.dump(geojson, f, indent=2)
    print("Saved to hexmap_test.geojson (open in geojson.io)")

    print("\n✅ All tests complete!")
