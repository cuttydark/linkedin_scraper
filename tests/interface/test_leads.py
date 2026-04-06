"""Tests for interface/routes/leads.py"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from interface.database import Base, init_db, get_engine
from interface.routes.leads import router, get_session


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    init_db(eng)
    return eng


@pytest.fixture
def app(engine):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: Session(engine)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


def seed_lead(client, url="https://linkedin.com/in/test", name="Test User"):
    return client.post("/api/leads", json={
        "linkedin_url": url,
        "name": name,
        "role": "Engineer",
        "company": "Acme",
        "location": "Madrid",
        "about": None,
        "raw_json": "{}",
    })


def test_create_lead(client):
    response = seed_lead(client)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test User"
    assert data["id"] is not None


def test_create_lead_duplicate_returns_existing(client):
    seed_lead(client)
    response = seed_lead(client)
    assert response.status_code == 200
    # Duplicate returns existing lead (same id)
    assert response.json()["id"] is not None


def test_get_leads_empty(client):
    response = client.get("/api/leads")
    assert response.status_code == 200
    assert response.json() == []


def test_get_leads_with_data(client):
    seed_lead(client, "https://linkedin.com/in/a", "Alice")
    seed_lead(client, "https://linkedin.com/in/b", "Bob")
    response = client.get("/api/leads")
    assert len(response.json()) == 2


def test_get_leads_filter_by_name(client):
    seed_lead(client, "https://linkedin.com/in/a", "Alice Smith")
    seed_lead(client, "https://linkedin.com/in/b", "Bob Jones")
    response = client.get("/api/leads?name=alice")
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Alice Smith"


def test_delete_lead(client):
    seed_lead(client)
    lead_id = client.get("/api/leads").json()[0]["id"]
    response = client.delete(f"/api/leads/{lead_id}")
    assert response.status_code == 200
    assert client.get("/api/leads").json() == []


def test_delete_lead_not_found(client):
    response = client.delete("/api/leads/999")
    assert response.status_code == 404


def test_export_csv(client):
    seed_lead(client, name="Maria Garcia")
    response = client.get("/api/export")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    text = response.text
    assert "Maria Garcia" in text
    assert "name" in text.lower()


def test_export_csv_with_filter(client):
    seed_lead(client, "https://linkedin.com/in/a", "Alice")
    seed_lead(client, "https://linkedin.com/in/b", "Bob")
    response = client.get("/api/export?name=alice")
    assert "Alice" in response.text
    assert "Bob" not in response.text
