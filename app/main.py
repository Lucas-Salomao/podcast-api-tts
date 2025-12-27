"""
FastAPI Application Factory.

This module creates and configures the FastAPI application instance,
including middleware, routers, and other application-level settings.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import logger
from app.routers import health, enhance, podcast, voices


def create_app() -> FastAPI:
    """
    Creates and configures the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title=settings.APP_TITLE,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION
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
