"""
Unit tests for Trust Indicators

Tests source diversity, source quality, and normalized volume calculations.
"""

import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from indicators.source_diversity import calculate_source_diversity
from indicators.source_quality import calculate_source_quality
from indicators.normalized_volume import calculate_normalized_volume, get_volume_level


class TestSourceDiversity:
    """Tests for source diversity score calculation."""
    
    def test_empty_domains(self):
        """Empty list should return score 0."""
        result = calculate_source_diversity([])
        assert result["score"] == 0
        assert result["unique_count"] == 0
        assert result["total_signals"] == 0
    
    def test_single_domain(self):
        """Single domain should have low score (no entropy)."""
        result = calculate_source_diversity(["example.com"] * 10)
        assert result["unique_count"] == 1
        assert result["score"] < 30  # Low diversity
        assert result["total_signals"] == 10
    
    def test_many_domains_even_distribution(self):
        """Many unique domains with even distribution = high score."""
        domains = [f"source{i}.com" for i in range(20)]
        result = calculate_source_diversity(domains)
        assert result["unique_count"] == 20
        assert result["score"] > 80  # High diversity
    
    def test_many_domains_uneven_distribution(self):
        """Many domains but dominated by one = medium score."""
        domains = ["dominant.com"] * 50 + [f"source{i}.com" for i in range(10)]
        result = calculate_source_diversity(domains)
        assert result["unique_count"] == 11
        # Should be lower than even distribution due to entropy
        assert result["score"] < 70
    
    def test_case_insensitive(self):
        """Domain counting should be case-insensitive."""
        domains = ["Example.com", "EXAMPLE.COM", "example.com"]
        result = calculate_source_diversity(domains)
        assert result["unique_count"] == 1
    
    def test_top_domains_returned(self):
        """Top domains should be included in result."""
        domains = ["a.com"] * 10 + ["b.com"] * 5 + ["c.com"] * 3
        result = calculate_source_diversity(domains)
        top = result["top_domains"]
        assert len(top) > 0
        assert top[0][0] == "a.com"  # Most common first
        assert top[0][1] == 10
    
    def test_tooltip_included(self):
        """Result should include tooltip text."""
        result = calculate_source_diversity(["example.com"])
        assert "tooltip" in result
        assert len(result["tooltip"]) > 0


class TestSourceQuality:
    """Tests for source quality score calculation."""
    
    def test_empty_domains(self):
        """Empty list should return score 0."""
        result = calculate_source_quality([])
        assert result["score"] == 0
    
    def test_all_allowlisted(self):
        """All allowlisted sources should give high score."""
        result = calculate_source_quality(["reuters.com", "bbc.com", "apnews.com"])
        assert result["score"] >= 60
        assert result["allowlisted_count"] == 3
    
    def test_all_unknown(self):
        """Unknown sources should get base score only."""
        result = calculate_source_quality(["unknown-site.com"])
        assert result["score"] == 30  # Base score
        assert result["unknown_count"] == 1
        assert result["allowlisted_count"] == 0
    
    def test_mixed_sources(self):
        """Mix of allowlisted and unknown should be between extremes."""
        result = calculate_source_quality([
            "reuters.com",
            "unknown1.com",
            "unknown2.com"
        ])
        assert 30 < result["score"] < 100
        assert result["allowlisted_count"] == 1
        assert result["unknown_count"] == 2
    
    def test_max_score_capped(self):
        """Score should not exceed 100."""
        # Many allowlisted sources
        result = calculate_source_quality([
            "reuters.com", "bbc.com", "apnews.com",
            "nytimes.com", "washingtonpost.com", "theguardian.com",
            "economist.com", "ft.com", "wsj.com", "bloomberg.com"
        ])
        assert result["score"] <= 100
    
    def test_allowlisted_sources_returned(self):
        """Result should list which sources were allowlisted."""
        result = calculate_source_quality(["reuters.com", "unknown.com"])
        assert "reuters.com" in result["allowlisted_sources"]
    
    def test_case_insensitive(self):
        """Quality check should be case-insensitive."""
        result = calculate_source_quality(["REUTERS.COM", "Reuters.com"])
        assert result["allowlisted_count"] == 1  # Should dedupe


class TestNormalizedVolume:
    """Tests for normalized volume calculation."""
    
    def test_spike_detection(self):
        """High volume relative to baseline = spike."""
        result = calculate_normalized_volume(
            current_count=300,
            baseline_avg=100,
            baseline_stddev=20
        )
        assert result["multiplier"] == 3.0
        assert result["z_score"] == 10.0
        assert result["level"] == "exceptional"
    
    def test_normal_volume(self):
        """Volume near baseline = normal."""
        result = calculate_normalized_volume(
            current_count=105,
            baseline_avg=100,
            baseline_stddev=20
        )
        assert result["multiplier"] == 1.05
        assert result["level"] == "normal"
    
    def test_elevated_volume(self):
        """Moderately high volume = elevated."""
        result = calculate_normalized_volume(
            current_count=140,
            baseline_avg=100,
            baseline_stddev=20
        )
        assert result["multiplier"] == 1.4
        assert result["z_score"] == 2.0
        assert result["level"] == "high"
    
    def test_low_volume(self):
        """Volume below baseline = low."""
        result = calculate_normalized_volume(
            current_count=50,
            baseline_avg=100,
            baseline_stddev=20
        )
        assert result["multiplier"] == 0.5
        assert result["z_score"] < -1
        assert result["level"] == "low"
    
    def test_zero_baseline(self):
        """Zero baseline should return unknown level."""
        result = calculate_normalized_volume(
            current_count=100,
            baseline_avg=0,
            baseline_stddev=0
        )
        assert result["multiplier"] is None
        assert result["level"] == "unknown"
    
    def test_zero_stddev(self):
        """Zero stddev should still calculate multiplier."""
        result = calculate_normalized_volume(
            current_count=200,
            baseline_avg=100,
            baseline_stddev=0
        )
        assert result["multiplier"] == 2.0
        # z_score approximation
        assert result["z_score"] == 3
    
    def test_tooltip_included(self):
        """Result should include tooltip text."""
        result = calculate_normalized_volume(100, 100, 20)
        assert "tooltip" in result
        assert len(result["tooltip"]) > 0


class TestVolumeLevelHelper:
    """Tests for get_volume_level helper function."""
    
    def test_exceptional(self):
        assert get_volume_level(3.5) == "exceptional"
    
    def test_high(self):
        assert get_volume_level(2.5) == "high"
    
    def test_elevated(self):
        assert get_volume_level(1.5) == "elevated"
    
    def test_normal(self):
        assert get_volume_level(0.5) == "normal"
        assert get_volume_level(-0.5) == "normal"
    
    def test_low(self):
        assert get_volume_level(-2.0) == "low"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
