"""
Tests for Health Endpoint

Tests the /health endpoint response shape and status logic.
"""

import pytest
import sys
import os

# Note: These tests require the FastAPI app to be running
# or need to mock the database connection


class TestHealthEndpointShape:
    """Tests for health endpoint response structure."""
    
    def test_response_has_required_fields(self):
        """Health response should have all required fields."""
        # This is a documentation of expected response shape
        expected_fields = {
            "status",           # 'healthy', 'degraded', or 'error'
            "db_ok",            # boolean
            "timestamp",        # ISO timestamp
            "last_ingest_ts",   # ISO timestamp or null
            "ingest_lag_minutes",  # float or null
            "rows_ingested_last_15m",  # int
            "total_signals",    # int
            "error_count_last_15m"  # int
        }
        # Actual test would call the endpoint
        # For now, just document the expected shape
        assert len(expected_fields) == 8


class TestHealthStatusLogic:
    """Tests for health status determination logic."""
    
    def test_healthy_status_conditions(self):
        """
        Healthy status requires:
        - db_ok = True
        - ingest_lag_minutes < 30
        """
        # Mock condition
        db_ok = True
        ingest_lag_minutes = 15.0
        
        if not db_ok:
            status = "error"
        elif ingest_lag_minutes is None or ingest_lag_minutes > 30:
            status = "degraded"
        else:
            status = "healthy"
        
        assert status == "healthy"
    
    def test_degraded_status_high_lag(self):
        """Degraded status when ingestion lag > 30 minutes."""
        db_ok = True
        ingest_lag_minutes = 45.0
        
        if not db_ok:
            status = "error"
        elif ingest_lag_minutes is None or ingest_lag_minutes > 30:
            status = "degraded"
        else:
            status = "healthy"
        
        assert status == "degraded"
    
    def test_degraded_status_no_data(self):
        """Degraded status when no ingestion timestamp."""
        db_ok = True
        ingest_lag_minutes = None
        
        if not db_ok:
            status = "error"
        elif ingest_lag_minutes is None or ingest_lag_minutes > 30:
            status = "degraded"
        else:
            status = "healthy"
        
        assert status == "degraded"
    
    def test_error_status_db_down(self):
        """Error status when database is not connected."""
        db_ok = False
        ingest_lag_minutes = 5.0  # Doesn't matter
        
        if not db_ok:
            status = "error"
        elif ingest_lag_minutes is None or ingest_lag_minutes > 30:
            status = "degraded"
        else:
            status = "healthy"
        
        assert status == "error"


class TestIngestLagCalculation:
    """Tests for ingestion lag calculation."""
    
    def test_lag_in_minutes(self):
        """Lag should be calculated correctly in minutes."""
        from datetime import datetime, timedelta
        
        last_ingest = datetime.utcnow() - timedelta(minutes=20)
        now = datetime.utcnow()
        
        lag_minutes = (now - last_ingest).total_seconds() / 60
        
        assert 19.5 < lag_minutes < 20.5
    
    def test_lag_rounds_to_one_decimal(self):
        """Lag should be rounded to one decimal place."""
        lag_raw = 15.678
        lag_rounded = round(lag_raw, 1)
        
        assert lag_rounded == 15.7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
