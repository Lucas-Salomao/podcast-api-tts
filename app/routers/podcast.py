"""
Podcast generation endpoints.
"""

import json
import logging
import re
from typing import List

from fastapi import APIRouter, Form, UploadFile, File
from fastapi.responses import Response

from app.models.schemas import HostVoice, PodcastScriptResponse
from app.models.voices import get_default_voice_configs
from app.services.script_service import script_service
from app.services.tts_service import tts_service
from app.services.document_service import document_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/podcast", tags=["podcast"])


@router.post("/script", response_model=PodcastScriptResponse)
async def generate_script_endpoint(
    tema: str = Form(...),
    duracao_minutos: int = Form(default=3),
    num_hosts: int = Form(default=2),
):
    """
    Gera apenas o script do podcast (sem áudio).
    Útil para preview e ajustes antes de gerar o áudio.
    """
    logger.info(f"[API] POST /podcast/script - Tema: {tema[:50]}..., Duração: {duracao_minutos} min, Hosts: {num_hosts}")
    script = await script_service.generate_script(tema, duracao_minutos, num_hosts)
    logger.info("[API] /podcast/script concluído com sucesso")
    return PodcastScriptResponse(script=script)


@router.post("/generate")
async def create_podcast(
    tema: str = Form(...),
    duracao_minutos: int = Form(default=3),
    num_hosts: int = Form(default=2),
    hosts_vozes: str = Form(default=None),
    documentos: List[UploadFile] = File(default=[]),
):
    """
    Gera um podcast completo a partir do tema.
    
    1. Usa LLM para criar o script do diálogo
    2. Converte o script em áudio usando TTS
    3. Retorna o áudio em formato WAV
    
    Args:
        tema: Tema ou conteúdo base para o podcast
        duracao_minutos: Duração aproximada em minutos (1-60)
        num_hosts: Número de hosts do podcast (1-10)
        hosts_vozes: JSON string com configuração de vozes [{"hostNumber": 1, "vozId": "Zephyr"}, ...]
        documentos: Arquivos opcionais para usar como base
    """
    logger.info(f"[API] POST /podcast/generate - Tema: {tema[:50]}..., Duração: {duracao_minutos} min, Hosts: {num_hosts}")
    
    # Parse hosts_vozes from JSON string
    parsed_voices: List[HostVoice] = []
    if hosts_vozes:
        try:
            voices_data = json.loads(hosts_vozes)
            parsed_voices = [HostVoice(**v) for v in voices_data]
            logger.debug(f"[API] Vozes configuradas: {parsed_voices}")
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[API] Erro ao parsear hosts_vozes, usando padrão: {e}")
            parsed_voices = get_default_voice_configs(num_hosts)
    else:
        parsed_voices = get_default_voice_configs(num_hosts)
    
    # Ensure we have voices for all hosts
    if len(parsed_voices) < num_hosts:
        for i in range(len(parsed_voices) + 1, num_hosts + 1):
            default_voice = get_default_voice_configs(1)[0]
            default_voice.hostNumber = i
            parsed_voices.append(default_voice)
    
    # Process documents using Docling
    documentos_conteudo = ""
    if documentos:
        files_to_process = []
        for doc in documentos:
            content = await doc.read()
            files_to_process.append((doc.filename, content))
        documentos_conteudo = await document_service.process_uploaded_files(files_to_process)
    
    # Combine theme with document content
    tema_completo = tema
    if documentos_conteudo:
        tema_completo = f"{tema}\n\n## Material de Referência:{documentos_conteudo}"
    
    # Generate script via LLM
    script = await script_service.generate_script(tema_completo, duracao_minutos, num_hosts)
    
    # Generate audio via TTS
    audio = tts_service.generate_audio(script, parsed_voices)
    
    logger.info(f"[API] /podcast/generate concluído - Áudio: {len(audio)} bytes")
    
    # Return audio as WAV
    return Response(
        content=audio,
        media_type="audio/wav",
        headers={
            "Content-Disposition": "attachment; filename=podcast.wav"
        }
    )


@router.post("/generate-from-script")
async def create_podcast_from_script(
    script: str = Form(...),
    hosts_vozes: str = Form(default=None),
):
    """
    Gera áudio a partir de um script já pronto.
    Use este endpoint se você já tem um script formatado.
    
    Args:
        script: Script formatado com Speaker 1, Speaker 2, etc.
        hosts_vozes: JSON string com configuração de vozes
    """
    logger.info(f"[API] POST /podcast/generate-from-script - Script: {len(script)} chars")
    
    # Count how many speakers exist in the script
    speakers = set(re.findall(r'Speaker (\d+):', script))
    num_hosts = max([int(s) for s in speakers]) if speakers else 2
    
    # Parse hosts_vozes
    parsed_voices: List[HostVoice] = []
    if hosts_vozes:
        try:
            voices_data = json.loads(hosts_vozes)
            parsed_voices = [HostVoice(**v) for v in voices_data]
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[API] Erro ao parsear hosts_vozes: {e}")
            parsed_voices = get_default_voice_configs(num_hosts)
    else:
        parsed_voices = get_default_voice_configs(num_hosts)
    
    audio = tts_service.generate_audio(script, parsed_voices)
    
    logger.info(f"[API] /podcast/generate-from-script concluído - Áudio: {len(audio)} bytes")
    
    return Response(
        content=audio,
        media_type="audio/wav",
        headers={
            "Content-Disposition": "attachment; filename=podcast.wav"
        }
    )
