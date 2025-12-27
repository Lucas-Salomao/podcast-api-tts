"""
Pydantic schemas for API request/response models.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class HostVoice(BaseModel):
    """Configuração de voz para um host"""
    hostNumber: int = Field(..., ge=1, le=10, description="Número do host (1-10)")
    vozId: str = Field(..., description="ID da voz do Gemini TTS")


class PodcastRequest(BaseModel):
    """Request para gerar um podcast"""
    tema: str = Field(..., description="Tema ou conteúdo base para o podcast")
    duracao_minutos: int = Field(default=3, ge=1, le=60, description="Duração aproximada em minutos (1-60)")
    num_hosts: int = Field(default=2, ge=1, le=10, description="Número de hosts do podcast (1-10)")
    hosts_vozes: Optional[List[HostVoice]] = Field(default=None, description="Configuração de vozes por host")


class PodcastScriptResponse(BaseModel):
    """Response com apenas o script gerado"""
    script: str


class EnhanceResponse(BaseModel):
    """Response com texto aprimorado"""
    texto_original: str
    texto_aprimorado: str
