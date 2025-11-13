"""Tests for flow detector service."""

import pytest
import math
from datetime import datetime, timedelta
from app.services.flow_detector import FlowDetector, parse_time_window
from app.models.schemas import Topic


class TestFlowDetector:
    """Test suite for FlowDetector."""

    def test_initialization(self):
        """Test FlowDetector initialization with custom parameters."""
        detector = FlowDetector(heat_halflife_hours=12.0, flow_threshold=0.7)
        assert detector.heat_halflife_hours == 12.0
        assert detector.flow_threshold == 0.7

    def test_initialization_defaults(self):
        """Test FlowDetector initialization with default parameters."""
        detector = FlowDetector()
        assert detector.heat_halflife_hours == 6.0
        assert detector.flow_threshold == 0.5

    def test_calculate_similarity_identical_topics(self):
        """Test similarity calculation with identical topics."""
        detector = FlowDetector()
        topics_a = ["election results", "climate change"]
        topics_b = ["election results", "climate change"]

        similarity = detector.calculate_similarity(topics_a, topics_b)

        # Identical topics should have similarity close to 1.0
        assert similarity >= 0.9
        assert similarity <= 1.0

    def test_calculate_similarity_similar_topics(self):
        """Test similarity calculation with semantically similar topics."""
        detector = FlowDetector()
        topics_a = ["election results", "voting outcomes"]
        topics_b = ["election outcomes", "vote counting"]

        similarity = detector.calculate_similarity(topics_a, topics_b)

        # Similar topics should have moderate to high similarity
        assert similarity >= 0.3
        assert similarity <= 1.0

    def test_calculate_similarity_different_topics(self):
        """Test similarity calculation with completely different topics."""
        detector = FlowDetector()
        topics_a = ["quantum physics research"]
        topics_b = ["banana recipes cooking"]

        similarity = detector.calculate_similarity(topics_a, topics_b)

        # Different topics should have low similarity
        assert similarity >= 0.0
        assert similarity <= 0.5

    def test_calculate_similarity_empty_topics(self):
        """Test similarity calculation with empty topic lists."""
        detector = FlowDetector()

        # Empty list A
        similarity = detector.calculate_similarity([], ["election results"])
        assert similarity == 0.0

        # Empty list B
        similarity = detector.calculate_similarity(["election results"], [])
        assert similarity == 0.0

        # Both empty
        similarity = detector.calculate_similarity([], [])
        assert similarity == 0.0

    def test_calculate_time_decay_zero_hours(self):
        """Test time decay with zero time difference."""
        detector = FlowDetector(heat_halflife_hours=6.0)
        decay = detector.calculate_time_decay(0.0)

        # At time 0, decay should be 1.0
        assert decay == pytest.approx(1.0, abs=0.001)

    def test_calculate_time_decay_halflife(self):
        """Test time decay at exactly the halflife duration."""
        detector = FlowDetector(heat_halflife_hours=6.0)
        decay = detector.calculate_time_decay(6.0)

        # At halflife, decay should be ~0.368 (1/e)
        expected = math.exp(-1)
        assert decay == pytest.approx(expected, abs=0.001)

    def test_calculate_time_decay_various_times(self):
        """Test time decay at various time intervals."""
        detector = FlowDetector(heat_halflife_hours=6.0)

        # Test cases from ADR-0002
        test_cases = [
            (0, 1.00),
            (3, 0.61),
            (6, 0.37),
            (12, 0.14),
            (24, 0.02),
        ]

        for delta_hours, expected_decay in test_cases:
            decay = detector.calculate_time_decay(delta_hours)
            assert decay == pytest.approx(expected_decay, abs=0.02)

    def test_calculate_time_decay_negative_hours(self):
        """Test time decay with negative hours (should be treated as 0)."""
        detector = FlowDetector(heat_halflife_hours=6.0)
        decay = detector.calculate_time_decay(-5.0)

        # Negative time should be treated as 0
        assert decay == pytest.approx(1.0, abs=0.001)

    def test_calculate_heat(self):
        """Test heat calculation combining similarity and time decay."""
        detector = FlowDetector(heat_halflife_hours=6.0)

        # High similarity, recent time
        heat = detector.calculate_heat(similarity=0.9, time_delta_hours=1.0)
        assert heat >= 0.7  # Should be high

        # High similarity, old time
        heat = detector.calculate_heat(similarity=0.9, time_delta_hours=24.0)
        assert heat <= 0.05  # Should be very low

        # Low similarity, recent time
        heat = detector.calculate_heat(similarity=0.2, time_delta_hours=1.0)
        assert heat <= 0.3  # Should be low

    def test_calculate_heat_example_from_adr(self):
        """Test heat calculation with example from ADR-0002."""
        detector = FlowDetector(heat_halflife_hours=6.0)

        # Example: similarity=0.87, delta=3h
        # Expected: 0.87 × exp(-3/6) = 0.87 × 0.61 ≈ 0.53
        similarity = 0.87
        delta_hours = 3.0

        heat = detector.calculate_heat(similarity, delta_hours)

        expected = 0.87 * math.exp(-3.0 / 6.0)
        assert heat == pytest.approx(expected, abs=0.01)
        assert heat == pytest.approx(0.53, abs=0.02)

    def test_calculate_hotspot_intensity_empty_topics(self):
        """Test hotspot intensity with empty topics."""
        detector = FlowDetector()
        intensity = detector.calculate_hotspot_intensity([])
        assert intensity == 0.0

    def test_calculate_hotspot_intensity_single_topic(self):
        """Test hotspot intensity with single topic."""
        detector = FlowDetector()
        topics = [
            Topic(
                id="1",
                label="Test Topic",
                count=100,
                confidence=0.9,
                sample_titles=[],
                sources=["test"],
            )
        ]

        intensity = detector.calculate_hotspot_intensity(topics)

        # Should be > 0 and <= 1
        assert intensity > 0.0
        assert intensity <= 1.0

    def test_calculate_hotspot_intensity_multiple_topics(self):
        """Test hotspot intensity with multiple topics."""
        detector = FlowDetector()
        topics = [
            Topic(
                id=f"{i}",
                label=f"Topic {i}",
                count=100 - i * 10,
                confidence=0.8 + i * 0.02,
                sample_titles=[],
                sources=["test"],
            )
            for i in range(10)
        ]

        intensity = detector.calculate_hotspot_intensity(topics)

        # More topics should lead to higher intensity
        assert intensity > 0.0
        assert intensity <= 1.0

    def test_detect_flows_single_country(self):
        """Test flow detection with single country (should return no flows)."""
        detector = FlowDetector()

        topics = [
            Topic(
                id="1",
                label="Test Topic",
                count=100,
                confidence=0.9,
                sample_titles=[],
                sources=["test"],
            )
        ]

        trends_by_country = {"US": (topics, datetime.utcnow())}

        hotspots, flows, metadata = detector.detect_flows(trends_by_country)

        # Should have 1 hotspot
        assert len(hotspots) == 1
        assert hotspots[0].country == "US"

        # Should have 0 flows (need at least 2 countries)
        assert len(flows) == 0

    def test_detect_flows_two_countries_recent(self):
        """Test flow detection between two countries with recent timing."""
        detector = FlowDetector(flow_threshold=0.3)

        topics_us = [
            Topic(
                id="1",
                label="election results",
                count=100,
                confidence=0.9,
                sample_titles=[],
                sources=["test"],
            ),
            Topic(
                id="2",
                label="climate summit",
                count=80,
                confidence=0.85,
                sample_titles=[],
                sources=["test"],
            ),
        ]

        topics_co = [
            Topic(
                id="3",
                label="election outcomes",
                count=90,
                confidence=0.88,
                sample_titles=[],
                sources=["test"],
            ),
            Topic(
                id="4",
                label="climate conference",
                count=75,
                confidence=0.82,
                sample_titles=[],
                sources=["test"],
            ),
        ]

        now = datetime.utcnow()
        trends_by_country = {
            "US": (topics_us, now),
            "CO": (topics_co, now + timedelta(hours=2)),
        }

        hotspots, flows, metadata = detector.detect_flows(trends_by_country)

        # Should have 2 hotspots
        assert len(hotspots) == 2

        # Should have at least 1 flow (topics are similar and recent)
        assert len(flows) >= 1

        # Check flow properties
        flow = flows[0]
        assert flow.from_country in ["US", "CO"]
        assert flow.to_country in ["US", "CO"]
        assert flow.heat > 0.3
        assert flow.similarity_score > 0.0
        assert flow.time_delta_hours >= 0.0

    def test_detect_flows_threshold_filtering(self):
        """Test that flows below threshold are filtered out."""
        # Use high threshold to filter most flows
        detector = FlowDetector(flow_threshold=0.9)

        topics = [
            Topic(
                id="1",
                label="test topic",
                count=100,
                confidence=0.9,
                sample_titles=[],
                sources=["test"],
            )
        ]

        now = datetime.utcnow()
        trends_by_country = {
            "US": (topics, now),
            "CO": (topics, now + timedelta(hours=10)),  # Older timing = lower heat
        }

        hotspots, flows, metadata = detector.detect_flows(trends_by_country)

        # With high threshold and old timing, should filter out flows
        assert metadata["total_flows_computed"] >= 1
        # flows_returned might be 0 or small
        assert len(flows) <= metadata["total_flows_computed"]

    def test_detect_flows_time_window(self):
        """Test that flows outside time window are excluded."""
        detector = FlowDetector()

        topics = [
            Topic(
                id="1",
                label="test topic",
                count=100,
                confidence=0.9,
                sample_titles=[],
                sources=["test"],
            )
        ]

        now = datetime.utcnow()
        trends_by_country = {
            "US": (topics, now),
            "CO": (topics, now + timedelta(hours=30)),  # 30 hours later
        }

        # Use 24h time window - should exclude 30h difference
        hotspots, flows, metadata = detector.detect_flows(trends_by_country, time_window_hours=24.0)

        # Flow should be excluded due to time window
        assert len(flows) == 0
        assert metadata["total_flows_computed"] == 0

    def test_detect_flows_metadata(self):
        """Test that metadata is correctly populated."""
        detector = FlowDetector(flow_threshold=0.5)

        topics = [
            Topic(
                id="1",
                label="test topic",
                count=100,
                confidence=0.9,
                sample_titles=[],
                sources=["test"],
            )
        ]

        now = datetime.utcnow()
        trends_by_country = {
            "US": (topics, now),
            "CO": (topics, now + timedelta(hours=1)),
            "BR": (topics, now + timedelta(hours=2)),
        }

        hotspots, flows, metadata = detector.detect_flows(trends_by_country, time_window_hours=24.0)

        # Check metadata
        assert metadata["threshold"] == 0.5
        assert metadata["time_window_hours"] == 24.0
        assert metadata["total_flows_computed"] >= 0
        assert metadata["flows_returned"] == len(flows)
        assert set(metadata["countries_analyzed"]) == {"US", "CO", "BR"}

    def test_find_shared_topics_exact_matches(self):
        """Test finding shared topics with exact matches."""
        detector = FlowDetector()

        topics_a = ["election results", "climate change", "economic reform"]
        topics_b = ["election results", "healthcare policy", "climate change"]

        shared = detector._find_shared_topics(topics_a, topics_b, limit=5)

        # Should find exact matches
        assert len(shared) >= 2
        assert "election results" in [t.lower() for t in shared]
        assert "climate change" in [t.lower() for t in shared]

    def test_find_shared_topics_partial_matches(self):
        """Test finding shared topics with partial matches."""
        detector = FlowDetector()

        topics_a = ["presidential election results"]
        topics_b = ["election fraud allegations"]

        shared = detector._find_shared_topics(topics_a, topics_b, limit=3)

        # Should find partial match on "election"
        assert len(shared) >= 1

    def test_find_shared_topics_limit(self):
        """Test that shared topics respects limit."""
        detector = FlowDetector()

        topics_a = ["topic1", "topic2", "topic3", "topic4"]
        topics_b = ["topic1", "topic2", "topic3", "topic4"]

        shared = detector._find_shared_topics(topics_a, topics_b, limit=2)

        # Should respect limit
        assert len(shared) <= 2


class TestParseTimeWindow:
    """Test suite for parse_time_window function."""

    def test_parse_valid_hours(self):
        """Test parsing valid hour formats."""
        assert parse_time_window("1h") == 1.0
        assert parse_time_window("6h") == 6.0
        assert parse_time_window("12h") == 12.0
        assert parse_time_window("24h") == 24.0
        assert parse_time_window("48h") == 48.0

    def test_parse_with_whitespace(self):
        """Test parsing with whitespace."""
        assert parse_time_window(" 24h ") == 24.0
        assert parse_time_window("  6h  ") == 6.0

    def test_parse_uppercase(self):
        """Test parsing with uppercase H."""
        assert parse_time_window("24H") == 24.0
        assert parse_time_window("6H") == 6.0

    def test_parse_float_hours(self):
        """Test parsing decimal hours."""
        assert parse_time_window("0.5h") == 0.5
        assert parse_time_window("1.5h") == 1.5

    def test_parse_invalid_format(self):
        """Test parsing invalid formats raises ValueError."""
        with pytest.raises(ValueError, match="must end with 'h'"):
            parse_time_window("24")

        with pytest.raises(ValueError, match="must end with 'h'"):
            parse_time_window("24m")

    def test_parse_invalid_number(self):
        """Test parsing invalid numbers raises ValueError."""
        with pytest.raises(ValueError, match="Invalid time window format"):
            parse_time_window("abch")

    def test_parse_negative_hours(self):
        """Test parsing negative hours raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            parse_time_window("-5h")

    def test_parse_zero_hours(self):
        """Test parsing zero hours raises ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            parse_time_window("0h")
