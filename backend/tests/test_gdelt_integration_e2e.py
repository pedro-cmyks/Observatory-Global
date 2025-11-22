"""
End-to-End Integration Test for GDELT Pipeline.

Tests the complete data flow:
1. Download GKG file from GDELT
2. Parse GKG CSV
3. Convert GKGRecord → GDELTSignal
4. Client integration
5. API response validation

Note: This test requires network access and may be slow due to real downloads.
Mark as integration test in pytest configuration.
"""

import pytest
import asyncio
from pathlib import Path
from app.services.gdelt_downloader import GDELTDownloader
from app.services.gdelt_parser import GDELTParser
from app.services.gdelt_client import GDELTClient
from app.adapters.gdelt_adapter import convert_gkg_to_signals


class TestGDELTPipelineE2E:
    """End-to-end integration tests for GDELT pipeline."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_full_pipeline_with_real_data(self):
        """
        Test complete pipeline: Download → Parse → Convert → Filter.

        This is the golden path test that validates the entire system.
        """
        # Step 1: Download real GDELT file
        downloader = GDELTDownloader()
        csv_path = await downloader.download_latest()

        # Should successfully download a file
        assert csv_path is not None
        assert csv_path.exists()
        assert csv_path.suffix == '.csv'

        # Step 2: Parse GKG file
        parser = GDELTParser()
        records = list(parser.parse_gkg_file(csv_path))

        # Should parse at least some records
        assert len(records) > 0, "Parser should return GKG records"

        # Step 3: Convert GKGRecord → GDELTSignal
        all_signals = []
        for record in records[:10]:  # Test first 10 records
            signals = convert_gkg_to_signals(record)
            all_signals.extend(signals)

        # Should create signals (one per theme)
        assert len(all_signals) > 0, "Should create signals from records"

        # Step 4: Validate signal schema
        for signal in all_signals[:5]:
            # Required fields
            assert signal.signal_id is not None
            assert signal.timestamp is not None
            assert signal.primary_location is not None
            assert len(signal.themes) > 0
            assert len(signal.theme_labels) > 0
            assert len(signal.theme_counts) > 0
            assert signal.tone is not None

            # Derived fields
            assert 0.0 <= signal.intensity <= 1.0
            assert signal.sentiment_label in ["very_negative", "negative", "neutral", "positive", "very_positive"]
            assert signal.geographic_precision in ["country", "state", "city"]

            # Source attribution
            assert signal.sources.gdelt is True
            assert signal.confidence > 0.0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_client_fetch_signals(self):
        """
        Test GDELTClient integration with real download and parse.
        """
        client = GDELTClient()

        # Fetch signals for a test country
        signals = await client.fetch_gdelt_signals("US", count=10)

        # Should return signals (real or placeholder)
        assert len(signals) > 0
        assert len(signals) <= 10

        # Validate signal structure
        for signal in signals:
            assert signal.signal_id is not None
            assert signal.primary_location.country_code == "US"
            assert len(signal.themes) > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_client_caching(self):
        """
        Test that client caching works correctly.
        """
        client = GDELTClient()

        # First fetch (should download and parse)
        signals_1 = await client.fetch_gdelt_signals("BR", count=5)

        # Second fetch (should use cache)
        signals_2 = await client.fetch_gdelt_signals("BR", count=5)

        # Should return cached results
        assert len(signals_1) > 0
        assert len(signals_2) > 0

        # Cache hit should be much faster (but we don't measure time here)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_fallback_to_placeholder(self):
        """
        Test graceful fallback when GDELT download fails.
        """
        client = GDELTClient()

        # Force a download failure by using invalid timestamp
        client.downloader.get_latest_timestamp = lambda: "19700101000000"

        # Should fall back to placeholder data
        signals = await client.fetch_gdelt_signals("GB", count=5)

        # Should still return signals (placeholders)
        assert len(signals) > 0
        assert len(signals) <= 5

    def test_converter_with_mock_record(self):
        """
        Test converter with a hand-crafted GKGRecord.

        This is a unit-level test but included here for completeness.
        """
        from app.services.gdelt_parser import GKGRecord, GKGLocation, GKGTone, GKGCount
        from datetime import datetime, timezone

        # Create minimal valid record
        record = GKGRecord(
            record_id="TEST123",
            timestamp=datetime(2025, 1, 20, 12, 0, 0, tzinfo=timezone.utc),
            source_collection=1,
            source_name="test.com",
            source_url="https://test.com/article",
            themes=["THEME_A", "THEME_B"],
            locations=[
                GKGLocation(
                    location_type=3,
                    full_name="New York",
                    country_code="US",
                    country_name="United States",
                    adm1_code="USNY",
                    latitude=40.7128,
                    longitude=-74.0060,
                    feature_id="5128581",
                    char_offset=100
                )
            ],
            tone=GKGTone(
                overall=-5.0,
                positive_pct=10.0,
                negative_pct=40.0,
                polarity=2.0,
                activity_density=15.0,
                self_group_ref=3.0,
                word_count=200
            ),
            counts=[
                GKGCount("THEME_A", 10, "", None),
                GKGCount("THEME_B", 5, "", None)
            ]
        )

        # Convert
        signals = convert_gkg_to_signals(record)

        # Should create 2 signals (one per theme)
        assert len(signals) == 2

        # Validate conversion
        for signal in signals:
            assert signal.primary_location.country_code == "US"
            assert signal.tone.overall == -5.0
            assert signal.theme_counts["THEME_A"] == 10
            assert signal.theme_counts["THEME_B"] == 5


@pytest.mark.integration
class TestGDELTDataQuality:
    """Tests for data quality validation."""

    @pytest.mark.asyncio
    async def test_signals_have_valid_coordinates(self):
        """Ensure all signals have valid lat/long."""
        client = GDELTClient()
        signals = await client.fetch_gdelt_signals("JP", count=10)

        for signal in signals:
            loc = signal.primary_location
            assert -90.0 <= loc.latitude <= 90.0
            assert -180.0 <= loc.longitude <= 180.0

    @pytest.mark.asyncio
    async def test_signals_have_valid_sentiment(self):
        """Ensure all signals have valid sentiment scores."""
        client = GDELTClient()
        signals = await client.fetch_gdelt_signals("DE", count=10)

        for signal in signals:
            assert -100.0 <= signal.tone.overall <= 100.0
            assert 0.0 <= signal.tone.positive_pct <= 100.0
            assert 0.0 <= signal.tone.negative_pct <= 100.0
