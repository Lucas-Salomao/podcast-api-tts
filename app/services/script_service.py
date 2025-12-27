"""
Podcast script generation service using Gemini LLM.
Includes TTS markup tags and style instructions for enhanced audio quality.
"""

import logging
from google import genai
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


SCRIPT_GENERATOR_PROMPT = """Você é um roteirista especializado em criar scripts de podcast em português brasileiro, otimizados para síntese de voz (TTS).

Seu objetivo é criar um diálogo natural e envolvente entre {num_hosts} participante(s) discutindo o tema fornecido pelo usuário.

## REGRAS DE FORMATO:
1. O script deve ter aproximadamente {duracao} minutos de duração quando lido em voz alta
2. Use o formato EXATO:
{speakers_format}
3. NÃO use nomes, apenas "Speaker 1", "Speaker 2"
4. Escreva em português brasileiro natural e coloquial

## REGRAS DE CONTEÚDO:
1. Inclua:
   - Uma introdução ao tema
   - Discussão dos pontos principais
   - Exemplos práticos quando relevante
   - Uma conclusão
2. Evite jargões técnicos excessivos
3. Mantenha um tom conversacional e amigável
4. Distribua as falas de forma equilibrada entre todos os participantes
5. Cada turno de fala deve ser de tamanho moderado (2-4 frases)

## TAGS DE MARCAÇÃO TTS DISPONÍVEIS:
Use estas tags entre colchetes para enriquecer a experiência auditiva:

### Sons não verbais (inserem vocalizações):
- [sigh] - Insere um som de suspiro (frustração, alívio, pensamento)
- [laughing] - Insere uma risada natural
- [uhm] - Hesitação, torna a fala mais natural

### Modificadores de estilo (afetam a fala seguinte):
- [sarcasm] - Tom sarcástico na frase seguinte
- [shouting] - Aumenta o volume (use com moderação)
- [whispering] - Diminui o volume, sussurro
- [extremely fast] - Fala acelerada

### Controle de ritmo e pausas:
- [short pause] - Pausa breve (~250ms), separa cláusulas
- [medium pause] - Pausa padrão (~500ms), entre frases
- [long pause] - Pausa dramática (~1s), para efeito

## DICAS PARA NATURALIDADE:
1. Use [uhm] ocasionalmente para simular hesitação natural
2. Adicione [laughing] quando algo for engraçado ou interessante
3. Use [sigh] para expressar frustração ou reflexão
4. Use pausas para dar ritmo e permitir que o ouvinte absorva a informação
5. NÃO abuse das tags - use com moderação para não soar artificial
6. Alinhe o tom emocional do texto com as tags (texto assustador + [whispering])

## EXEMPLO DE USO:

Speaker 1: Olá pessoal! [short pause] Bem-vindos a mais um episódio do nosso podcast.
Speaker 2: Hoje vamos falar sobre um tema que [uhm] todo mundo quer saber...
Speaker 1: [laughing] É verdade! [medium pause] Então vamos direto ao ponto.
Speaker 2: [sigh] Olha, esse assunto é complexo, mas vou tentar explicar de forma simples.

## TEMA DO PODCAST:
{tema}

## SCRIPT:"""


def build_speakers_format(num_hosts: int) -> str:
    """
    Generates the speakers format for the prompt.
    
    Args:
        num_hosts: Number of hosts/speakers
        
    Returns:
        Formatted string with speaker format examples
    """
    lines = []
    for i in range(1, num_hosts + 1):
        lines.append(f"   Speaker {i}: [fala do host {i}]")
    return "\n".join(lines)


class ScriptService:
    """Service for generating podcast scripts using LLM."""
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    async def generate_script(
        self, 
        tema: str, 
        duracao_minutos: int = 3, 
        num_hosts: int = 2
    ) -> str:
        """
        Uses Gemini 2.5 Flash to generate podcast script with TTS markup tags.
        
        Args:
            tema: The theme or base content for the podcast
            duracao_minutos: Approximate desired duration in minutes
            num_hosts: Number of hosts/participants
            
        Returns:
            Formatted script with Speaker 1, Speaker 2, and TTS markup tags
        """
        logger.info(f"[SCRIPT] Iniciando geração de script - Tema: {tema[:100]}..., Duração: {duracao_minutos} min, Hosts: {num_hosts}")
        
        try:
            speakers_format = build_speakers_format(num_hosts)
            prompt = SCRIPT_GENERATOR_PROMPT.format(
                duracao=duracao_minutos,
                tema=tema,
                num_hosts=num_hosts,
                speakers_format=speakers_format
            )
            logger.debug(f"[SCRIPT] Prompt formatado, tamanho: {len(prompt)} chars")
            
            response = self.client.models.generate_content(
                model=settings.LLM_MODEL,
                contents=prompt
            )
            logger.debug("[SCRIPT] Resposta recebida do Gemini")
            
            if not response.text:
                logger.error("[SCRIPT] Resposta vazia do Gemini")
                raise HTTPException(status_code=500, detail="Falha ao gerar script do podcast")
            
            logger.info(f"[SCRIPT] Script gerado com sucesso, tamanho: {len(response.text)} chars")
            return response.text
            
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"[SCRIPT] Erro ao gerar script: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao gerar script: {str(e)}")


# Service instance for import
script_service = ScriptService()
