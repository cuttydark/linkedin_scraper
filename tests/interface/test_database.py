"""Tests for interface/database.py"""
import pytest
from datetime import datetime, timezone
from interface.database import (
    Lead,
    init_db,
    create_lead,
    get_leads,
    delete_lead,
    lead_exists,
    get_engine,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture
def engine():
    """In-memory SQLite engine for tests."""
    eng = create_engine("sqlite:///:memory:")
    init_db(eng)
    return eng


@pytest.fixture
def session(engine):
    with Session(engine) as s:
        yield s


def test_create_lead(session):
    lead = create_lead(
        session,
        linkedin_url="https://linkedin.com/in/test",
        name="Test User",
        role="Engineer",
        company="Acme",
        location="Madrid",
        about="About text",
        raw_json='{"linkedin_url": "https://linkedin.com/in/test"}',
    )
    assert lead.id is not None
    assert lead.name == "Test User"
    assert lead.role == "Engineer"
    assert lead.company == "Acme"


def test_create_lead_duplicate_is_ignored(session):
    create_lead(
        session,
        linkedin_url="https://linkedin.com/in/test",
        name="Test User",
        role=None,
        company=None,
        location=None,
        about=None,
        raw_json="{}",
    )
    result = create_lead(
        session,
        linkedin_url="https://linkedin.com/in/test",
        name="Test User",
        role=None,
        company=None,
        location=None,
        about=None,
        raw_json="{}",
    )
    assert result is None
    assert len(get_leads(session)) == 1


def test_lead_exists(session):
    assert not lead_exists(session, "https://linkedin.com/in/test")
    create_lead(
        session,
        linkedin_url="https://linkedin.com/in/test",
        name="Test User",
        role=None,
        company=None,
        location=None,
        about=None,
        raw_json="{}",
    )
    assert lead_exists(session, "https://linkedin.com/in/test")


def test_get_leads_no_filter(session):
    for i in range(3):
        create_lead(
            session,
            linkedin_url=f"https://linkedin.com/in/user{i}",
            name=f"User {i}",
            role="Dev",
            company="Corp",
            location="Madrid",
            about=None,
            raw_json="{}",
        )
    leads = get_leads(session)
    assert len(leads) == 3


def test_get_leads_filter_by_name(session):
    create_lead(session, linkedin_url="https://linkedin.com/in/maria", name="Maria Garcia", role=None, company=None, location=None, about=None, raw_json="{}")
    create_lead(session, linkedin_url="https://linkedin.com/in/carlos", name="Carlos Lopez", role=None, company=None, location=None, about=None, raw_json="{}")
    leads = get_leads(session, name="maria")
    assert len(leads) == 1
    assert leads[0].name == "Maria Garcia"


def test_get_leads_filter_by_company(session):
    create_lead(session, linkedin_url="https://linkedin.com/in/a", name="A", role=None, company="Acme", location=None, about=None, raw_json="{}")
    create_lead(session, linkedin_url="https://linkedin.com/in/b", name="B", role=None, company="Beta Corp", location=None, about=None, raw_json="{}")
    leads = get_leads(session, company="acme")
    assert len(leads) == 1


def test_delete_lead(session):
    lead = create_lead(session, linkedin_url="https://linkedin.com/in/test", name="Test", role=None, company=None, location=None, about=None, raw_json="{}")
    assert delete_lead(session, lead.id) is True
    assert len(get_leads(session)) == 0


def test_delete_lead_not_found(session):
    assert delete_lead(session, 999) is False


def test_get_engine_creates_engine(tmp_path):
    from sqlalchemy.engine import Engine
    eng = get_engine(str(tmp_path / "test.db"))
    assert isinstance(eng, Engine)
