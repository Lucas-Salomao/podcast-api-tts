"""
FastAPI Application Factory.

This module creates and configures the FastAPI application instance,
including middleware, routers, and other application-level settings.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import logger
from app.routers import health, enhance, podcast, voices
from app.db.database import create_tables, close_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("[APP] Starting up...")
    await create_tables()
    logger.info(f"[APP] {settings.APP_TITLE} v{settings.APP_VERSION} ready")
    
    yield
    
    # Shutdown
    logger.info("[APP] Shutting down...")
    await close_database()
    logger.info("[APP] Shutdown complete")


def create_app() -> FastAPI:
    """
    Creates and configures the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    # Configure CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router)
    app.include_router(enhance.router)
    app.include_router(podcast.router)
    app.include_router(voices.router)

    logger.info(f"[APP] {settings.APP_TITLE} v{settings.APP_VERSION} initialized")

    return app


# Application instance
app = create_app()
