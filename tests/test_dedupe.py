"""
Tests for Signal Deduplication

Tests URL-based deduplication logic.
"""

import pytest
from typing import List, Dict


def deduplicate_signals(signals: List[Dict]) -> List[Dict]:
    """
    Deduplicate signals by source_url.
    
    Keeps the first occurrence of each URL.
    
    Args:
        signals: List of signal dicts with 'source_url' key
    
    Returns:
        Deduplicated list of signals
    """
    seen_urls = set()
    result = []
    
    for signal in signals:
        url = signal.get("source_url")
        if url and url not in seen_urls:
            seen_urls.add(url)
            result.append(signal)
    
    return result


class TestDeduplication:
    """Tests for signal deduplication."""
    
    def test_dedupe_by_url(self):
        """Signals with same URL should be deduplicated."""
        signals = [
            {"source_url": "https://example.com/article1", "title": "Title 1"},
            {"source_url": "https://example.com/article1", "title": "Title 1 Duplicate"},
            {"source_url": "https://example.com/article2", "title": "Title 2"},
        ]
        result = deduplicate_signals(signals)
        
        assert len(result) == 2
        urls = [s["source_url"] for s in result]
        assert "https://example.com/article1" in urls
        assert "https://example.com/article2" in urls
    
    def test_keeps_first_occurrence(self):
        """Should keep the first occurrence of duplicate URLs."""
        signals = [
            {"source_url": "https://example.com/dup", "title": "First"},
            {"source_url": "https://example.com/dup", "title": "Second"},
        ]
        result = deduplicate_signals(signals)
        
        assert len(result) == 1
        assert result[0]["title"] == "First"
    
    def test_handles_empty_list(self):
        """Empty list should return empty list."""
        result = deduplicate_signals([])
        assert result == []
    
    def test_handles_missing_url(self):
        """Signals without source_url should be excluded."""
        signals = [
            {"source_url": "https://example.com/valid", "title": "Valid"},
            {"title": "No URL"},
            {"source_url": None, "title": "Null URL"},
        ]
        result = deduplicate_signals(signals)
        
        assert len(result) == 1
        assert result[0]["title"] == "Valid"
    
    def test_url_exact_match(self):
        """URLs must match exactly (case-sensitive)."""
        signals = [
            {"source_url": "https://Example.com/article", "title": "Upper"},
            {"source_url": "https://example.com/article", "title": "Lower"},
        ]
        result = deduplicate_signals(signals)
        
        # These are different URLs
        assert len(result) == 2
    
    def test_preserves_all_fields(self):
        """Deduplication should preserve all signal fields."""
        signals = [
            {
                "source_url": "https://example.com/article",
                "title": "Title",
                "themes": ["ECONOMY", "TRADE"],
                "sentiment": -2.5
            },
        ]
        result = deduplicate_signals(signals)
        
        assert result[0]["themes"] == ["ECONOMY", "TRADE"]
        assert result[0]["sentiment"] == -2.5
    
    def test_handles_large_batch(self):
        """Should handle large batches efficiently."""
        # Create 10000 signals with 5000 duplicates
        signals = []
        for i in range(10000):
            url = f"https://example.com/article{i % 5000}"
            signals.append({"source_url": url, "title": f"Title {i}"})
        
        result = deduplicate_signals(signals)
        
        assert len(result) == 5000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
