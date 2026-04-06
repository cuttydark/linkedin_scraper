"""FastAPI application entry point for the LinkedIn Scraper web interface."""

from __future__ import annotations

import asyncio
import logging
import threading
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

# Absolute path so the app works regardless of working directory
SESSION_PATH = str(Path(__file__).parent.parent / "session.json")
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
    logging.basicConfig(level=logging.INFO)
    # Delay browser open until server has time to start
    threading.Timer(2.5, lambda: webbrowser.open("http://localhost:8000")).start()
    uvicorn.run(
        "interface.app:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info",
    )
