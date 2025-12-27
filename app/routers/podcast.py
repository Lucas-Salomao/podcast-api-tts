"""
Podcast generation endpoints.
"""

import json
import logging
import re
import uuid
from typing import List, Optional

from fastapi import APIRouter, Form, UploadFile, File, Query, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.models.schemas import HostVoice, PodcastScriptResponse
from app.models.voices import get_default_voice_configs
from app.services.script_service import script_service
from app.services.tts_service import tts_service
from app.services.document_service import document_service
from app.services.storage_service import storage_service
from app.services.podcast_repository import podcast_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/podcast", tags=["podcast"])


# Response models
class PodcastResponse(BaseModel):
    """Response model for a podcast."""
    id: str
    title: str
    theme: Optional[str]
    duration_minutes: Optional[int]
    audio_url: str
    created_at: str
    
    class Config:
        from_attributes = True


class PodcastListResponse(BaseModel):
    """Response model for podcast list."""
    podcasts: List[PodcastResponse]
    total: int


class PodcastGenerateResponse(BaseModel):
    """Response model for podcast generation with metadata."""
    id: str
    title: str
    audio_url: str


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
    user_id: str = Form(default=None),
    documentos: List[UploadFile] = File(default=[]),
):
    """
    Gera um podcast completo a partir do tema.
    
    1. Usa LLM para criar o script do diálogo
    2. Converte o script em áudio usando TTS
    3. Salva o áudio no GCS e metadados no banco (se user_id fornecido)
    4. Retorna o áudio em formato WAV
    
    Args:
        tema: Tema ou conteúdo base para o podcast
        duracao_minutos: Duração aproximada em minutos (1-60)
        num_hosts: Número de hosts do podcast (1-10)
        hosts_vozes: JSON string com configuração de vozes [{\"hostNumber\": 1, \"vozId\": \"Zephyr\"}, ...]
        user_id: ID do usuário (WSO2 sub) para salvar o podcast
        documentos: Arquivos opcionais para usar como base
    """
    logger.info(f"[API] POST /podcast/generate - Tema: {tema[:50]}..., Duração: {duracao_minutos} min, Hosts: {num_hosts}, User: {user_id}")
    
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
    
    logger.info(f"[API] /podcast/generate - Áudio gerado: {len(audio)} bytes")
    
    # If user_id provided, save to storage and database
    podcast_id = None
    if user_id:
        try:
            # Generate title from theme (first 100 chars)
            title = tema[:100] if len(tema) > 100 else tema
            
            # Upload to GCS
            audio_url, audio_path = storage_service.upload_audio(audio, user_id)
            
            # Save to database
            podcast = await podcast_repository.create(
                user_id=user_id,
                title=title,
                theme=tema[:500] if len(tema) > 500 else tema,
                duration_minutes=duracao_minutos,
                audio_url=audio_url,
                audio_path=audio_path,
            )
            podcast_id = str(podcast.id)
            logger.info(f"[API] Podcast saved with id: {podcast_id}")
        except Exception as e:
            logger.error(f"[API] Failed to save podcast: {e}")
            # Continue without saving - still return the audio
    
    # Return audio as WAV
    headers = {
        "Content-Disposition": "attachment; filename=podcast.wav"
    }
    if podcast_id:
        headers["X-Podcast-Id"] = podcast_id
    
    return Response(
        content=audio,
        media_type="audio/wav",
        headers=headers
    )


@router.get("/list", response_model=PodcastListResponse)
async def list_podcasts(
    user_id: str = Query(..., description="User ID from WSO2"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    Lista os podcasts de um usuário.
    
    Args:
        user_id: ID do usuário (WSO2 sub)
        limit: Número máximo de resultados (1-100)
        offset: Número de resultados para pular
    """
    logger.info(f"[API] GET /podcast/list - User: {user_id}, Limit: {limit}, Offset: {offset}")
    
    podcasts = await podcast_repository.list_by_user(user_id, limit, offset)
    total = await podcast_repository.count_by_user(user_id)
    
    # Generate signed URLs for each podcast
    podcast_responses = []
    for p in podcasts:
        try:
            signed_url = storage_service.get_signed_url(p.audio_path, expiration_hours=1)
        except Exception as e:
            logger.warning(f"[API] Failed to generate signed URL for {p.id}: {e}")
            signed_url = p.audio_url  # Fallback to stored URL
        
        podcast_responses.append(PodcastResponse(
            id=str(p.id),
            title=p.title,
            theme=p.theme,
            duration_minutes=p.duration_minutes,
            audio_url=signed_url,
            created_at=p.created_at.isoformat(),
        ))
    
    return PodcastListResponse(podcasts=podcast_responses, total=total)


@router.get("/{podcast_id}")
async def get_podcast(
    podcast_id: str,
    user_id: str = Query(..., description="User ID for authorization"),
):
    """
    Retorna um podcast específico com URL assinada.
    
    Args:
        podcast_id: UUID do podcast
        user_id: ID do usuário para autorização
    """
    try:
        pid = uuid.UUID(podcast_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid podcast ID format")
    
    podcast = await podcast_repository.get_by_id(pid)
    
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    
    if podcast.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this podcast")
    
    # Generate signed URL
    try:
        signed_url = storage_service.get_signed_url(podcast.audio_path, expiration_hours=2)
    except Exception as e:
        logger.error(f"[API] Failed to generate signed URL: {e}")
        signed_url = podcast.audio_url
    
    return PodcastResponse(
        id=str(podcast.id),
        title=podcast.title,
        theme=podcast.theme,
        duration_minutes=podcast.duration_minutes,
        audio_url=signed_url,
        created_at=podcast.created_at.isoformat(),
    )


@router.delete("/{podcast_id}")
async def delete_podcast(
    podcast_id: str,
    user_id: str = Query(..., description="User ID for authorization"),
):
    """
    Deleta um podcast (áudio do GCS e metadados do banco).
    
    Args:
        podcast_id: UUID do podcast
        user_id: ID do usuário para autorização
    """
    try:
        pid = uuid.UUID(podcast_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid podcast ID format")
    
    # Get podcast first to get the audio path
    podcast = await podcast_repository.get_by_id(pid)
    
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    
    if podcast.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this podcast")
    
    # Delete from GCS
    storage_service.delete_audio(podcast.audio_path)
    
    # Delete from database
    await podcast_repository.delete(pid, user_id)
    
    logger.info(f"[API] Deleted podcast {podcast_id}")
    
    return {"message": "Podcast deleted successfully", "id": podcast_id}


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
