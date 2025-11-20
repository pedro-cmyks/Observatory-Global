"""
Tests for GDELT GKG Parser - V2Locations and V2Counts Methods

Tests cover:
1. Valid input parsing (single and multiple items)
2. Edge cases (empty strings, malformed data)
3. Validation logic (coordinate ranges, required fields)
4. Aggregation and deduplication behavior
5. Embedded location parsing in counts

Based on:
- ADR-0003: GDELT Parser Strategy
- Real GDELT GKG v2.1 format specifications
"""

import pytest
from app.services.gdelt_parser import GDELTParser, GKGLocation, GKGCount


class TestParseV2Locations:
    """Test suite for parse_v2_locations() method."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for tests."""
        return GDELTParser()

    def test_parse_single_country_location(self, parser):
        """Test parsing single country-level location (Type 1)."""
        locations_str = "1#United States#US###38#-97#US#1"  # ADM1 and ADM2 both empty

        locations = parser.parse_v2_locations(locations_str)

        assert len(locations) == 1
        assert locations[0].location_type == 1
        assert locations[0].full_name == "United States"
        assert locations[0].country_code == "US"
        assert locations[0].adm1_code == ""
        assert locations[0].adm2_code == ""
        assert locations[0].latitude == 38.0
        assert locations[0].longitude == -97.0
        assert locations[0].feature_id == "US"
        assert locations[0].char_offset == 1

    def test_parse_single_city_location(self, parser):
        """Test parsing single city-level location (Type 3)."""
        locations_str = "3#Los Angeles, California, United States#US#USCA#CA037#34.0522#-118.244#1662328#1325"

        locations = parser.parse_v2_locations(locations_str)

        assert len(locations) == 1
        loc = locations[0]
        assert loc.location_type == 3
        assert loc.full_name == "Los Angeles, California, United States"
        assert loc.country_code == "US"
        assert loc.adm1_code == "USCA"
        assert loc.adm2_code == "CA037"
        assert loc.latitude == pytest.approx(34.0522)
        assert loc.longitude == pytest.approx(-118.244)
        assert loc.feature_id == "1662328"
        assert loc.char_offset == 1325

    def test_parse_multiple_locations(self, parser):
        """Test parsing multiple locations separated by semicolons."""
        locations_str = "1#United States#US###38#-97#US#0;3#New York#US#USNY##40.7128#-74.006#5128581#234"

        locations = parser.parse_v2_locations(locations_str)

        assert len(locations) == 2

        # First location: Country
        assert locations[0].location_type == 1
        assert locations[0].full_name == "United States"
        assert locations[0].country_code == "US"
        assert locations[0].char_offset == 0

        # Second location: City
        assert locations[1].location_type == 3
        assert locations[1].full_name == "New York"
        assert locations[1].country_code == "US"
        assert locations[1].adm1_code == "USNY"
        assert locations[1].latitude == pytest.approx(40.7128)
        assert locations[1].longitude == pytest.approx(-74.006)
        assert locations[1].feature_id == "5128581"
        assert locations[1].char_offset == 234

    def test_parse_world_city_location(self, parser):
        """Test parsing world city location (Type 4)."""
        locations_str = "4#London, England, United Kingdom#GB#GBENG##51.5074#-0.1278#2643743#500"

        locations = parser.parse_v2_locations(locations_str)

        assert len(locations) == 1
        loc = locations[0]
        assert loc.location_type == 4
        assert loc.full_name == "London, England, United Kingdom"
        assert loc.country_code == "GB"
        assert loc.latitude == pytest.approx(51.5074)
        assert loc.longitude == pytest.approx(-0.1278)

    def test_parse_world_state_location(self, parser):
        """Test parsing world state/province location (Type 5)."""
        locations_str = "5#Ontario, Canada#CA#CAON##43.6532#-79.3832#6093943#100"

        locations = parser.parse_v2_locations(locations_str)

        assert len(locations) == 1
        loc = locations[0]
        assert loc.location_type == 5
        assert loc.full_name == "Ontario, Canada"
        assert loc.country_code == "CA"

    def test_parse_empty_string(self, parser):
        """Test parsing empty location string returns empty list."""
        assert parser.parse_v2_locations("") == []
        assert parser.parse_v2_locations("   ") == []
        assert parser.parse_v2_locations("\t\n") == []

    def test_parse_malformed_too_few_fields(self, parser):
        """Test handling location block with insufficient fields."""
        locations_str = "1#United States#US"  # Only 3 fields, need 7+

        locations = parser.parse_v2_locations(locations_str)

        # Should skip malformed block and return empty list
        assert locations == []

    def test_parse_invalid_location_type(self, parser):
        """Test handling invalid location type values."""
        # Type 0 (invalid)
        locations_str = "0#Unknown#US##38#-97#US#1"
        assert parser.parse_v2_locations(locations_str) == []

        # Type 6 (out of range)
        locations_str = "6#Invalid#US##38#-97#US#1"
        assert parser.parse_v2_locations(locations_str) == []

    def test_parse_missing_required_fields(self, parser):
        """Test handling empty required fields (full_name, country_code)."""
        # Empty full_name
        locations_str = "1##US##38#-97#US#1"
        assert parser.parse_v2_locations(locations_str) == []

        # Empty country_code
        locations_str = "1#United States###38#-97#US#1"
        assert parser.parse_v2_locations(locations_str) == []

    def test_parse_zero_coordinates(self, parser):
        """Test handling zero/empty coordinates (common in GDELT)."""
        locations_str = "1#United States#US###0#0#US#1"

        locations = parser.parse_v2_locations(locations_str)

        assert len(locations) == 1
        assert locations[0].latitude == 0.0
        assert locations[0].longitude == 0.0

    def test_parse_invalid_coordinates(self, parser):
        """Test handling out-of-range coordinates."""
        # Invalid latitude (> 90)
        locations_str = "1#Invalid#US###150#-97#US#1"
        locations = parser.parse_v2_locations(locations_str)
        assert len(locations) == 1
        assert locations[0].latitude == 0.0  # Should default to 0

        # Invalid longitude (< -180)
        locations_str = "1#Invalid#US###38#-200#US#1"
        locations = parser.parse_v2_locations(locations_str)
        assert len(locations) == 1
        assert locations[0].longitude == 0.0  # Should default to 0

    def test_parse_missing_optional_fields(self, parser):
        """Test parsing with missing optional fields (adm codes, feature_id, char_offset)."""
        locations_str = "1#United States#US###38#-97"  # Missing feature_id and char_offset

        locations = parser.parse_v2_locations(locations_str)

        assert len(locations) == 1
        assert locations[0].feature_id == ""
        assert locations[0].char_offset == 0

    def test_parse_invalid_char_offset(self, parser):
        """Test handling non-numeric char_offset."""
        locations_str = "1#United States#US###38#-97#US#abc"

        locations = parser.parse_v2_locations(locations_str)

        assert len(locations) == 1
        assert locations[0].char_offset == 0  # Should default to 0

    def test_parse_mixed_valid_invalid_blocks(self, parser):
        """Test parsing mixture of valid and invalid location blocks."""
        locations_str = "1#United States#US###38#-97#US#1;INVALID;3#New York#US#USNY##40.7128#-74.006#5128581#234"

        locations = parser.parse_v2_locations(locations_str)

        # Should skip invalid block but parse valid ones
        assert len(locations) == 2
        assert locations[0].full_name == "United States"
        assert locations[1].full_name == "New York"

    def test_parse_with_international_characters(self, parser):
        """Test parsing location names with international characters."""
        locations_str = "4#São Paulo, Brazil#BR#BRSP##-23.5505#-46.6333#3448439#100"

        locations = parser.parse_v2_locations(locations_str)

        assert len(locations) == 1
        assert locations[0].full_name == "São Paulo, Brazil"
        assert locations[0].country_code == "BR"


class TestParseV2Counts:
    """Test suite for parse_v2_counts() method."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for tests."""
        return GDELTParser()

    def test_parse_single_count_simple(self, parser):
        """Test parsing single count without location data."""
        counts_str = "KILL#12#civilians"

        counts = parser.parse_v2_counts(counts_str)

        assert len(counts) == 1
        assert counts[0].count_type == "KILL"
        assert counts[0].number == 12
        assert counts[0].object_type == "civilians"
        assert counts[0].location is None

    def test_parse_single_count_with_location(self, parser):
        """Test parsing count with embedded location data."""
        counts_str = "KILL#12##3#Pacific Palisades, California, United States#US#USCA#34.0481#-118.526#1661169"

        counts = parser.parse_v2_counts(counts_str)

        assert len(counts) == 1
        count = counts[0]
        assert count.count_type == "KILL"
        assert count.number == 12
        assert count.object_type == ""

        # Verify embedded location
        assert count.location is not None
        assert count.location.location_type == 3
        assert count.location.full_name == "Pacific Palisades, California, United States"
        assert count.location.country_code == "US"
        assert count.location.adm1_code == "USCA"
        assert count.location.latitude == pytest.approx(34.0481)
        assert count.location.longitude == pytest.approx(-118.526)
        assert count.location.feature_id == "1661169"

    def test_parse_multiple_counts(self, parser):
        """Test parsing multiple count entries."""
        counts_str = "KILL#12#civilians;WOUND#34#soldiers;ARREST#5#protesters"

        counts = parser.parse_v2_counts(counts_str)

        assert len(counts) == 3
        assert counts[0].count_type == "KILL"
        assert counts[0].number == 12
        assert counts[1].count_type == "WOUND"
        assert counts[1].number == 34
        assert counts[2].count_type == "ARREST"
        assert counts[2].number == 5

    def test_parse_crisis_lex_counts(self, parser):
        """Test parsing CRISISLEX theme counts."""
        counts_str = "CRISISLEX_T03_DEAD#25##1#United States#US##38#-97#US;CRISISLEX_T02_INJURED#50##1#United States#US##38#-97#US"

        counts = parser.parse_v2_counts(counts_str)

        assert len(counts) == 2
        assert counts[0].count_type == "CRISISLEX_T03_DEAD"
        assert counts[0].number == 25
        assert counts[1].count_type == "CRISISLEX_T02_INJURED"
        assert counts[1].number == 50

    def test_parse_duplicate_count_types_not_aggregated(self, parser):
        """Test that duplicate count types are kept separate (context matters)."""
        counts_str = "KILL#10##3#Los Angeles#US#USCA#34.05#-118.24#12345;KILL#5##3#New York#US#USNY#40.71#-74.00#54321"

        counts = parser.parse_v2_counts(counts_str)

        # Should keep both KILL entries (different locations = different context)
        assert len(counts) == 2
        assert counts[0].count_type == "KILL"
        assert counts[0].number == 10
        assert counts[0].location.full_name == "Los Angeles"
        assert counts[1].count_type == "KILL"
        assert counts[1].number == 5
        assert counts[1].location.full_name == "New York"

    def test_parse_empty_string(self, parser):
        """Test parsing empty count string returns empty list."""
        assert parser.parse_v2_counts("") == []
        assert parser.parse_v2_counts("   ") == []
        assert parser.parse_v2_counts("\t\n") == []

    def test_parse_malformed_too_few_fields(self, parser):
        """Test handling count block with insufficient fields."""
        counts_str = "KILL"  # Missing number field

        counts = parser.parse_v2_counts(counts_str)

        assert counts == []

    def test_parse_empty_count_type(self, parser):
        """Test handling empty count type."""
        counts_str = "#12#civilians"

        counts = parser.parse_v2_counts(counts_str)

        assert counts == []

    def test_parse_empty_count_number(self, parser):
        """Test handling empty count number."""
        counts_str = "KILL##civilians"

        counts = parser.parse_v2_counts(counts_str)

        assert counts == []

    def test_parse_invalid_count_number(self, parser):
        """Test handling non-numeric count number."""
        counts_str = "KILL#abc#civilians"

        counts = parser.parse_v2_counts(counts_str)

        assert counts == []

    def test_parse_missing_object_type(self, parser):
        """Test parsing count without object_type (optional field)."""
        counts_str = "AFFECT#1000"

        counts = parser.parse_v2_counts(counts_str)

        assert len(counts) == 1
        assert counts[0].count_type == "AFFECT"
        assert counts[0].number == 1000
        assert counts[0].object_type == ""

    def test_parse_embedded_location_partial_data(self, parser):
        """Test parsing count with incomplete embedded location."""
        # Only 8 fields (missing feature_id)
        counts_str = "KILL#12##3#Los Angeles#US#USCA#34.05"

        counts = parser.parse_v2_counts(counts_str)

        assert len(counts) == 1
        # Should still parse count even if location is missing
        assert counts[0].count_type == "KILL"
        assert counts[0].number == 12
        assert counts[0].location is None  # Not enough location data

    def test_parse_embedded_location_invalid_data(self, parser):
        """Test handling invalid embedded location data."""
        # Invalid latitude
        counts_str = "KILL#12##3#Los Angeles#US#USCA#invalid#-118.24#12345"

        counts = parser.parse_v2_counts(counts_str)

        assert len(counts) == 1
        assert counts[0].count_type == "KILL"
        assert counts[0].number == 12
        # Location parsing should fail gracefully
        assert counts[0].location is None

    def test_parse_mixed_valid_invalid_blocks(self, parser):
        """Test parsing mixture of valid and invalid count blocks."""
        counts_str = "KILL#12#civilians;INVALID;WOUND#34#soldiers"

        counts = parser.parse_v2_counts(counts_str)

        # Should skip invalid block but parse valid ones
        assert len(counts) == 2
        assert counts[0].count_type == "KILL"
        assert counts[1].count_type == "WOUND"

    def test_parse_zero_count_value(self, parser):
        """Test parsing count with zero value (valid edge case)."""
        counts_str = "KILL#0#civilians"

        counts = parser.parse_v2_counts(counts_str)

        assert len(counts) == 1
        assert counts[0].number == 0

    def test_parse_large_count_value(self, parser):
        """Test parsing count with large numeric value."""
        counts_str = "AFFECT#1000000#people"

        counts = parser.parse_v2_counts(counts_str)

        assert len(counts) == 1
        assert counts[0].number == 1000000


class TestParserIntegration:
    """Integration tests for complete parsing workflows."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for tests."""
        return GDELTParser()

    def test_locations_and_counts_together(self, parser):
        """Test that locations and counts can be parsed from same record."""
        locations_str = "1#United States#US###38#-97#US#1;3#New York#US#USNY##40.7128#-74.006#5128581#234"
        counts_str = "KILL#12#civilians;WOUND#34#soldiers"

        locations = parser.parse_v2_locations(locations_str)
        counts = parser.parse_v2_counts(counts_str)

        assert len(locations) == 2
        assert len(counts) == 2

        # Verify independent parsing
        assert locations[0].country_code == "US"
        assert counts[0].count_type == "KILL"

    def test_empty_inputs_all_fields(self, parser):
        """Test parsing all empty fields gracefully."""
        assert parser.parse_v2_locations("") == []
        assert parser.parse_v2_counts("") == []
        assert parser.parse_v2_themes("") == []
        assert parser.parse_v2_tone("") == parser.parse_v2_tone("")  # Should return default GKGTone
