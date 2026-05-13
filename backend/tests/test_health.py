"""Tests for health endpoint."""

import pytest
from fastapi.testclient import TestClient
from app.main_v2 import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint returns the current health payload."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"healthy", "degraded", "error"}
    assert "db_ok" in data
    assert "timestamp" in data


def test_health_check_content_type():
    """Test health check returns JSON content type."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
