"""
Voices listing endpoint.
"""

from fastapi import APIRouter

from app.models.voices import VOZES_LISTA

router = APIRouter()


@router.get("/vozes")
async def list_voices():
    """
    Lista todas as vozes disponíveis do Gemini TTS.
    """
    return {"vozes": VOZES_LISTA}
