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
    is_logged_in,
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
