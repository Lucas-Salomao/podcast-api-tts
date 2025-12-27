"""
Text enhancement endpoint.
"""

import logging
from fastapi import APIRouter, Form, HTTPException

from app.models.schemas import EnhanceResponse
from app.services.enhance_service import enhance_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/enhance", response_model=EnhanceResponse)
async def enhance_text_endpoint(
    texto: str = Form(...),
):
    """
    Aprimora o texto do usuário usando IA.
    Transforma uma ideia simples em uma descrição mais rica e detalhada.
    """
    if not texto.strip():
        raise HTTPException(status_code=400, detail="Texto não pode estar vazio")
    
    logger.info(f"[API] POST /enhance - Texto: {texto[:50]}...")
    texto_aprimorado = await enhance_service.enhance_text(texto)
    
    return EnhanceResponse(
        texto_original=texto,
        texto_aprimorado=texto_aprimorado
    )
