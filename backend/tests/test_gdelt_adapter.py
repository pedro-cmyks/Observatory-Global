"""
Unit tests for GDELT adapter functions.

Tests:
- Country centroid mapping
- Theme label normalization
- GKGRecord → GDELTSignal conversion (one signal per theme)
- Location fallback to country centroids
- Edge cases (missing fields, empty data)
"""

import pytest
from datetime import datetime, timezone
from app.adapters.gdelt_adapter import (
    get_country_centroid,
    normalize_theme_label,
    convert_gkg_to_signals,
)
from app.services.gdelt_parser import (
    GKGRecord,
    GKGLocation,
    GKGTone,
    GKGCount,
)


class TestCountryCentroids:
    """Test country centroid lookup function."""

    def test_known_country(self):
        """Test centroid for known country (US)."""
        lat, lon, name = get_country_centroid("US")
        assert lat == pytest.approx(37.0902)
        assert lon == pytest.approx(-95.7129)
        assert name == "United States"

    def test_another_known_country(self):
        """Test centroid for another known country (BR)."""
        lat, lon, name = get_country_centroid("BR")
        assert lat == pytest.approx(-14.2350)
        assert lon == pytest.approx(-51.9253)
        assert name == "Brazil"

    def test_unknown_country_fallback(self):
        """Test fallback for unknown country."""
        lat, lon, name = get_country_centroid("XX")
        assert lat == 0.0
        assert lon == 0.0
        assert name == "XX"  # Returns input as name


class TestThemeLabelNormalization:
    """Test theme label normalization."""

    def test_wb_prefix_removal(self):
        """Test World Bank prefix removal and formatting."""
        label = normalize_theme_label("WB_632_WOMEN_IN_POLITICS")
        assert label == "Women In Politics"

    def test_tax_prefix_removal(self):
        """Test GDELT taxonomy prefix removal."""
        label = normalize_theme_label("TAX_TERROR")
        assert label == "Terror"

    def test_econ_prefix(self):
        """Test economics prefix."""
        label = normalize_theme_label("ECON_INFLATION")
        assert label == "Inflation"

    def test_no_prefix(self):
        """Test theme without prefix."""
        label = normalize_theme_label("PROTEST")
        assert label == "Protest"

    def test_empty_string(self):
        """Test empty string fallback."""
        label = normalize_theme_label("")
        assert label == ""


class TestGKGRecordConversion:
    """Test GKGRecord → GDELTSignal conversion."""

    def create_sample_gkg_record(
        self,
        themes=None,
        locations=None,
        tone=None,
        counts=None
    ):
        """Helper to create test GKGRecord."""
        if themes is None:
            themes = ["ECON_INFLATION", "PROTEST"]
        if tone is None:
            tone = GKGTone(
                overall=-3.5,
                positive_pct=2.1,
                negative_pct=45.2,
                polarity=1.8,
                activity_density=12.0,
                self_group_ref=5.0,
                word_count=250
            )
        if counts is None:
            counts = [
                GKGCount(
                    count_type="ECON_INFLATION",
                    number=52,
                    object_type="",
                    location=None
                ),
                GKGCount(
                    count_type="PROTEST",
                    number=34,
                    object_type="",
                    location=None
                )
            ]
        if locations is None:
            locations = [
                GKGLocation(
                    location_type=3,
                    full_name="New York",
                    country_code="US",
                    country_name="United States",
                    adm1_code="USNY",
                    latitude=40.7128,
                    longitude=-74.0060,
                    feature_id="5128581",
                    char_offset=234
                )
            ]

        return GKGRecord(
            record_id="20250120120000-T52",
            timestamp=datetime(2025, 1, 20, 12, 0, 0, tzinfo=timezone.utc),
            source_collection=1,
            source_name="nytimes.com",
            source_url="https://www.nytimes.com/article",
            themes=themes,
            locations=locations,
            tone=tone,
            counts=counts,
            persons=["Jerome Powell"],
            organizations=["Federal Reserve"]
        )

    def test_complete_record_conversion(self):
        """Test conversion of complete GKGRecord with all fields."""
        record = self.create_sample_gkg_record()
        signals = convert_gkg_to_signals(record)

        # Should create 2 signals (one per theme)
        assert len(signals) == 2

        # Check first signal
        signal = signals[0]
        assert signal.signal_id == "20250120120000-T52_ECON_INFLATION"
        assert signal.timestamp == record.timestamp
        assert signal.source_collection_id == 1
        assert signal.primary_location.country_code == "US"
        assert signal.primary_location.latitude == pytest.approx(40.7128)
        assert signal.tone.overall == pytest.approx(-3.5)
        assert "ECON_INFLATION" in signal.themes
        assert "PROTEST" in signal.themes
        assert signal.theme_counts["ECON_INFLATION"] == 52
        assert signal.theme_counts["PROTEST"] == 34
        assert signal.persons == ["Jerome Powell"]
        assert signal.organizations == ["Federal Reserve"]
        assert signal.source_url == "https://www.nytimes.com/article"
        assert signal.source_outlet == "nytimes.com"

    def test_one_signal_per_theme(self):
        """Test that we get one signal per theme."""
        record = self.create_sample_gkg_record(
            themes=["THEME_A", "THEME_B", "THEME_C"]
        )
        signals = convert_gkg_to_signals(record)

        assert len(signals) == 3
        assert signals[0].signal_id == "20250120120000-T52_THEME_A"
        assert signals[1].signal_id == "20250120120000-T52_THEME_B"
        assert signals[2].signal_id == "20250120120000-T52_THEME_C"

        # All signals should have the same themes list
        for signal in signals:
            assert signal.themes == ["THEME_A", "THEME_B", "THEME_C"]

    def test_no_location_uses_centroid(self):
        """Test that missing location falls back to country centroid."""
        record = self.create_sample_gkg_record(locations=[])
        signals = convert_gkg_to_signals(record)

        assert len(signals) == 2
        signal = signals[0]

        # Should use US centroid (default fallback)
        assert signal.primary_location.country_code == "US"
        assert signal.primary_location.latitude == pytest.approx(37.0902)
        assert signal.primary_location.longitude == pytest.approx(-95.7129)
        assert signal.primary_location.location_type == 1  # Country-level

    def test_no_themes_returns_empty(self):
        """Test that record with no themes returns empty list."""
        record = self.create_sample_gkg_record(themes=[])
        signals = convert_gkg_to_signals(record)

        assert len(signals) == 0

    def test_no_counts_defaults_to_one(self):
        """Test that missing counts default to 1 per theme."""
        record = self.create_sample_gkg_record(counts=[])
        signals = convert_gkg_to_signals(record)

        assert len(signals) == 2
        signal = signals[0]

        # Should have default counts of 1
        assert signal.theme_counts["ECON_INFLATION"] == 1
        assert signal.theme_counts["PROTEST"] == 1

    def test_intensity_calculation(self):
        """Test intensity calculation (total_count / max_possible)."""
        record = self.create_sample_gkg_record(
            counts=[
                GKGCount("THEME_A", 250, "", None),
                GKGCount("THEME_B", 250, "", None)
            ]
        )
        signals = convert_gkg_to_signals(record)

        signal = signals[0]
        # Total count = 500, max_possible = 500 → intensity = 1.0
        assert signal.intensity == pytest.approx(1.0)

    def test_bucket_15min_rounding(self):
        """Test that timestamp is rounded to 15-minute bucket."""
        record = self.create_sample_gkg_record()
        record.timestamp = datetime(2025, 1, 20, 12, 37, 45, tzinfo=timezone.utc)

        signals = convert_gkg_to_signals(record)
        signal = signals[0]

        # Should round down to 12:30:00
        assert signal.bucket_15min == datetime(2025, 1, 20, 12, 30, 0, tzinfo=timezone.utc)

    def test_source_attribution(self):
        """Test that source attribution is set correctly."""
        record = self.create_sample_gkg_record()
        signals = convert_gkg_to_signals(record)
        signal = signals[0]

        assert signal.sources.gdelt is True
        assert signal.sources.google_trends is False
        assert signal.sources.wikipedia is False
        assert signal.confidence == pytest.approx(0.7)  # GDELT only = 0.7

    def test_url_hash_generation(self):
        """Test URL hash generation for deduplication."""
        record = self.create_sample_gkg_record()
        signals = convert_gkg_to_signals(record)
        signal = signals[0]

        # Should have non-empty hash
        assert signal.url_hash != ""
        assert signal.url_hash != "no_url"

    def test_multiple_locations(self):
        """Test record with multiple locations."""
        locations = [
            GKGLocation(3, "New York", "US", "United States", "USNY", 40.7128, -74.0060, "5128581", 100),
            GKGLocation(3, "Los Angeles", "US", "United States", "USCA", 34.0522, -118.2437, "5368361", 200),
        ]
        record = self.create_sample_gkg_record(locations=locations)
        signals = convert_gkg_to_signals(record)

        signal = signals[0]
        assert len(signal.locations) == 2
        # Primary location should be first
        assert signal.primary_location.location_name == "New York"

    def test_theme_labels_generated(self):
        """Test that theme labels are generated."""
        record = self.create_sample_gkg_record(
            themes=["ECON_INFLATION", "TAX_TERROR"]
        )
        signals = convert_gkg_to_signals(record)
        signal = signals[0]

        assert "Inflation" in signal.theme_labels
        assert "Terror" in signal.theme_labels

    def test_invalid_record_type_raises_error(self):
        """Test that passing wrong type raises ValueError."""
        with pytest.raises(ValueError, match="Expected GKGRecord"):
            convert_gkg_to_signals("not a record")

    def test_duplicate_count_aggregation(self):
        """Test that duplicate count types are aggregated."""
        counts = [
            GKGCount("KILL", 10, "", None),
            GKGCount("KILL", 5, "", None),  # Duplicate
            GKGCount("WOUND", 7, "", None),
        ]
        record = self.create_sample_gkg_record(counts=counts)
        signals = convert_gkg_to_signals(record)
        signal = signals[0]

        # KILL counts should be summed
        assert signal.theme_counts["KILL"] == 15
        assert signal.theme_counts["WOUND"] == 7
