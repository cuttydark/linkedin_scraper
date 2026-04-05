# LinkedIn Scraper — Interface Design

**Date:** 2026-04-05  
**Status:** Approved  

---

## Overview

A local web application (FastAPI + HTML/JS) that wraps the existing `linkedin_scraper` library, providing a browser-based UI to search LinkedIn person profiles, save them as leads, filter/manage the collection, and export to CSV.

**Runs locally on Mac.** Single user. No authentication layer required. Starts with `python interface/app.py` and opens at `http://localhost:8000`.

---

## Architecture

### Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python async) |
| Frontend | HTML + vanilla JavaScript + CSS |
| Database | SQLite via SQLAlchemy (`leads.db`) |
| Scraping | Existing `linkedin_scraper` package (Playwright) |
| Session | Existing `session.json` file |

### File structure

```
interface/
├── app.py            # FastAPI app entry point
├── database.py       # SQLAlchemy models + SQLite setup
├── routes/
│   ├── search.py     # Scrape endpoints
│   └── leads.py      # CRUD + export endpoints
└── static/
    ├── index.html    # Single-page app shell
    ├── app.js        # Frontend logic
    └── style.css     # Styles
```

The existing `linkedin_scraper/` package is used as-is. No changes to it.

### Data flow

```
Browser (HTML + JS)
  ↓ POST /api/search · GET /api/leads · GET /api/export
FastAPI (app.py)
  ↓ scrape()              ↓ save/query
linkedin_scraper       SQLite (leads.db)
  ↓ Playwright
LinkedIn.com
```

---

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/search` | Scrape a LinkedIn profile URL, return data |
| `POST` | `/api/leads` | Save a scraped profile as a lead |
| `GET` | `/api/leads` | List leads with optional filters (name, company, role, location) |
| `DELETE` | `/api/leads/{id}` | Delete a lead |
| `GET` | `/api/export` | Download all leads (or filtered selection) as CSV |
| `GET` | `/api/session` | Check LinkedIn session status |

---

## UI — Screens

### Navigation (sidebar)
- Buscar perfiles
- Mis leads
- Exportar
- Sesión LinkedIn

### Screen 1: Buscar perfiles
- Input: LinkedIn profile URL (e.g. `https://linkedin.com/in/username`)
- "Buscar" button triggers scrape via `PersonScraper`
- Result card: Name, Role, Company, Location, + "Guardar" / "Guardado" action
- Scraping runs async; result appears when complete
- Note: keyword/company search is out of scope for v1 (not supported by existing scraper)

### Screen 2: Mis leads
- Counter: total profiles saved
- Filters: name, company, role, location (live filter)
- Table with checkboxes: Name, Role, Company, Location, Saved date, "Ver perfil" link
- Bulk actions: "Exportar selección" (CSV), "Eliminar selección"
- "Exportar CSV" button (all leads)

### Screen 3: Sesión LinkedIn
- Shows current session status (active / expired)
- Button to reload `session.json`

---

## Data Model

```python
class Lead(SQLAlchemy Base):
    id: int (PK)
    linkedin_url: str (unique)
    name: str
    headline: str | None
    location: str | None
    company: str | None        # from first experience
    role: str | None           # from first experience
    about: str | None
    skills: str | None         # JSON array stored as text
    raw_json: str              # full Person model as JSON
    saved_at: datetime
```

---

## Error Handling

- Session expired → show banner "Sesión LinkedIn expirada. Regenera session.json."
- Profile not found / private → show inline error on search result row
- Rate limit → show banner with retry suggestion
- Duplicate save → silently ignore (lead already exists)

---

## Launch

```bash
pip install fastapi uvicorn aiosqlite
python interface/app.py
# Opens http://localhost:8000
```

Requires an existing valid `session.json` in the project root (created via `python samples/create_session.py`).
