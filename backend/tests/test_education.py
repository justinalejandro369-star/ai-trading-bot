"""
Tests for education API endpoints.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=True)


class TestEducationConcepts:
    def test_list_concepts_returns_all(self):
        resp = client.get("/api/education/concepts")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 5
        slugs = [item["slug"] for item in data]
        assert "rsi" in slugs
        assert "macd" in slugs
        assert "bollinger-bands" in slugs
        assert "adx" in slugs
        assert "atr" in slugs

    def test_get_concept_rsi(self):
        resp = client.get("/api/education/concepts/rsi")
        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == "rsi"
        assert "RSI" in data["name"]
        assert "explanation" in data
        assert "thresholds" in data
        assert "how_we_use_it" in data
        assert data["thresholds"]["oversold"] == 30
        assert data["thresholds"]["overbought"] == 70

    def test_get_concept_macd(self):
        resp = client.get("/api/education/concepts/macd")
        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == "macd"
        assert "MACD" in data["name"]

    def test_get_concept_bollinger_bands(self):
        resp = client.get("/api/education/concepts/bollinger-bands")
        assert resp.status_code == 200
        data = resp.json()
        assert data["slug"] == "bollinger-bands"

    def test_get_concept_not_found(self):
        resp = client.get("/api/education/concepts/nonexistent-concept")
        assert resp.status_code == 404

    def test_each_concept_has_required_fields(self):
        resp = client.get("/api/education/concepts")
        assert resp.status_code == 200
        for concept in resp.json():
            assert "slug" in concept
            assert "name" in concept
            assert "short" in concept
            assert "explanation" in concept
            assert "category" in concept
