"""Generate H3 hexmap payloads from country-level signal intensities.

This service is kept as a small compatibility layer for the legacy heatmap
contract. The active map UI is frontend-driven, but tests and downstream tools
still rely on this deterministic country-centroid to H3 conversion.
"""

from __future__ import annotations

from collections import defaultdict
from numbers import Real
from typing import Any

import h3

from app.core.country_metadata import COUNTRY_METADATA


class HexmapGenerator:
    """Generate smoothed H3 cells from country-level hotspots."""

    COUNTRY_CENTROIDS = {
        code: (lat, lng)
        for code, (_name, lat, lng) in COUNTRY_METADATA.items()
    }

    def __init__(self, default_resolution: int = 3):
        self.default_resolution = default_resolution

    def get_resolution_for_zoom(self, zoom: float) -> int:
        """Map a frontend map zoom level to a conservative H3 resolution."""
        if zoom < 0:
            zoom = 0
        if zoom < 3:
            return 1
        if zoom < 5:
            return 2
        if zoom < 7:
            return 3
        if zoom < 10:
            return 4
        return 6

    def generate_hexmap(
        self,
        hotspots: list[dict[str, Any]],
        resolution: int | None = None,
        k_ring: int = 2,
        normalize: bool = False,
    ) -> list[dict[str, float | str]]:
        """Convert country hotspots into H3 cells with optional k-ring smoothing."""
        resolution = self.default_resolution if resolution is None else resolution
        if resolution < 0 or resolution > 15:
            raise ValueError("Invalid H3 resolution")
        if k_ring < 0:
            raise ValueError("Invalid k_ring")

        intensities: defaultdict[str, float] = defaultdict(float)
        for hotspot in hotspots:
            country = str(hotspot.get("country", "")).upper()
            if country not in self.COUNTRY_CENTROIDS:
                continue

            intensity = float(hotspot.get("intensity", 0) or 0)
            lat, lng = self.COUNTRY_CENTROIDS[country]
            center = h3.latlng_to_cell(lat, lng, resolution)
            for cell in h3.grid_disk(center, k_ring):
                distance = h3.grid_distance(center, cell)
                intensities[cell] += intensity / (1 + distance)

        if not intensities:
            return []

        max_intensity = max(intensities.values())
        if normalize and max_intensity > 0:
            intensities = defaultdict(
                float,
                {cell: value / max_intensity for cell, value in intensities.items()},
            )

        return [
            {"h3_index": cell, "intensity": value}
            for cell, value in sorted(intensities.items())
        ]

    def validate_hexmap_data(self, hexmap: Any) -> tuple[bool, str]:
        """Validate the JSON-ready hexmap shape consumed by the frontend."""
        if not isinstance(hexmap, list):
            return False, "hexmap data must be a list"

        for item in hexmap:
            if not isinstance(item, dict):
                return False, "hexmap item must be an object"
            if "h3_index" not in item:
                return False, "hexmap item missing 'h3_index'"
            if "intensity" not in item:
                return False, "hexmap item missing 'intensity'"
            if not isinstance(item["h3_index"], str):
                return False, "h3_index must be string"
            if not isinstance(item["intensity"], Real):
                return False, "intensity must be number"
            if item["intensity"] < 0 or item["intensity"] > 1:
                return False, "intensity must be in [0, 1]"

        return True, ""
