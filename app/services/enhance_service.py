"""
Text enhancement service using Gemini LLM.
"""

import logging
from google import genai
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


ENHANCE_PROMPT = """Você é um assistente especializado em aprimorar textos para podcasts.

Seu objetivo é pegar a ideia ou tema do usuário e transformá-lo em uma descrição mais rica, detalhada e interessante para servir como base para um podcast.

## REGRAS:
1. Mantenha a essência da ideia original
2. Expanda com pontos interessantes que poderiam ser discutidos
3. Adicione contexto relevante se apropriado
4. Use português brasileiro formal mas acessível
5. O texto deve ter entre 3-5 parágrafos
6. NÃO inclua introduções como "Aqui está o texto aprimorado"
7. Vá direto ao conteúdo aprimorado

## TEXTO ORIGINAL:
{texto}

## TEXTO APRIMORADO:"""


class EnhanceService:
    """Service for enhancing text using LLM."""
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    async def enhance_text(self, texto: str) -> str:
        """
        Uses Gemini to enhance user text.
        
        Args:
            texto: The original user text
            
        Returns:
            Enhanced and expanded text
        """
        logger.info(f"[ENHANCE] Aprimorando texto: {texto[:100]}...")
        
        try:
            prompt = ENHANCE_PROMPT.format(texto=texto)
            
            response = self.client.models.generate_content(
                model=settings.LLM_MODEL,
                contents=prompt
            )
            
            if not response.text:
                logger.error("[ENHANCE] Resposta vazia do Gemini")
                raise HTTPException(status_code=500, detail="Falha ao aprimorar texto")
            
            logger.info(f"[ENHANCE] Texto aprimorado com sucesso, tamanho: {len(response.text)} chars")
            return response.text
            
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"[ENHANCE] Erro ao aprimorar texto: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao aprimorar texto: {str(e)}")


# Service instance for import
enhance_service = EnhanceService()
