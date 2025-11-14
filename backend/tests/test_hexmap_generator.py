"""Tests for hexmap generator service."""

import pytest
from app.services.hexmap_generator import HexmapGenerator


class TestHexmapGenerator:
    """Test suite for HexmapGenerator."""

    def test_initialization(self):
        """Test HexmapGenerator initialization."""
        generator = HexmapGenerator(default_resolution=4)
        assert generator.default_resolution == 4

    def test_initialization_defaults(self):
        """Test HexmapGenerator initialization with defaults."""
        generator = HexmapGenerator()
        assert generator.default_resolution == 3

    def test_country_centroids_defined(self):
        """Test that country centroids are properly defined."""
        assert len(HexmapGenerator.COUNTRY_CENTROIDS) >= 17
        assert 'US' in HexmapGenerator.COUNTRY_CENTROIDS
        assert 'BR' in HexmapGenerator.COUNTRY_CENTROIDS
        assert 'GB' in HexmapGenerator.COUNTRY_CENTROIDS

        # Validate centroid format (lat, lng)
        us_centroid = HexmapGenerator.COUNTRY_CENTROIDS['US']
        assert isinstance(us_centroid, tuple)
        assert len(us_centroid) == 2
        lat, lng = us_centroid
        assert -90 <= lat <= 90
        assert -180 <= lng <= 180

    def test_zoom_to_resolution_mapping(self):
        """Test zoom level to H3 resolution mapping."""
        generator = HexmapGenerator()

        # Test specific mappings
        assert generator.get_resolution_for_zoom(0) == 1
        assert generator.get_resolution_for_zoom(3) == 2
        assert generator.get_resolution_for_zoom(5) == 3
        assert generator.get_resolution_for_zoom(7) == 4
        assert generator.get_resolution_for_zoom(10) == 6

    def test_get_resolution_for_zoom_clamping(self):
        """Test that zoom values are clamped to valid range."""
        generator = HexmapGenerator()

        # Test below minimum
        assert generator.get_resolution_for_zoom(-5) == 1  # Should clamp to 0

        # Test above maximum
        assert generator.get_resolution_for_zoom(20) == 6  # Should clamp to 12

    def test_generate_hexmap_single_country(self):
        """Test hexmap generation with single country."""
        generator = HexmapGenerator()

        hotspots = [
            {'country': 'US', 'intensity': 0.8}
        ]

        hexes = generator.generate_hexmap(hotspots, resolution=3, k_ring=0)

        # Should have exactly 1 hex (no smoothing)
        assert len(hexes) == 1
        assert hexes[0]['intensity'] == 0.8
        assert 'h3_index' in hexes[0]

    def test_generate_hexmap_multiple_countries(self):
        """Test hexmap generation with multiple countries."""
        generator = HexmapGenerator()

        hotspots = [
            {'country': 'US', 'intensity': 0.9},
            {'country': 'BR', 'intensity': 0.7},
            {'country': 'GB', 'intensity': 0.5},
        ]

        hexes = generator.generate_hexmap(hotspots, resolution=3, k_ring=0)

        # Should have exactly 3 hexes (no smoothing)
        assert len(hexes) == 3

        # Check intensities
        intensities = sorted([h['intensity'] for h in hexes])
        assert intensities == [0.5, 0.7, 0.9]

    def test_generate_hexmap_with_k_ring_smoothing(self):
        """Test that k-ring smoothing increases hex count."""
        generator = HexmapGenerator()

        hotspots = [
            {'country': 'US', 'intensity': 1.0}
        ]

        # Without smoothing
        hexes_no_smooth = generator.generate_hexmap(hotspots, resolution=3, k_ring=0)
        assert len(hexes_no_smooth) == 1

        # With k=1 smoothing (hex + 6 neighbors = 7 total)
        hexes_k1 = generator.generate_hexmap(hotspots, resolution=3, k_ring=1)
        assert len(hexes_k1) == 7

        # With k=2 smoothing (hex + k1 ring + k2 ring ≈ 19 hexes)
        hexes_k2 = generator.generate_hexmap(hotspots, resolution=3, k_ring=2)
        assert len(hexes_k2) == 19

    def test_generate_hexmap_normalization(self):
        """Test that intensities are normalized to [0, 1]."""
        generator = HexmapGenerator()

        hotspots = [
            {'country': 'US', 'intensity': 0.5},
            {'country': 'BR', 'intensity': 1.0},
        ]

        hexes = generator.generate_hexmap(hotspots, resolution=3, k_ring=2, normalize=True)

        # All intensities should be in [0, 1]
        for hex_data in hexes:
            assert 0 <= hex_data['intensity'] <= 1

        # Maximum should be 1.0 after normalization
        max_intensity = max(h['intensity'] for h in hexes)
        assert max_intensity == pytest.approx(1.0, abs=0.001)

    def test_generate_hexmap_without_normalization(self):
        """Test hexmap generation without normalization."""
        generator = HexmapGenerator()

        hotspots = [
            {'country': 'US', 'intensity': 0.5},
        ]

        hexes = generator.generate_hexmap(hotspots, resolution=3, k_ring=2, normalize=False)

        # Without normalization, center hex should have original intensity
        # After smoothing, some hexes will have distributed values
        intensities = [h['intensity'] for h in hexes]
        # Max value should be influenced by smoothing weights
        assert max(intensities) > 0

    def test_generate_hexmap_invalid_resolution(self):
        """Test that invalid resolution raises error."""
        generator = HexmapGenerator()

        hotspots = [{'country': 'US', 'intensity': 1.0}]

        with pytest.raises(ValueError, match="Invalid H3 resolution"):
            generator.generate_hexmap(hotspots, resolution=16)

        with pytest.raises(ValueError, match="Invalid H3 resolution"):
            generator.generate_hexmap(hotspots, resolution=-1)

    def test_generate_hexmap_unknown_country(self):
        """Test that unknown countries are logged but don't crash."""
        generator = HexmapGenerator()

        hotspots = [
            {'country': 'US', 'intensity': 1.0},
            {'country': 'INVALID', 'intensity': 0.5},  # Unknown country
        ]

        hexes = generator.generate_hexmap(hotspots, resolution=3, k_ring=0)

        # Should only generate hex for US
        assert len(hexes) == 1

    def test_generate_hexmap_empty_hotspots(self):
        """Test hexmap generation with empty hotspots list."""
        generator = HexmapGenerator()

        hexes = generator.generate_hexmap([], resolution=3, k_ring=2)

        # Should return empty list
        assert hexes == []

    def test_generate_hexmap_uses_default_resolution(self):
        """Test that default resolution is used when not specified."""
        generator = HexmapGenerator(default_resolution=4)

        hotspots = [{'country': 'US', 'intensity': 1.0}]

        hexes = generator.generate_hexmap(hotspots, resolution=None, k_ring=0)

        # Check that resolution 4 was used (can verify by h3_index format)
        # At resolution 4, different hex IDs than resolution 3
        assert len(hexes) == 1

    def test_validate_hexmap_data_valid(self):
        """Test validation with valid hexmap data."""
        generator = HexmapGenerator()

        hexmap = [
            {'h3_index': '8326eefffffffff', 'intensity': 0.8},
            {'h3_index': '8326edfffffffff', 'intensity': 0.5},
        ]

        is_valid, msg = generator.validate_hexmap_data(hexmap)

        assert is_valid is True
        assert msg == ""

    def test_validate_hexmap_data_not_list(self):
        """Test validation with non-list input."""
        generator = HexmapGenerator()

        is_valid, msg = generator.validate_hexmap_data("not a list")

        assert is_valid is False
        assert "must be a list" in msg

    def test_validate_hexmap_data_missing_h3_index(self):
        """Test validation with missing h3_index."""
        generator = HexmapGenerator()

        hexmap = [
            {'intensity': 0.8},  # Missing h3_index
        ]

        is_valid, msg = generator.validate_hexmap_data(hexmap)

        assert is_valid is False
        assert "missing 'h3_index'" in msg

    def test_validate_hexmap_data_missing_intensity(self):
        """Test validation with missing intensity."""
        generator = HexmapGenerator()

        hexmap = [
            {'h3_index': '8326eefffffffff'},  # Missing intensity
        ]

        is_valid, msg = generator.validate_hexmap_data(hexmap)

        assert is_valid is False
        assert "missing 'intensity'" in msg

    def test_validate_hexmap_data_invalid_intensity_type(self):
        """Test validation with invalid intensity type."""
        generator = HexmapGenerator()

        hexmap = [
            {'h3_index': '8326eefffffffff', 'intensity': "not a number"},
        ]

        is_valid, msg = generator.validate_hexmap_data(hexmap)

        assert is_valid is False
        assert "must be number" in msg

    def test_validate_hexmap_data_intensity_out_of_range(self):
        """Test validation with intensity out of [0, 1] range."""
        generator = HexmapGenerator()

        # Test above range
        hexmap = [
            {'h3_index': '8326eefffffffff', 'intensity': 1.5},
        ]

        is_valid, msg = generator.validate_hexmap_data(hexmap)

        assert is_valid is False
        assert "must be in [0, 1]" in msg

        # Test below range
        hexmap = [
            {'h3_index': '8326eefffffffff', 'intensity': -0.1},
        ]

        is_valid, msg = generator.validate_hexmap_data(hexmap)

        assert is_valid is False
        assert "must be in [0, 1]" in msg

    def test_validate_hexmap_data_invalid_h3_index_type(self):
        """Test validation with invalid h3_index type."""
        generator = HexmapGenerator()

        hexmap = [
            {'h3_index': 12345, 'intensity': 0.5},  # Should be string
        ]

        is_valid, msg = generator.validate_hexmap_data(hexmap)

        assert is_valid is False
        assert "must be string" in msg

    def test_k_ring_smoothing_intensity_distribution(self):
        """Test that k-ring smoothing properly distributes intensity."""
        generator = HexmapGenerator()

        hotspots = [
            {'country': 'US', 'intensity': 1.0}
        ]

        hexes = generator.generate_hexmap(hotspots, resolution=3, k_ring=1, normalize=False)

        # With k=1, we should have 7 hexes (center + 6 neighbors)
        assert len(hexes) == 7

        # The center hex should have highest intensity (distance 0, weight 1.0)
        intensities = sorted([h['intensity'] for h in hexes], reverse=True)

        # Center should have full weight (1.0 / (1 + 0) = 1.0)
        assert intensities[0] == pytest.approx(1.0, abs=0.001)

        # Neighbors should have half weight (1.0 / (1 + 1) = 0.5)
        for i in range(1, 7):
            assert intensities[i] == pytest.approx(0.5, abs=0.001)

    def test_multiple_overlapping_smoothing(self):
        """Test smoothing with overlapping k-rings from multiple countries."""
        generator = HexmapGenerator()

        # Place two countries close together (US and CA both in North America)
        hotspots = [
            {'country': 'US', 'intensity': 1.0},
            {'country': 'CA', 'intensity': 0.8},
        ]

        hexes = generator.generate_hexmap(hotspots, resolution=2, k_ring=2, normalize=True)

        # With k=2 smoothing from 2 sources, hexes can overlap
        # Total count should be less than or equal to 2 * 19 = 38
        # (some hexes receive intensity from both sources)
        assert len(hexes) <= 38

        # All intensities should be normalized
        max_intensity = max(h['intensity'] for h in hexes)
        assert max_intensity == pytest.approx(1.0, abs=0.001)

    def test_hexmap_generation_different_resolutions(self):
        """Test hexmap generation at different resolutions."""
        generator = HexmapGenerator()

        hotspots = [{'country': 'US', 'intensity': 1.0}]

        # Generate at different resolutions
        hexes_r2 = generator.generate_hexmap(hotspots, resolution=2, k_ring=1)
        hexes_r3 = generator.generate_hexmap(hotspots, resolution=3, k_ring=1)
        hexes_r4 = generator.generate_hexmap(hotspots, resolution=4, k_ring=1)

        # All should have 7 hexes (1 center + 6 neighbors)
        assert len(hexes_r2) == 7
        assert len(hexes_r3) == 7
        assert len(hexes_r4) == 7

        # But h3_index values should differ (different resolutions)
        assert hexes_r2[0]['h3_index'] != hexes_r3[0]['h3_index']
        assert hexes_r3[0]['h3_index'] != hexes_r4[0]['h3_index']

    def test_hexmap_generation_response_format(self):
        """Test that generated hexmap has correct response format."""
        generator = HexmapGenerator()

        hotspots = [
            {'country': 'US', 'intensity': 0.9},
            {'country': 'BR', 'intensity': 0.6},
        ]

        hexes = generator.generate_hexmap(hotspots, resolution=3, k_ring=2)

        # Check format of each hex
        for hex_data in hexes:
            assert isinstance(hex_data, dict)
            assert 'h3_index' in hex_data
            assert 'intensity' in hex_data
            assert len(hex_data) == 2  # Only these two keys

            # Check types
            assert isinstance(hex_data['h3_index'], str)
            assert isinstance(hex_data['intensity'], (int, float))

            # H3 index should be 15 characters (hex string)
            assert len(hex_data['h3_index']) == 15
