# LinkedIn Scraper Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local FastAPI web UI that lets you scrape LinkedIn person profiles, save them as leads, filter/manage the collection, and export to CSV.

**Architecture:** FastAPI backend wraps the existing `linkedin_scraper` package. A single BrowserManager instance is held in `app.state` for the lifetime of the server (started at boot, loads `session.json`). A SQLite database stores leads. The frontend is a single HTML page with vanilla JS.

**Tech Stack:** FastAPI, uvicorn, SQLAlchemy (sync, SQLite), httpx (test client), pytest, HTML + vanilla JS + CSS

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `interface/__init__.py` | Create | Package marker |
| `interface/database.py` | Create | SQLAlchemy Lead model + CRUD helpers |
| `interface/routes/__init__.py` | Create | Package marker |
| `interface/routes/search.py` | Create | `POST /api/search`, `GET /api/session`, `POST /api/session/reload` |
| `interface/routes/leads.py` | Create | `GET/POST /api/leads`, `DELETE /api/leads/{id}`, `GET /api/export` |
| `interface/app.py` | Create | FastAPI app, lifespan (browser start/stop), static mount, router include |
| `interface/static/index.html` | Create | Single-page HTML shell with sidebar |
| `interface/static/style.css` | Create | Styles |
| `interface/static/app.js` | Create | All client-side logic (search, leads list, filters, export) |
| `requirements.txt` | Modify | Add `fastapi`, `uvicorn[standard]`, `aiosqlite` |
| `tests/interface/__init__.py` | Create | Package marker |
| `tests/interface/test_database.py` | Create | Database CRUD unit tests |
| `tests/interface/test_search.py` | Create | Search route tests (mocked scraper) |
| `tests/interface/test_leads.py` | Create | Leads CRUD + export tests |

---

## Task 1: Add dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add new deps to requirements.txt**

Open `requirements.txt` and add after the existing lines:

```
# Web interface
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
httpx>=0.27.0
```

Note: `sqlalchemy>=2.0.0` already present. `aiosqlite` not needed — we use SQLAlchemy in sync mode.

- [ ] **Step 2: Install the new deps**

```bash
pip install fastapi "uvicorn[standard]" httpx
```

Expected: installs without errors.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat(interface): add fastapi/uvicorn/httpx dependencies"
```

---

## Task 2: Database model and CRUD

**Files:**
- Create: `interface/__init__.py`
- Create: `interface/database.py`
- Create: `tests/interface/__init__.py`
- Create: `tests/interface/test_database.py`

- [ ] **Step 1: Create package markers**

Create `interface/__init__.py` (empty file):
```python
```

Create `tests/interface/__init__.py` (empty file):
```python
```

- [ ] **Step 2: Write the failing tests**

Create `tests/interface/test_database.py`:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd /Users/cuttydark/emdash-projects/worktrees/eight-baths-film-58k
pytest tests/interface/test_database.py -v
```

Expected: `ModuleNotFoundError: No module named 'interface'` or similar.

- [ ] **Step 4: Create `interface/database.py`**

```python
"""SQLAlchemy Lead model and CRUD helpers for the web interface."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Text, DateTime, create_engine, Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session


class Base(DeclarativeBase):
    pass


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    linkedin_url: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(200))
    role: Mapped[Optional[str]] = mapped_column(String(200))
    company: Mapped[Optional[str]] = mapped_column(String(200))
    location: Mapped[Optional[str]] = mapped_column(String(200))
    about: Mapped[Optional[str]] = mapped_column(Text)
    raw_json: Mapped[str] = mapped_column(Text, nullable=False)
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "linkedin_url": self.linkedin_url,
            "name": self.name,
            "role": self.role,
            "company": self.company,
            "location": self.location,
            "about": self.about,
            "saved_at": self.saved_at.isoformat() if self.saved_at else None,
        }


def get_engine(db_path: str = "leads.db") -> Engine:
    return create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def create_lead(
    session: Session,
    *,
    linkedin_url: str,
    name: Optional[str],
    role: Optional[str],
    company: Optional[str],
    location: Optional[str],
    about: Optional[str],
    raw_json: str,
) -> Optional[Lead]:
    """Create a lead. Returns None if linkedin_url already exists (duplicate ignored)."""
    if lead_exists(session, linkedin_url):
        return None
    lead = Lead(
        linkedin_url=linkedin_url,
        name=name,
        role=role,
        company=company,
        location=location,
        about=about,
        raw_json=raw_json,
        saved_at=datetime.now(timezone.utc),
    )
    session.add(lead)
    session.commit()
    session.refresh(lead)
    return lead


def get_leads(
    session: Session,
    *,
    name: Optional[str] = None,
    company: Optional[str] = None,
    role: Optional[str] = None,
    location: Optional[str] = None,
) -> list[Lead]:
    """List leads with optional case-insensitive filters."""
    query = session.query(Lead)
    if name:
        query = query.filter(Lead.name.ilike(f"%{name}%"))
    if company:
        query = query.filter(Lead.company.ilike(f"%{company}%"))
    if role:
        query = query.filter(Lead.role.ilike(f"%{role}%"))
    if location:
        query = query.filter(Lead.location.ilike(f"%{location}%"))
    return query.order_by(Lead.saved_at.desc()).all()


def lead_exists(session: Session, linkedin_url: str) -> bool:
    return session.query(Lead).filter_by(linkedin_url=linkedin_url).first() is not None


def delete_lead(session: Session, lead_id: int) -> bool:
    lead = session.get(Lead, lead_id)
    if not lead:
        return False
    session.delete(lead)
    session.commit()
    return True
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/interface/test_database.py -v
```

Expected: all 8 tests pass.

- [ ] **Step 6: Commit**

```bash
git add interface/__init__.py interface/database.py tests/interface/__init__.py tests/interface/test_database.py
git commit -m "feat(interface): add Lead database model and CRUD helpers"
```

---

## Task 3: Search route

**Files:**
- Create: `interface/routes/__init__.py`
- Create: `interface/routes/search.py`
- Create: `tests/interface/test_search.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/interface/test_search.py`:

```python
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
def test_search_success(mock_run_scrape, client):
    mock_run_scrape.return_value = make_mock_person()
    response = client.post("/api/search", json={"url": "https://linkedin.com/in/maria"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Maria Garcia"
    assert data["linkedin_url"] == "https://linkedin.com/in/maria"
    assert data["role"] == "Head of Marketing"
    assert data["company"] == "Acme Corp"


@patch("interface.routes.search.run_scrape")
def test_search_scrape_error(mock_run_scrape, client):
    from linkedin_scraper import RateLimitError
    mock_run_scrape.side_effect = RateLimitError("rate limited")
    response = client.post("/api/search", json={"url": "https://linkedin.com/in/test"})
    assert response.status_code == 429


def test_session_status_no_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr("interface.routes.search.SESSION_PATH", str(tmp_path / "no-session.json"))
    response = client.get("/api/session")
    assert response.status_code == 200
    assert response.json()["status"] == "missing"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/interface/test_search.py -v
```

Expected: `ModuleNotFoundError: No module named 'interface.routes'`.

- [ ] **Step 3: Create package marker**

Create `interface/routes/__init__.py` (empty):
```python
```

- [ ] **Step 4: Create `interface/routes/search.py`**

```python
"""Search and session routes."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from linkedin_scraper import (
    BrowserManager,
    PersonScraper,
    AuthenticationError,
    RateLimitError,
    ProfileNotFoundError,
)

logger = logging.getLogger(__name__)
router = APIRouter()

SESSION_PATH = "session.json"


class SearchRequest(BaseModel):
    url: str


class SearchResult(BaseModel):
    linkedin_url: str
    name: Optional[str]
    role: Optional[str]
    company: Optional[str]
    location: Optional[str]
    about: Optional[str]
    raw_json: str


async def run_scrape(url: str, browser: BrowserManager):
    """Run PersonScraper using the shared browser. Caller must hold the scrape lock."""
    scraper = PersonScraper(browser.page)
    return await scraper.scrape(url)


@router.post("/api/search", response_model=SearchResult)
async def search(body: SearchRequest, request: Request):
    if "linkedin.com/in/" not in body.url:
        raise HTTPException(status_code=400, detail="URL must contain linkedin.com/in/")

    browser: Optional[BrowserManager] = getattr(request.app.state, "browser", None)
    lock: Optional[asyncio.Lock] = getattr(request.app.state, "scrape_lock", None)

    if browser is None or lock is None:
        raise HTTPException(status_code=503, detail="Browser not initialized. Check session.json.")

    try:
        async with lock:
            person = await run_scrape(body.url, browser)
    except RateLimitError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except AuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except ProfileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Scrape error: {e}")
        raise HTTPException(status_code=500, detail=f"Scrape failed: {e}")

    return SearchResult(
        linkedin_url=person.linkedin_url,
        name=person.name,
        role=person.job_title,
        company=person.company,
        location=person.location,
        about=person.about,
        raw_json=person.model_dump_json(),
    )


@router.get("/api/session")
async def session_status(request: Request):
    path = Path(getattr(request.app.state, "session_path", SESSION_PATH))
    if not path.exists():
        return {"status": "missing", "message": "session.json not found. Run samples/create_session.py."}

    browser: Optional[BrowserManager] = getattr(request.app.state, "browser", None)
    if browser is None:
        return {"status": "error", "message": "Browser not started."}

    from linkedin_scraper import is_logged_in
    try:
        logged_in = await is_logged_in(browser.page)
    except Exception:
        logged_in = False

    return {
        "status": "active" if logged_in else "expired",
        "session_file": str(path),
    }


@router.post("/api/session/reload")
async def reload_session(request: Request):
    browser: Optional[BrowserManager] = getattr(request.app.state, "browser", None)
    path = getattr(request.app.state, "session_path", SESSION_PATH)

    if browser is None:
        raise HTTPException(status_code=503, detail="Browser not running.")
    if not Path(path).exists():
        raise HTTPException(status_code=404, detail="session.json not found.")

    try:
        await browser.load_session(path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reload session: {e}")

    return {"status": "reloaded"}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/interface/test_search.py -v
```

Expected: all 5 tests pass.

- [ ] **Step 6: Commit**

```bash
git add interface/routes/__init__.py interface/routes/search.py tests/interface/test_search.py
git commit -m "feat(interface): add search and session routes"
```

---

## Task 4: Leads route (CRUD + export)

**Files:**
- Create: `interface/routes/leads.py`
- Create: `tests/interface/test_leads.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/interface/test_leads.py`:

```python
"""Tests for interface/routes/leads.py"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from interface.database import Base, init_db, get_engine
from interface.routes.leads import router, get_session


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/interface/test_leads.py -v
```

Expected: `ImportError: cannot import name 'router' from 'interface.routes.leads'`.

- [ ] **Step 3: Create `interface/routes/leads.py`**

```python
"""Leads CRUD and export routes."""

from __future__ import annotations

import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from interface.database import (
    get_engine,
    init_db,
    create_lead,
    get_leads,
    delete_lead,
    Lead,
)

router = APIRouter()

# Module-level engine (overridden in tests via dependency injection)
_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        _engine = get_engine()
        init_db(_engine)
    return _engine


def get_session():
    """FastAPI dependency that yields a database session."""
    with Session(_get_engine()) as session:
        yield session


class LeadIn(BaseModel):
    linkedin_url: str
    name: Optional[str]
    role: Optional[str]
    company: Optional[str]
    location: Optional[str]
    about: Optional[str]
    raw_json: str


class LeadOut(BaseModel):
    id: int
    linkedin_url: str
    name: Optional[str]
    role: Optional[str]
    company: Optional[str]
    location: Optional[str]
    about: Optional[str]
    saved_at: Optional[str]


@router.post("/api/leads", response_model=LeadOut)
def save_lead(body: LeadIn, session: Session = Depends(get_session)):
    lead = create_lead(
        session,
        linkedin_url=body.linkedin_url,
        name=body.name,
        role=body.role,
        company=body.company,
        location=body.location,
        about=body.about,
        raw_json=body.raw_json,
    )
    if lead is None:
        # Duplicate — return existing
        lead = session.query(Lead).filter_by(linkedin_url=body.linkedin_url).first()
    return LeadOut(**lead.to_dict())


@router.get("/api/leads", response_model=list[LeadOut])
def list_leads(
    name: Optional[str] = None,
    company: Optional[str] = None,
    role: Optional[str] = None,
    location: Optional[str] = None,
    session: Session = Depends(get_session),
):
    leads = get_leads(session, name=name, company=company, role=role, location=location)
    return [LeadOut(**l.to_dict()) for l in leads]


@router.delete("/api/leads/{lead_id}")
def remove_lead(lead_id: int, session: Session = Depends(get_session)):
    if not delete_lead(session, lead_id):
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"deleted": lead_id}


@router.get("/api/export")
def export_csv(
    name: Optional[str] = None,
    company: Optional[str] = None,
    role: Optional[str] = None,
    location: Optional[str] = None,
    session: Session = Depends(get_session),
):
    leads = get_leads(session, name=name, company=company, role=role, location=location)

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=["id", "name", "role", "company", "location", "linkedin_url", "about", "saved_at"],
    )
    writer.writeheader()
    for lead in leads:
        d = lead.to_dict()
        writer.writerow({k: d.get(k, "") or "" for k in writer.fieldnames})

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/interface/test_leads.py -v
```

Expected: all 10 tests pass.

- [ ] **Step 5: Commit**

```bash
git add interface/routes/leads.py tests/interface/test_leads.py
git commit -m "feat(interface): add leads CRUD and CSV export routes"
```

---

## Task 5: FastAPI app entry point

**Files:**
- Create: `interface/app.py`

- [ ] **Step 1: Create `interface/app.py`**

```python
"""FastAPI application entry point for the LinkedIn Scraper web interface."""

from __future__ import annotations

import asyncio
import logging
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from linkedin_scraper import BrowserManager
from interface.routes.search import router as search_router
from interface.routes.leads import router as leads_router

logger = logging.getLogger(__name__)

SESSION_PATH = "session.json"
STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start browser on boot, shut down on exit."""
    app.state.scrape_lock = asyncio.Lock()
    app.state.session_path = SESSION_PATH

    browser = BrowserManager(headless=True)
    await browser.start()
    app.state.browser = browser

    if Path(SESSION_PATH).exists():
        try:
            await browser.load_session(SESSION_PATH)
            logger.info(f"Session loaded from {SESSION_PATH}")
        except Exception as e:
            logger.warning(f"Could not load session: {e}. Use /api/session/reload after fixing session.json.")
    else:
        logger.warning(f"No {SESSION_PATH} found. Scraping will fail until a session is created.")

    yield

    await browser.close()
    logger.info("Browser closed")


def create_app() -> FastAPI:
    app = FastAPI(title="LinkedIn Scraper", lifespan=lifespan)
    app.include_router(search_router)
    app.include_router(leads_router)
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
    return app


app = create_app()


if __name__ == "__main__":
    webbrowser.open("http://localhost:8000")
    uvicorn.run(
        "interface.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info",
    )
```

- [ ] **Step 2: Verify the app starts (without a session)**

```bash
cd /Users/cuttydark/emdash-projects/worktrees/eight-baths-film-58k
python -c "from interface.app import create_app; app = create_app(); print('OK')"
```

Expected: `OK` (import succeeds, no errors).

- [ ] **Step 3: Commit**

```bash
git add interface/app.py
git commit -m "feat(interface): add FastAPI app with browser lifespan management"
```

---

## Task 6: Frontend (HTML + CSS + JS)

**Files:**
- Create: `interface/static/index.html`
- Create: `interface/static/style.css`
- Create: `interface/static/app.js`

- [ ] **Step 1: Create `interface/static/style.css`**

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #f8fafc;
  color: #1e293b;
  height: 100vh;
  display: flex;
}

/* Sidebar */
#sidebar {
  width: 200px;
  background: #1a1f2e;
  padding: 24px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
}

#sidebar .logo {
  color: #e2e8f0;
  font-size: 13px;
  font-weight: 700;
  padding: 8px 12px 16px;
  border-bottom: 1px solid #2d3748;
  margin-bottom: 8px;
}

#sidebar .nav-item {
  color: #94a3b8;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s;
}

#sidebar .nav-item:hover { background: #2d3748; color: #e2e8f0; }
#sidebar .nav-item.active { background: #3b5bdb; color: white; font-weight: 600; }

#sidebar .nav-bottom {
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid #2d3748;
}

/* Main */
#main {
  flex: 1;
  padding: 28px 32px;
  overflow-y: auto;
}

.screen { display: none; }
.screen.active { display: block; }

h2 { font-size: 20px; font-weight: 700; margin-bottom: 20px; }

/* Banner */
.banner {
  padding: 10px 16px;
  border-radius: 6px;
  font-size: 13px;
  margin-bottom: 16px;
  display: none;
}
.banner.error { background: #fee2e2; color: #dc2626; display: block; }
.banner.warning { background: #fef3c7; color: #92400e; display: block; }
.banner.success { background: #dcfce7; color: #16a34a; display: block; }

/* Search */
.search-bar { display: flex; gap: 8px; margin-bottom: 20px; }
.search-bar input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
  background: white;
}
.search-bar input:focus { outline: none; border-color: #3b5bdb; }

.btn {
  padding: 10px 20px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: opacity 0.15s;
}
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: #3b5bdb; color: white; }
.btn-primary:hover:not(:disabled) { background: #3451c7; }
.btn-success { background: #16a34a; color: white; }
.btn-success:hover:not(:disabled) { background: #15803d; }
.btn-danger { background: #dc2626; color: white; }
.btn-sm { padding: 5px 12px; font-size: 12px; }

/* Result card */
#result-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 20px;
  display: none;
}
#result-card .person-name { font-size: 16px; font-weight: 700; margin-bottom: 4px; }
#result-card .person-meta { font-size: 13px; color: #64748b; margin-bottom: 12px; }
#result-card .person-about { font-size: 13px; color: #475569; margin-bottom: 16px; }

/* Leads table */
.filters { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.filters input {
  padding: 7px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 12px;
  background: white;
  min-width: 120px;
}
.filters input:focus { outline: none; border-color: #3b5bdb; }

.leads-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.leads-count { font-size: 13px; color: #94a3b8; margin-left: 8px; }

table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; }
thead th { padding: 11px 14px; font-size: 11px; font-weight: 700; color: #94a3b8; text-align: left; letter-spacing: 0.5px; border-bottom: 1px solid #f1f5f9; }
tbody td { padding: 11px 14px; font-size: 13px; border-bottom: 1px solid #f8fafc; }
tbody tr:last-child td { border-bottom: none; }
tbody tr:hover { background: #fafafa; }

.badge-saved { background: #e0f2fe; color: #0369a1; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }

/* Bulk actions */
#bulk-actions { font-size: 12px; color: #64748b; margin-top: 10px; display: none; }
#bulk-actions span { color: #1e293b; font-weight: 600; }
#bulk-actions a { color: #3b5bdb; cursor: pointer; margin-left: 8px; }
#bulk-actions a.danger { color: #dc2626; }

/* Session screen */
.session-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 24px;
  max-width: 480px;
}
.status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 8px; }
.status-dot.active { background: #16a34a; }
.status-dot.expired, .status-dot.missing, .status-dot.error { background: #dc2626; }
.session-info { font-size: 13px; color: #64748b; margin: 12px 0; }

/* Spinner */
.spinner { display: inline-block; width: 14px; height: 14px; border: 2px solid #cbd5e1; border-top-color: #3b5bdb; border-radius: 50%; animation: spin 0.6s linear infinite; margin-right: 8px; vertical-align: middle; }
@keyframes spin { to { transform: rotate(360deg); } }
```

- [ ] **Step 2: Create `interface/static/index.html`**

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>LinkedIn Scraper</title>
  <link rel="stylesheet" href="/style.css" />
</head>
<body>

<nav id="sidebar">
  <div class="logo">LinkedIn Scraper</div>
  <div class="nav-item active" data-screen="search">Buscar perfiles</div>
  <div class="nav-item" data-screen="leads">Mis leads</div>
  <div class="nav-bottom">
    <div class="nav-item" data-screen="session">Sesion LinkedIn</div>
  </div>
</nav>

<main id="main">

  <!-- Search screen -->
  <div id="screen-search" class="screen active">
    <h2>Buscar perfiles</h2>
    <div id="search-banner" class="banner"></div>
    <div class="search-bar">
      <input type="text" id="search-url" placeholder="https://linkedin.com/in/username" />
      <button class="btn btn-primary" id="btn-search" onclick="doSearch()">Buscar</button>
    </div>
    <div id="result-card">
      <div class="person-name" id="r-name"></div>
      <div class="person-meta" id="r-meta"></div>
      <div class="person-about" id="r-about"></div>
      <button class="btn btn-success btn-sm" id="btn-save" onclick="doSave()">Guardar como lead</button>
    </div>
  </div>

  <!-- Leads screen -->
  <div id="screen-leads" class="screen">
    <div class="leads-header">
      <div>
        <h2 style="display:inline">Mis leads</h2>
        <span class="leads-count" id="leads-count"></span>
      </div>
      <button class="btn btn-success btn-sm" onclick="exportLeads()">Exportar CSV</button>
    </div>
    <div id="leads-banner" class="banner"></div>
    <div class="filters">
      <input type="text" id="f-name" placeholder="Nombre..." oninput="loadLeads()" />
      <input type="text" id="f-company" placeholder="Empresa..." oninput="loadLeads()" />
      <input type="text" id="f-role" placeholder="Cargo..." oninput="loadLeads()" />
      <input type="text" id="f-location" placeholder="Ubicacion..." oninput="loadLeads()" />
    </div>
    <table>
      <thead>
        <tr>
          <th><input type="checkbox" id="chk-all" onchange="toggleAll(this)" /></th>
          <th>NOMBRE</th>
          <th>CARGO</th>
          <th>EMPRESA</th>
          <th>UBICACION</th>
          <th>GUARDADO</th>
          <th></th>
        </tr>
      </thead>
      <tbody id="leads-body"></tbody>
    </table>
    <div id="bulk-actions">
      <span id="bulk-count">0</span> seleccionados —
      <a onclick="exportSelected()">Exportar seleccion</a>
      <a class="danger" onclick="deleteSelected()">Eliminar seleccion</a>
    </div>
  </div>

  <!-- Session screen -->
  <div id="screen-session" class="screen">
    <h2>Sesion LinkedIn</h2>
    <div class="session-card">
      <div id="session-status-line" style="font-size:14px;font-weight:600;margin-bottom:8px;"></div>
      <div class="session-info" id="session-info"></div>
      <button class="btn btn-primary btn-sm" onclick="reloadSession()">Recargar session.json</button>
    </div>
  </div>

</main>

<script src="/app.js"></script>
</body>
</html>
```

- [ ] **Step 3: Create `interface/static/app.js`**

```javascript
// State
let currentPerson = null;
let selectedIds = new Set();

// Navigation
document.querySelectorAll('.nav-item[data-screen]').forEach(item => {
  item.addEventListener('click', () => {
    const screen = item.dataset.screen;
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    item.classList.add('active');
    document.getElementById('screen-' + screen).classList.add('active');
    if (screen === 'leads') loadLeads();
    if (screen === 'session') loadSessionStatus();
  });
});

// -- SEARCH --

async function doSearch() {
  const url = document.getElementById('search-url').value.trim();
  if (!url) return;

  const btn = document.getElementById('btn-search');
  const banner = document.getElementById('search-banner');
  const card = document.getElementById('result-card');

  setBanner(banner, null);
  card.style.display = 'none';
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Buscando...';

  try {
    const res = await fetch('/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });

    const data = await res.json();

    if (!res.ok) {
      const msg = res.status === 429
        ? 'LinkedIn esta limitando las peticiones. Espera unos minutos.'
        : res.status === 401
        ? 'Sesion expirada. Ve a "Sesion LinkedIn" y recarga session.json.'
        : res.status === 404
        ? 'Perfil no encontrado o privado.'
        : data.detail || 'Error al buscar el perfil.';
      setBanner(banner, msg, 'error');
      return;
    }

    currentPerson = data;
    document.getElementById('r-name').textContent = data.name || '(sin nombre)';
    document.getElementById('r-meta').textContent = [data.role, data.company, data.location].filter(Boolean).join(' · ');
    document.getElementById('r-about').textContent = data.about ? data.about.slice(0, 200) + (data.about.length > 200 ? '...' : '') : '';
    card.style.display = 'block';

    const saveBtn = document.getElementById('btn-save');
    saveBtn.textContent = 'Guardar como lead';
    saveBtn.disabled = false;

  } catch (e) {
    setBanner(banner, 'Error de red. Asegurate de que la app está corriendo.', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Buscar';
  }
}

async function doSave() {
  if (!currentPerson) return;

  const btn = document.getElementById('btn-save');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span>Guardando...';

  try {
    const res = await fetch('/api/leads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(currentPerson),
    });

    if (res.ok) {
      btn.textContent = 'Guardado';
      btn.style.background = '#0369a1';
    } else {
      btn.disabled = false;
      btn.textContent = 'Guardar como lead';
    }
  } catch (e) {
    btn.disabled = false;
    btn.textContent = 'Guardar como lead';
  }
}

document.getElementById('search-url').addEventListener('keydown', e => {
  if (e.key === 'Enter') doSearch();
});

// -- LEADS --

async function loadLeads() {
  const name = document.getElementById('f-name').value;
  const company = document.getElementById('f-company').value;
  const role = document.getElementById('f-role').value;
  const location = document.getElementById('f-location').value;

  const params = new URLSearchParams();
  if (name) params.set('name', name);
  if (company) params.set('company', company);
  if (role) params.set('role', role);
  if (location) params.set('location', location);

  const res = await fetch('/api/leads?' + params.toString());
  const leads = await res.json();

  selectedIds.clear();
  updateBulkActions();

  document.getElementById('leads-count').textContent = leads.length + ' perfiles';
  const tbody = document.getElementById('leads-body');
  tbody.innerHTML = '';

  if (leads.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#94a3b8;padding:24px;">No hay leads guardados.</td></tr>';
    return;
  }

  leads.forEach(lead => {
    const tr = document.createElement('tr');
    const date = lead.saved_at ? new Date(lead.saved_at).toLocaleDateString('es-ES', { day: '2-digit', month: 'short' }) : '';
    tr.innerHTML = `
      <td><input type="checkbox" data-id="${lead.id}" onchange="toggleSelect(${lead.id}, this)" /></td>
      <td style="font-weight:600">${esc(lead.name || '')}</td>
      <td style="color:#64748b">${esc(lead.role || '')}</td>
      <td style="color:#64748b">${esc(lead.company || '')}</td>
      <td style="color:#94a3b8;font-size:12px">${esc(lead.location || '')}</td>
      <td style="color:#94a3b8;font-size:12px">${date}</td>
      <td><a href="${esc(lead.linkedin_url)}" target="_blank" style="color:#3b5bdb;font-size:12px;text-decoration:none">Ver perfil</a></td>
    `;
    tbody.appendChild(tr);
  });
}

function toggleSelect(id, chk) {
  if (chk.checked) selectedIds.add(id);
  else selectedIds.delete(id);
  updateBulkActions();
}

function toggleAll(chk) {
  document.querySelectorAll('#leads-body input[type=checkbox]').forEach(c => {
    c.checked = chk.checked;
    const id = parseInt(c.dataset.id);
    if (chk.checked) selectedIds.add(id);
    else selectedIds.delete(id);
  });
  updateBulkActions();
}

function updateBulkActions() {
  const el = document.getElementById('bulk-actions');
  if (selectedIds.size > 0) {
    el.style.display = 'block';
    document.getElementById('bulk-count').textContent = selectedIds.size;
  } else {
    el.style.display = 'none';
  }
}

async function deleteSelected() {
  if (selectedIds.size === 0) return;
  if (!confirm(`Eliminar ${selectedIds.size} lead(s)?`)) return;
  await Promise.all([...selectedIds].map(id => fetch('/api/leads/' + id, { method: 'DELETE' })));
  loadLeads();
}

function exportLeads() {
  const params = new URLSearchParams();
  const name = document.getElementById('f-name').value;
  const company = document.getElementById('f-company').value;
  const role = document.getElementById('f-role').value;
  const location = document.getElementById('f-location').value;
  if (name) params.set('name', name);
  if (company) params.set('company', company);
  if (role) params.set('role', role);
  if (location) params.set('location', location);
  window.location.href = '/api/export?' + params.toString();
}

async function exportSelected() {
  // Build a mini-CSV client-side from selected rows
  const rows = [...document.querySelectorAll('#leads-body tr')];
  const selected = rows.filter(r => r.querySelector('input[type=checkbox]')?.checked);
  const ids = selected.map(r => parseInt(r.querySelector('input').dataset.id));

  // Fetch all then filter
  const res = await fetch('/api/leads');
  const all = await res.json();
  const filtered = all.filter(l => ids.includes(l.id));

  const header = 'name,role,company,location,linkedin_url,saved_at\n';
  const lines = filtered.map(l =>
    [l.name, l.role, l.company, l.location, l.linkedin_url, l.saved_at].map(v => `"${(v || '').replace(/"/g, '""')}"`).join(',')
  ).join('\n');

  const blob = new Blob([header + lines], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'leads-seleccion.csv';
  a.click();
  URL.revokeObjectURL(url);
}

// -- SESSION --

async function loadSessionStatus() {
  const res = await fetch('/api/session');
  const data = await res.json();
  const line = document.getElementById('session-status-line');
  const info = document.getElementById('session-info');
  const dot = `<span class="status-dot ${data.status}"></span>`;
  const labels = { active: 'Activa', expired: 'Expirada', missing: 'Sin sesion', error: 'Error' };
  line.innerHTML = dot + (labels[data.status] || data.status);
  info.textContent = data.message || (data.session_file ? 'Archivo: ' + data.session_file : '');
}

async function reloadSession() {
  const res = await fetch('/api/session/reload', { method: 'POST' });
  await loadSessionStatus();
}

// -- UTILS --

function setBanner(el, msg, type) {
  el.className = 'banner';
  el.textContent = '';
  if (msg) {
    el.classList.add(type || 'error');
    el.textContent = msg;
  }
}

function esc(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
```

- [ ] **Step 4: Run all tests to make sure nothing broke**

```bash
pytest tests/interface/ -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add interface/static/
git commit -m "feat(interface): add HTML/CSS/JS frontend"
```

---

## Task 7: Smoke test — launch the app

- [ ] **Step 1: Run the full test suite**

```bash
pytest tests/interface/ -v --tb=short
```

Expected: all tests green.

- [ ] **Step 2: Start the app (requires a valid session.json)**

```bash
python -m interface.app
```

Or:

```bash
python interface/app.py
```

Expected: browser opens at `http://localhost:8000`. Sidebar shows "Buscar perfiles" active.

- [ ] **Step 3: Test the search flow manually**

1. Paste a LinkedIn profile URL in the search box.
2. Click "Buscar" — spinner appears, then result card shows name/role/company.
3. Click "Guardar como lead" — button changes to "Guardado".
4. Click "Mis leads" in sidebar — lead appears in table.
5. Click "Exportar CSV" — browser downloads `leads.csv`.

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat(interface): complete LinkedIn Scraper web interface v1"
```
