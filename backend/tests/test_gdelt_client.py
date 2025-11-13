"""Tests for GDELT client service."""

import pytest
import io
import zipfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import httpx

from app.services.gdelt_client import GDELTClient


class TestGDELTClient:
    """Test suite for GDELTClient."""

    def test_initialization(self):
        """Test GDELTClient initialization."""
        client = GDELTClient()
        assert client.base_url == "http://data.gdeltproject.org/gdeltv2"
        assert client.timeout == 30.0

    def test_country_codes_mapping(self):
        """Test that country codes are properly mapped."""
        assert GDELTClient.COUNTRY_CODES["US"] == "United States"
        assert GDELTClient.COUNTRY_CODES["BR"] == "Brazil"
        assert GDELTClient.COUNTRY_CODES["CO"] == "Colombia"
        assert len(GDELTClient.COUNTRY_CODES) >= 17

    def test_get_latest_gkg_url_format(self):
        """Test that GKG URL is correctly formatted."""
        client = GDELTClient()

        # Mock current time to ensure consistent URL generation
        with patch('app.services.gdelt_client.datetime') as mock_datetime:
            mock_now = datetime(2025, 1, 13, 14, 37, 25)
            mock_datetime.utcnow.return_value = mock_now

            url = client._get_latest_gkg_url()

            # Should round to 14:30, then subtract 10 minutes = 14:20
            expected_timestamp = "20250113142000"
            expected_url = f"http://data.gdeltproject.org/gdeltv2/{expected_timestamp}.gkg.csv.zip"
            assert url == expected_url

    def test_get_latest_gkg_url_rounding(self):
        """Test that GKG URL correctly rounds to 15-minute intervals."""
        client = GDELTClient()

        test_cases = [
            # (input_time, expected_timestamp)
            (datetime(2025, 1, 13, 14, 0, 0), "20250113134500"),  # 14:00 -> 14:00 -> 13:50
            (datetime(2025, 1, 13, 14, 7, 30), "20250113134500"),  # 14:07 -> 14:00 -> 13:50
            (datetime(2025, 1, 13, 14, 15, 0), "20250113140500"),  # 14:15 -> 14:15 -> 14:05
            (datetime(2025, 1, 13, 14, 22, 45), "20250113140500"),  # 14:22 -> 14:15 -> 14:05
            (datetime(2025, 1, 13, 14, 30, 0), "20250113142000"),  # 14:30 -> 14:30 -> 14:20
            (datetime(2025, 1, 13, 14, 44, 59), "20250113143000"),  # 14:44 -> 14:30 -> 14:20
            (datetime(2025, 1, 13, 14, 45, 0), "20250113143500"),  # 14:45 -> 14:45 -> 14:35
        ]

        for input_time, expected_timestamp in test_cases:
            with patch('app.services.gdelt_client.datetime') as mock_datetime:
                mock_datetime.utcnow.return_value = input_time
                url = client._get_latest_gkg_url()
                assert expected_timestamp in url, f"Failed for {input_time}"

    def test_is_country_relevant_exact_code(self):
        """Test country filtering with exact country code."""
        client = GDELTClient()

        # Test with country code in locations string
        locations = "1#United States#US#37.09#-95.71;2#Brazil#BR#-14.23#-51.92"
        assert client._is_country_relevant(locations, "US") is True
        assert client._is_country_relevant(locations, "BR") is True
        assert client._is_country_relevant(locations, "CO") is False

    def test_is_country_relevant_country_name(self):
        """Test country filtering with country name."""
        client = GDELTClient()

        locations = "1#United States#US#37.09#-95.71"
        assert client._is_country_relevant(locations, "US") is True

        locations = "1#Brazil#BR#-14.23#-51.92"
        assert client._is_country_relevant(locations, "BR") is True

    def test_is_country_relevant_empty_locations(self):
        """Test country filtering with empty locations."""
        client = GDELTClient()
        assert client._is_country_relevant("", "US") is False
        assert client._is_country_relevant(None, "US") is False

    def test_parse_themes_valid(self):
        """Test theme parsing with valid semicolon-separated themes."""
        client = GDELTClient()

        themes_str = "WB_632_ECONOMIC_POLICY;TAX_TAXATION;UNGP_HUMAN_RIGHTS"
        themes = client._parse_themes(themes_str)

        assert len(themes) == 3
        assert "WB_632_ECONOMIC_POLICY" in themes
        assert "TAX_TAXATION" in themes
        assert "UNGP_HUMAN_RIGHTS" in themes

    def test_parse_themes_empty(self):
        """Test theme parsing with empty string."""
        client = GDELTClient()

        assert client._parse_themes("") == []
        assert client._parse_themes(None) == []

    def test_parse_themes_filters_long(self):
        """Test that very long themes are filtered out."""
        client = GDELTClient()

        # Create a theme longer than 100 characters
        long_theme = "A" * 150
        themes_str = f"VALID_THEME;{long_theme};ANOTHER_VALID"
        themes = client._parse_themes(themes_str)

        # Should only return the valid themes
        assert len(themes) == 2
        assert "VALID_THEME" in themes
        assert "ANOTHER_VALID" in themes
        assert long_theme not in themes

    def test_parse_themes_filters_empty(self):
        """Test that empty themes are filtered out."""
        client = GDELTClient()

        themes_str = "THEME1;;THEME2;  ;THEME3"
        themes = client._parse_themes(themes_str)

        # Should only return non-empty themes
        assert len(themes) == 3
        assert "THEME1" in themes
        assert "THEME2" in themes
        assert "THEME3" in themes

    def test_clean_theme_name_removes_prefixes(self):
        """Test that theme name cleaning removes common prefixes."""
        client = GDELTClient()

        assert client._clean_theme_name("WB_632_ECONOMIC_POLICY") == "Economic Policy"
        assert client._clean_theme_name("TAX_TAXATION") == "Taxation"
        assert client._clean_theme_name("UNGP_HUMAN_RIGHTS") == "Human Rights"

    def test_clean_theme_name_removes_numbers(self):
        """Test that theme name cleaning removes leading numbers."""
        client = GDELTClient()

        assert client._clean_theme_name("WB_632_POLICY") == "Policy"
        assert client._clean_theme_name("123_456_TEST") == "Test"

    def test_clean_theme_name_title_case(self):
        """Test that theme names are converted to title case."""
        client = GDELTClient()

        assert client._clean_theme_name("ECONOMIC_POLICY") == "Economic Policy"
        assert client._clean_theme_name("CLIMATE_CHANGE") == "Climate Change"

    def test_clean_theme_name_length_limit(self):
        """Test that theme names are truncated to 50 characters."""
        client = GDELTClient()

        long_theme = "VERY_LONG_THEME_NAME_" * 10
        cleaned = client._clean_theme_name(long_theme)

        assert len(cleaned) <= 50
        assert cleaned.endswith("...")

    def test_clean_theme_name_fallback(self):
        """Test that theme name cleaning has fallback."""
        client = GDELTClient()

        # Theme with only numbers should return original
        assert client._clean_theme_name("123_456") == "123_456"

    def test_generate_gdelt_fallback_structure(self):
        """Test that fallback data has correct structure."""
        client = GDELTClient()

        fallback = client._generate_gdelt_fallback("US")

        assert len(fallback) == 5
        for item in fallback:
            assert "title" in item
            assert "source" in item
            assert "count" in item
            assert item["source"] == "gdelt_fallback"
            assert "US" in item["title"]

    def test_generate_gdelt_fallback_country_specific(self):
        """Test that fallback data is country-specific."""
        client = GDELTClient()

        fallback_us = client._generate_gdelt_fallback("US")
        fallback_br = client._generate_gdelt_fallback("BR")

        # Should contain country code in titles
        assert any("US" in item["title"] for item in fallback_us)
        assert any("BR" in item["title"] for item in fallback_br)

    @pytest.mark.asyncio
    async def test_download_and_parse_gkg_success(self):
        """Test successful GKG CSV download and parsing."""
        client = GDELTClient()

        # Create mock CSV data
        csv_content = "\t".join([
            "20250113140000",  # COL_DATE
            "",  # 1
            "",  # 2
            "",  # 3
            "",  # 4
            "",  # 5
            "",  # 6
            "ECONOMIC_POLICY;TAXATION;HEALTHCARE",  # COL_THEMES (7)
            "",  # 8
            "1#United States#US#37.09#-95.71",  # COL_LOCATIONS (9)
            "",  # 10
            "",  # 11
            "",  # 12
            "",  # 13
            "",  # 14
            "",  # COL_GCAM (15)
        ]) + "\n"

        # Add more rows to test frequency counting
        csv_content += "\t".join([
            "20250113140000",
            "", "", "", "", "", "",
            "ECONOMIC_POLICY;CLIMATE_CHANGE",  # Different themes
            "",
            "1#United States#US#37.09#-95.71",
            "", "", "", "", "", "",
        ]) + "\n"

        # Create ZIP file in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("20250113140000.gkg.csv", csv_content)
        zip_buffer.seek(0)

        # Mock HTTP client
        mock_response = Mock()
        mock_response.content = zip_buffer.read()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client):
            topics = await client._download_and_parse_gkg(
                "http://example.com/test.gkg.csv.zip",
                "US"
            )

        # Should return topics
        assert len(topics) > 0

        # Check structure
        for topic in topics:
            assert "title" in topic
            assert "source" in topic
            assert "count" in topic
            assert topic["source"] == "gdelt"

        # ECONOMIC_POLICY should appear twice, so it should be first
        assert topics[0]["count"] == 2

    @pytest.mark.asyncio
    async def test_download_and_parse_gkg_no_matches(self):
        """Test GKG parsing when no country matches are found."""
        client = GDELTClient()

        # Create CSV with different country
        csv_content = "\t".join([
            "20250113140000",
            "", "", "", "", "", "",
            "ECONOMIC_POLICY",
            "",
            "1#Brazil#BR#-14.23#-51.92",  # BR, not US
            "", "", "", "", "", "",
        ]) + "\n"

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("test.gkg.csv", csv_content)
        zip_buffer.seek(0)

        mock_response = Mock()
        mock_response.content = zip_buffer.read()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(ValueError, match="No GDELT data found"):
                await client._download_and_parse_gkg(
                    "http://example.com/test.gkg.csv.zip",
                    "US"
                )

    @pytest.mark.asyncio
    async def test_download_and_parse_gkg_malformed_rows(self):
        """Test GKG parsing with malformed rows."""
        client = GDELTClient()

        # Create CSV with some malformed rows
        csv_content = "short\trow\n"  # Only 2 columns, should be skipped
        csv_content += "\t".join([
            "20250113140000",
            "", "", "", "", "", "",
            "VALID_THEME",
            "",
            "1#United States#US#37.09#-95.71",
            "", "", "", "", "", "",
        ]) + "\n"

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("test.gkg.csv", csv_content)
        zip_buffer.seek(0)

        mock_response = Mock()
        mock_response.content = zip_buffer.read()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client):
            topics = await client._download_and_parse_gkg(
                "http://example.com/test.gkg.csv.zip",
                "US"
            )

        # Should still get topics from valid row
        assert len(topics) > 0

    @pytest.mark.asyncio
    async def test_fetch_trending_topics_success(self):
        """Test successful fetch of trending topics."""
        client = GDELTClient()

        # Mock the download_and_parse_gkg method
        expected_topics = [
            {"title": "Economic Policy", "source": "gdelt", "count": 45},
            {"title": "Healthcare", "source": "gdelt", "count": 32},
        ]

        with patch.object(client, '_download_and_parse_gkg',
                          AsyncMock(return_value=expected_topics)):
            topics = await client.fetch_trending_topics("US")

        assert topics == expected_topics

    @pytest.mark.asyncio
    async def test_fetch_trending_topics_fallback_on_error(self):
        """Test that fetch_trending_topics falls back on errors."""
        client = GDELTClient()

        # Mock download_and_parse_gkg to raise an error
        with patch.object(client, '_download_and_parse_gkg',
                          AsyncMock(side_effect=httpx.HTTPError("Network error"))):
            topics = await client.fetch_trending_topics("US")

        # Should return fallback data
        assert len(topics) == 5
        assert all(item["source"] == "gdelt_fallback" for item in topics)

    @pytest.mark.asyncio
    async def test_fetch_trending_topics_fallback_on_timeout(self):
        """Test that fetch_trending_topics falls back on timeout."""
        client = GDELTClient()

        # Mock download_and_parse_gkg to raise timeout
        with patch.object(client, '_download_and_parse_gkg',
                          AsyncMock(side_effect=TimeoutError("Request timeout"))):
            topics = await client.fetch_trending_topics("BR")

        # Should return fallback data
        assert len(topics) == 5
        assert all(item["source"] == "gdelt_fallback" for item in topics)
        assert all("BR" in item["title"] for item in topics)

    @pytest.mark.asyncio
    async def test_download_and_parse_gkg_respects_max_themes(self):
        """Test that max_themes parameter limits themes per record."""
        client = GDELTClient()

        # Create a row with many themes
        many_themes = ";".join([f"THEME_{i}" for i in range(100)])
        csv_content = "\t".join([
            "20250113140000",
            "", "", "", "", "", "",
            many_themes,
            "",
            "1#United States#US#37.09#-95.71",
            "", "", "", "", "", "",
        ]) + "\n"

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("test.gkg.csv", csv_content)
        zip_buffer.seek(0)

        mock_response = Mock()
        mock_response.content = zip_buffer.read()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client):
            topics = await client._download_and_parse_gkg(
                "http://example.com/test.gkg.csv.zip",
                "US",
                max_themes=10  # Limit to 10 themes per record
            )

        # Should return at most 10 topics (limited by max_themes)
        assert len(topics) <= 10

    @pytest.mark.asyncio
    async def test_download_and_parse_gkg_returns_top_10(self):
        """Test that only top 10 themes are returned."""
        client = GDELTClient()

        # Create multiple rows with different theme frequencies
        csv_rows = []
        for i in range(20):
            theme = f"THEME_{i % 15}"  # 15 unique themes with varying frequencies
            csv_rows.append("\t".join([
                "20250113140000",
                "", "", "", "", "", "",
                theme,
                "",
                "1#United States#US#37.09#-95.71",
                "", "", "", "", "", "",
            ]))

        csv_content = "\n".join(csv_rows) + "\n"

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("test.gkg.csv", csv_content)
        zip_buffer.seek(0)

        mock_response = Mock()
        mock_response.content = zip_buffer.read()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch('httpx.AsyncClient', return_value=mock_client):
            topics = await client._download_and_parse_gkg(
                "http://example.com/test.gkg.csv.zip",
                "US"
            )

        # Should return at most 10 topics
        assert len(topics) <= 10

        # Topics should be sorted by count (descending)
        if len(topics) > 1:
            for i in range(len(topics) - 1):
                assert topics[i]["count"] >= topics[i + 1]["count"]
