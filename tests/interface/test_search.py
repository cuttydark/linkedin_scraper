"""Tests for interface/routes/search.py"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from interface.routes.search import router


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def app_with_browser():
    """App with mock browser state for search tests."""
    import asyncio
    app = FastAPI()
    app.include_router(router)
    app.state.browser = MagicMock()  # mock browser
    app.state.scrape_lock = asyncio.Lock()
    return app


@pytest.fixture
def client_with_browser(app_with_browser):
    return TestClient(app_with_browser)


def make_mock_person():
    person = MagicMock()
    person.name = "Maria Garcia"
    person.linkedin_url = "https://linkedin.com/in/maria"
    person.location = "Madrid"
    person.about = "Marketing professional"
    person.job_title = "Head of Marketing"
    person.company = "Acme Corp"
    person.model_dump_json.return_value = json.dumps({
        "linkedin_url": "https://linkedin.com/in/maria",
        "name": "Maria Garcia",
    })
    return person


def test_search_missing_url(client):
    response = client.post("/api/search", json={})
    assert response.status_code == 422


def test_search_invalid_url(client):
    response = client.post("/api/search", json={"url": "not-a-linkedin-url"})
    assert response.status_code == 400
    assert "linkedin.com/in/" in response.json()["detail"]


@patch("interface.routes.search.run_scrape")
def test_search_success(mock_run_scrape, client_with_browser):
    mock_run_scrape.return_value = make_mock_person()
    response = client_with_browser.post("/api/search", json={"url": "https://linkedin.com/in/maria"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Maria Garcia"
    assert data["linkedin_url"] == "https://linkedin.com/in/maria"
    assert data["role"] == "Head of Marketing"
    assert data["company"] == "Acme Corp"
    assert data["location"] == "Madrid"
    assert data["about"] == "Marketing professional"
    assert "raw_json" in data


@patch("interface.routes.search.run_scrape")
def test_search_scrape_error(mock_run_scrape, client_with_browser):
    from linkedin_scraper import RateLimitError
    mock_run_scrape.side_effect = RateLimitError("rate limited")
    response = client_with_browser.post("/api/search", json={"url": "https://linkedin.com/in/test"})
    assert response.status_code == 429


def test_session_status_no_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr("interface.routes.search.SESSION_PATH", str(tmp_path / "no-session.json"))
    response = client.get("/api/session")
    assert response.status_code == 200
    assert response.json()["status"] == "missing"
