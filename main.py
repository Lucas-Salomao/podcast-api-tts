# Podcast Generator API
# Gera podcasts a partir de um tema usando LLM + TTS

import io
import mimetypes
import os
import struct
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# FastAPI App
# ============================================================

app = FastAPI(
    title="Podcast Generator API",
    description="API para geração de podcasts usando LLM para criar scripts e TTS para gerar áudio",
    version="1.0.0"
)


# ============================================================
# Models
# ============================================================

class PodcastRequest(BaseModel):
    """Request para gerar um podcast"""
    tema: str = Field(..., description="Tema ou conteúdo base para o podcast")
    duracao_minutos: int = Field(default=3, ge=1, le=10, description="Duração aproximada em minutos (1-10)")


class PodcastScriptResponse(BaseModel):
    """Response com apenas o script gerado"""
    script: str


# ============================================================
# LLM Script Generator
# ============================================================

SCRIPT_GENERATOR_PROMPT = """Você é um roteirista especializado em criar scripts de podcast em português brasileiro.

Seu objetivo é criar um diálogo natural e envolvente entre dois co-hosts discutindo o tema fornecido pelo usuário.

## REGRAS:
1. O script deve ter aproximadamente {duracao} minutos de duração quando lido em voz alta
2. Use o formato EXATO:
   Speaker 1: [fala do primeiro host]
   Speaker 2: [fala do segundo host]
3. NÃO use nomes, apenas "Speaker 1" e "Speaker 2"
4. Escreva em português brasileiro natural e coloquial
5. Inclua:
   - Uma introdução ao tema
   - Discussão dos pontos principais
   - Exemplos práticos quando relevante
   - Uma conclusão
6. Evite jargões técnicos excessivos
7. Mantenha um tom conversacional e amigável, como dois amigos discutindo

## TEMA DO PODCAST:
{tema}

## SCRIPT:"""


async def generate_podcast_script(tema: str, duracao_minutos: int = 3) -> str:
    """
    Usa Gemini 2.5 Flash para gerar o script do podcast.
    
    Args:
        tema: O tema ou conteúdo base para o podcast
        duracao_minutos: Duração aproximada desejada em minutos
        
    Returns:
        Script formatado com Speaker 1 e Speaker 2
    """
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    prompt = SCRIPT_GENERATOR_PROMPT.format(
        duracao=duracao_minutos,
        tema=tema
    )
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    
    if not response.text:
        raise HTTPException(status_code=500, detail="Falha ao gerar script do podcast")
    
    return response.text


# ============================================================
# TTS Audio Generator
# ============================================================

def parse_audio_mime_type(mime_type: str) -> dict[str, int]:
    """
    Extrai bits per sample e sample rate do MIME type de áudio.
    
    Args:
        mime_type: String do MIME type (ex: "audio/L16;rate=24000")
        
    Returns:
        Dict com "bits_per_sample" e "rate"
    """
    bits_per_sample = 16
    rate = 24000

    parts = mime_type.split(";")
    for param in parts:
        param = param.strip()
        if param.lower().startswith("rate="):
            try:
                rate_str = param.split("=", 1)[1]
                rate = int(rate_str)
            except (ValueError, IndexError):
                pass
        elif param.startswith("audio/L"):
            try:
                bits_per_sample = int(param.split("L", 1)[1])
            except (ValueError, IndexError):
                pass

    return {"bits_per_sample": bits_per_sample, "rate": rate}


def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
    """
    Gera header WAV e combina com dados de áudio raw.
    
    Args:
        audio_data: Dados de áudio raw
        mime_type: MIME type do áudio
        
    Returns:
        Arquivo WAV completo em bytes
    """
    parameters = parse_audio_mime_type(mime_type)
    bits_per_sample = parameters["bits_per_sample"]
    sample_rate = parameters["rate"]
    num_channels = 1
    data_size = len(audio_data)
    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,
        1,
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size
    )
    return header + audio_data


def generate_podcast_audio(script: str) -> bytes:
    """
    Converte script de podcast em áudio WAV usando Gemini TTS.
    
    Args:
        script: Script formatado com Speaker 1 e Speaker 2
        
    Returns:
        Áudio WAV em bytes
    """
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    model = "gemini-2.5-pro-preview-tts"
    
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(
                    text=f"Please read aloud the following in a podcast interview style:\n{script}"
                ),
            ],
        ),
    ]
    
    generate_content_config = types.GenerateContentConfig(
        temperature=1,
        response_modalities=["audio"],
        speech_config=types.SpeechConfig(
            multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                speaker_voice_configs=[
                    types.SpeakerVoiceConfig(
                        speaker="Speaker 1",
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name="Zephyr"
                            )
                        ),
                    ),
                    types.SpeakerVoiceConfig(
                        speaker="Speaker 2",
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name="Puck"
                            )
                        ),
                    ),
                ]
            ),
        ),
    )

    # Coleta todos os chunks de áudio
    audio_chunks = []
    
    for chunk in client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=generate_content_config,
    ):
        if (
            chunk.candidates is None
            or chunk.candidates[0].content is None
            or chunk.candidates[0].content.parts is None
        ):
            continue
            
        part = chunk.candidates[0].content.parts[0]
        if part.inline_data and part.inline_data.data:
            inline_data = part.inline_data
            data_buffer = inline_data.data
            
            # Converte para WAV se necessário
            file_extension = mimetypes.guess_extension(inline_data.mime_type)
            if file_extension is None:
                data_buffer = convert_to_wav(inline_data.data, inline_data.mime_type)
            
            audio_chunks.append(data_buffer)
    
    if not audio_chunks:
        raise HTTPException(status_code=500, detail="Falha ao gerar áudio do podcast")
    
    # Combina todos os chunks (o primeiro já tem o header WAV)
    return b"".join(audio_chunks)


# ============================================================
# API Endpoints
# ============================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Podcast Generator API"}


@app.post("/podcast/script", response_model=PodcastScriptResponse)
async def generate_script(request: PodcastRequest):
    """
    Gera apenas o script do podcast (sem áudio).
    Útil para preview e ajustes antes de gerar o áudio.
    """
    script = await generate_podcast_script(request.tema, request.duracao_minutos)
    return PodcastScriptResponse(script=script)


@app.post("/podcast/generate")
async def create_podcast(request: PodcastRequest):
    """
    Gera um podcast completo a partir do tema.
    
    1. Usa LLM para criar o script do diálogo
    2. Converte o script em áudio usando TTS
    3. Retorna o áudio em formato WAV
    """
    # Gera o script via LLM
    script = await generate_podcast_script(request.tema, request.duracao_minutos)
    
    # Gera o áudio via TTS
    audio = generate_podcast_audio(script)
    
    # Retorna o áudio como WAV
    return Response(
        content=audio,
        media_type="audio/wav",
        headers={
            "Content-Disposition": "attachment; filename=podcast.wav"
        }
    )


@app.post("/podcast/generate-from-script")
async def create_podcast_from_script(script: str):
    """
    Gera áudio a partir de um script já pronto.
    Use este endpoint se você já tem um script formatado.
    """
    audio = generate_podcast_audio(script)
    
    return Response(
        content=audio,
        media_type="audio/wav",
        headers={
            "Content-Disposition": "attachment; filename=podcast.wav"
        }
    )


# ============================================================
# Run (para desenvolvimento)
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
