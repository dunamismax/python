# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# filename: main.py
# author: dunamismax
# version: 1.0.0
# date: 06-17-2025
# github: https://github.com/dunamismax
# description: Main application entry point for the FastAPI service.
# -----------------------------------------------------------------------------
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.app.config import settings
from src.core.logging_config import setup_logging
from src.web.routes import router as web_router

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Sets up logging on startup and yields control to the application.
    No specific cleanup is required for this simple application.

    Args:
        app: The FastAPI application instance.
    """
    setup_logging(log_level=settings.LOG_LEVEL)
    log.info("Application startup complete.", app_name=settings.APP_NAME)
    yield
    log.info("Application shutdown.")


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

# Mount static files (CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include web router for HTML/HTMX
app.include_router(web_router)
