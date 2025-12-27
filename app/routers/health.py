"""
Health check endpoint.
"""

import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def root():
    """Health check endpoint"""
    logger.debug("[API] Health check chamado")
    return {"status": "ok", "message": "Podcast Generator API"}
