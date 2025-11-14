"""Hexagonal heatmap generator using H3 spatial indexing."""

import h3
import logging
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from app.core.country_metadata import get_country_coordinates

logger = logging.getLogger(__name__)


class HexmapGenerator:
    """
    Generates hexagonal heatmaps from country-level intensity data.

    Uses Uber's H3 spatial indexing system to convert country centroids
    into hexagonal tiles with smoothed intensity values.
    """

    # H3 resolution mapping based on zoom level
    ZOOM_TO_RESOLUTION = {
        0: 1,   # Global overview (840 hexes)
        1: 1,
        2: 2,   # Continental (5,880 hexes)
        3: 2,
        4: 3,   # Country/region (41,160 hexes)
        5: 3,
        6: 4,   # State/province (288,120 hexes)
        7: 4,
        8: 5,   # City clusters
        9: 5,
        10: 6,  # Urban areas
        11: 6,
        12: 6,
    }

    def __init__(self, default_resolution: int = 3):
        """
        Initialize hexmap generator.

        Args:
            default_resolution: Default H3 resolution (0-15)
                               3 = ~158km edge length (good for country-level)
        """
        self.default_resolution = default_resolution

    def generate_hexmap(
        self,
        hotspots: List[Dict[str, Any]],
        resolution: int | None = None,
        k_ring: int = 2,
        normalize: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Generate hexagonal heatmap from country hotspot data.

        Args:
            hotspots: List of {country_code: str, intensity: float}
            resolution: H3 resolution (if None, uses default)
            k_ring: K-ring radius for smoothing (0 = no smoothing)
            normalize: Whether to normalize intensities to [0, 1]

        Returns:
            List of {h3_index: str, intensity: float}
        """
        if resolution is None:
            resolution = self.default_resolution

        # Validate resolution
        if not 0 <= resolution <= 15:
            raise ValueError(f"Invalid H3 resolution: {resolution}. Must be 0-15.")

        # Convert hotspots to hex intensities
        hex_intensities = self._hotspots_to_hexes(hotspots, resolution)

        # Apply k-ring smoothing if requested
        if k_ring > 0:
            hex_intensities = self._apply_k_ring_smoothing(hex_intensities, k_ring)

        # Normalize if requested
        if normalize and hex_intensities:
            max_intensity = max(hex_intensities.values())
            if max_intensity > 0:
                hex_intensities = {
                    h: (v / max_intensity)
                    for h, v in hex_intensities.items()
                }

        # Convert to list format
        result = [
            {
                "h3_index": hex_id,
                "intensity": intensity
            }
            for hex_id, intensity in hex_intensities.items()
        ]

        logger.info(
            f"Generated hexmap: resolution={resolution}, "
            f"k_ring={k_ring}, hexes={len(result)}, "
            f"countries={len(hotspots)}"
        )

        return result

    def _hotspots_to_hexes(
        self,
        hotspots: List[Dict[str, Any]],
        resolution: int
    ) -> Dict[str, float]:
        """
        Convert country hotspots to H3 hexagon intensities.

        Strategy: For each country, create a hex at its centroid with the given intensity.
        Future iterations can expand this to polyfill entire country geometries.

        Args:
            hotspots: List of {country_code: str, intensity: float}
            resolution: H3 resolution

        Returns:
            Dict mapping h3_index -> intensity
        """
        hex_intensities = {}

        for hotspot in hotspots:
            country = hotspot.get('country_code')
            intensity = hotspot.get('intensity', 0.0)

            # Get country centroid from centralized metadata
            try:
                lat, lng = get_country_coordinates(country)
            except KeyError:
                logger.warning(f"Unknown country code: {country}")
                continue

            # Convert lat/lng to H3 index (H3 v4 API)
            try:
                hex_id = h3.latlng_to_cell(lat, lng, resolution)
                hex_intensities[hex_id] = intensity
            except Exception as e:
                logger.error(f"Error converting {country} to H3: {e}")
                continue

        return hex_intensities

    def _apply_k_ring_smoothing(
        self,
        hex_intensities: Dict[str, float],
        k: int
    ) -> Dict[str, float]:
        """
        Apply k-ring smoothing to hex intensities for blob effect.

        For each hex, spreads its intensity to neighbors within k distance
        using inverse distance weighting.

        Args:
            hex_intensities: Dict mapping h3_index -> intensity
            k: K-ring radius (1 = immediate neighbors, 2 = neighbors + their neighbors)

        Returns:
            Smoothed hex intensities
        """
        smoothed = defaultdict(float)

        for hex_id, intensity in hex_intensities.items():
            # Get k-ring neighbors (including self) using H3 v4 API
            try:
                neighbors = h3.grid_disk(hex_id, k)
            except Exception as e:
                logger.error(f"Error getting k-ring for {hex_id}: {e}")
                # Fall back to just the hex itself
                smoothed[hex_id] += intensity
                continue

            # Distribute intensity with distance decay
            for neighbor in neighbors:
                try:
                    # Calculate distance between hexes
                    if neighbor == hex_id:
                        distance = 0
                    else:
                        distance = h3.grid_distance(hex_id, neighbor)

                    # Inverse distance weighting: closer neighbors get more intensity
                    # distance=0 (self) gets full weight
                    # distance=1 gets 0.5 weight
                    # distance=2 gets 0.33 weight
                    weight = 1.0 / (1.0 + distance)

                    smoothed[neighbor] += intensity * weight

                except Exception as e:
                    logger.error(f"Error calculating distance: {e}")
                    continue

        return dict(smoothed)

    def get_resolution_for_zoom(self, zoom: float) -> int:
        """
        Get appropriate H3 resolution for given map zoom level.

        Args:
            zoom: Map zoom level (0-12+)

        Returns:
            H3 resolution (0-15)
        """
        # Clamp zoom to valid range
        zoom = max(0, min(12, int(zoom)))
        return self.ZOOM_TO_RESOLUTION.get(zoom, self.default_resolution)

    def validate_hexmap_data(self, hexmap: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """
        Validate hexmap data structure.

        Args:
            hexmap: List of hex data

        Returns:
            (is_valid, error_message)
        """
        if not isinstance(hexmap, list):
            return False, "Hexmap must be a list"

        for i, hex_data in enumerate(hexmap):
            if not isinstance(hex_data, dict):
                return False, f"Hex {i} must be a dict"

            if 'h3_index' not in hex_data:
                return False, f"Hex {i} missing 'h3_index'"

            if 'intensity' not in hex_data:
                return False, f"Hex {i} missing 'intensity'"

            # Validate H3 index format
            h3_index = hex_data['h3_index']
            if not isinstance(h3_index, str):
                return False, f"Hex {i} h3_index must be string"

            # Validate intensity range
            intensity = hex_data['intensity']
            if not isinstance(intensity, (int, float)):
                return False, f"Hex {i} intensity must be number"

            if not 0 <= intensity <= 1:
                return False, f"Hex {i} intensity must be in [0, 1]"

        return True, ""
