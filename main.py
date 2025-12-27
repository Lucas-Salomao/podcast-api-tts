# Podcast Generator API
# Gera podcasts a partir de um tema usando LLM + TTS

import io
import json
import logging
import mimetypes
import os
import struct
from typing import List, Optional

from fastapi import FastAPI, Form, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Configuração de logging para debug
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# Vozes disponíveis do Gemini TTS
# ============================================================

VOZES_DISPONIVEIS = {
    # Femininas
    "Achernar", "Aoede", "Autonoe", "Callirrhoe", "Despina", "Erinome",
    "Gacrux", "Kore", "Laomedeia", "Leda", "Pulcherrima", "Sulafat",
    "Vindemiatrix", "Zephyr",
    # Masculinas
    "Achird", "Algenib", "Algieba", "Alnilam", "Charon", "Enceladus",
    "Fenrir", "Iapetus", "Orus", "Puck", "Rasalgethi", "Sadachbia",
    "Sadaltager", "Schedar", "Umbriel", "Zubenelgenubi"
}

# ============================================================
# FastAPI App
# ============================================================

app = FastAPI(
    title="Podcast Generator API",
    description="API para geração de podcasts usando LLM para criar scripts e TTS para gerar áudio",
    version="1.0.0"
)

# Configuração de CORS para permitir requisições do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique os domínios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Models
# ============================================================

class HostVoice(BaseModel):
    """Configuração de voz para um host"""
    hostNumber: int = Field(..., ge=1, le=10, description="Número do host (1-10)")
    vozId: str = Field(..., description="ID da voz do Gemini TTS")


class PodcastRequest(BaseModel):
    """Request para gerar um podcast"""
    tema: str = Field(..., description="Tema ou conteúdo base para o podcast")
    duracao_minutos: int = Field(default=3, ge=1, le=60, description="Duração aproximada em minutos (1-60)")
    num_hosts: int = Field(default=2, ge=1, le=10, description="Número de hosts do podcast (1-10)")
    hosts_vozes: List[HostVoice] = Field(default=None, description="Configuração de vozes por host")


class PodcastScriptResponse(BaseModel):
    """Response com apenas o script gerado"""
    script: str


class EnhanceResponse(BaseModel):
    """Response com texto aprimorado"""
    texto_original: str
    texto_aprimorado: str


# ============================================================
# LLM Text Enhancer
# ============================================================

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


async def enhance_text(texto: str) -> str:
    """
    Usa Gemini para aprimorar o texto do usuário.
    
    Args:
        texto: O texto original do usuário
        
    Returns:
        Texto aprimorado e expandido
    """
    logger.info(f"[ENHANCE] Aprimorando texto: {texto[:100]}...")
    
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        
        prompt = ENHANCE_PROMPT.format(texto=texto)
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        if not response.text:
            logger.error("[ENHANCE] Resposta vazia do Gemini")
            raise HTTPException(status_code=500, detail="Falha ao aprimorar texto")
        
        logger.info(f"[ENHANCE] Texto aprimorado com sucesso, tamanho: {len(response.text)} chars")
        return response.text
        
    except Exception as e:
        logger.exception(f"[ENHANCE] Erro ao aprimorar texto: {e}")
        raise


# ============================================================
# LLM Script Generator
# ============================================================

SCRIPT_GENERATOR_PROMPT = """Você é um roteirista especializado em criar scripts de podcast em português brasileiro.

Seu objetivo é criar um diálogo natural e envolvente entre {num_hosts} participante(s) discutindo o tema fornecido pelo usuário.

## REGRAS:
1. O script deve ter aproximadamente {duracao} minutos de duração quando lido em voz alta
2. Use o formato EXATO:
{speakers_format}
3. NÃO use nomes, apenas "Speaker 1", "Speaker 2", etc.
4. Escreva em português brasileiro natural e coloquial
5. Inclua:
   - Uma introdução ao tema
   - Discussão dos pontos principais
   - Exemplos práticos quando relevante
   - Uma conclusão
6. Evite jargões técnicos excessivos
7. Mantenha um tom conversacional e amigável
8. Distribua as falas de forma equilibrada entre todos os participantes

## TEMA DO PODCAST:
{tema}

## SCRIPT:"""


def build_speakers_format(num_hosts: int) -> str:
    """Gera o formato de speakers para o prompt."""
    lines = []
    for i in range(1, num_hosts + 1):
        lines.append(f"   Speaker {i}: [fala do host {i}]")
    return "\n".join(lines)


async def generate_podcast_script(tema: str, duracao_minutos: int = 3, num_hosts: int = 2) -> str:
    """
    Usa Gemini 2.5 Flash para gerar o script do podcast.
    
    Args:
        tema: O tema ou conteúdo base para o podcast
        duracao_minutos: Duração aproximada desejada em minutos
        num_hosts: Número de hosts/participantes do podcast
        
    Returns:
        Script formatado com Speaker 1, Speaker 2, ..., Speaker N
    """
    logger.info(f"[SCRIPT] Iniciando geração de script - Tema: {tema[:100]}..., Duração: {duracao_minutos} min, Hosts: {num_hosts}")
    
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        logger.debug("[SCRIPT] Cliente Gemini criado com sucesso")
        
        speakers_format = build_speakers_format(num_hosts)
        prompt = SCRIPT_GENERATOR_PROMPT.format(
            duracao=duracao_minutos,
            tema=tema,
            num_hosts=num_hosts,
            speakers_format=speakers_format
        )
        logger.debug(f"[SCRIPT] Prompt formatado, tamanho: {len(prompt)} chars")
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        logger.debug("[SCRIPT] Resposta recebida do Gemini")
        
        if not response.text:
            logger.error("[SCRIPT] Resposta vazia do Gemini")
            raise HTTPException(status_code=500, detail="Falha ao gerar script do podcast")
        
        logger.info(f"[SCRIPT] Script gerado com sucesso, tamanho: {len(response.text)} chars")
        return response.text
        
    except Exception as e:
        logger.exception(f"[SCRIPT] Erro ao gerar script: {e}")
        raise


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


def build_speaker_voice_configs(hosts_vozes: List[HostVoice]) -> List[types.SpeakerVoiceConfig]:
    """
    Constrói a configuração de vozes para cada speaker.
    
    Args:
        hosts_vozes: Lista de configurações de voz por host
        
    Returns:
        Lista de SpeakerVoiceConfig para o Gemini TTS
    """
    configs = []
    for hv in sorted(hosts_vozes, key=lambda x: x.hostNumber):
        # Valida se a voz existe
        voice_name = hv.vozId if hv.vozId in VOZES_DISPONIVEIS else "Zephyr"
        configs.append(
            types.SpeakerVoiceConfig(
                speaker=f"Speaker {hv.hostNumber}",
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                ),
            )
        )
    return configs


def get_default_voice_configs(num_hosts: int) -> List[HostVoice]:
    """
    Gera configuração de vozes padrão alternando entre feminino e masculino.
    """
    default_voices = ["Zephyr", "Puck", "Aoede", "Charon", "Leda", "Fenrir", "Kore", "Orus", "Gacrux", "Algenib"]
    return [
        HostVoice(hostNumber=i+1, vozId=default_voices[i % len(default_voices)])
        for i in range(num_hosts)
    ]


def generate_podcast_audio(script: str, hosts_vozes: List[HostVoice]) -> bytes:
    """
    Converte script de podcast em áudio WAV usando Gemini TTS.
    
    Args:
        script: Script formatado com Speaker 1, Speaker 2, ..., Speaker N
        hosts_vozes: Configuração de vozes por host
        
    Returns:
        Áudio WAV em bytes
    """
    logger.info(f"[TTS] Iniciando geração de áudio, script tem {len(script)} chars, {len(hosts_vozes)} hosts")
    
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        logger.debug("[TTS] Cliente Gemini criado para TTS")

        model = "gemini-2.5-pro-preview-tts"
        logger.debug(f"[TTS] Usando modelo: {model}")
        
        # Constrói configuração de vozes dinamicamente
        speaker_configs = build_speaker_voice_configs(hosts_vozes)
        logger.debug(f"[TTS] Configuração de vozes: {[(s.speaker, s.voice_config.prebuilt_voice_config.voice_name) for s in speaker_configs]}")
        
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
                    speaker_voice_configs=speaker_configs
                ),
            ),
        )

        logger.debug("[TTS] Iniciando streaming de áudio do Gemini...")
        
        # Coleta todos os chunks de áudio
        audio_chunks = []
        chunk_count = 0
        
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
                logger.debug(f"[TTS] Chunk {chunk_count} vazio, pulando...")
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
                chunk_count += 1
                logger.debug(f"[TTS] Chunk {chunk_count} recebido, tamanho: {len(data_buffer)} bytes")
        
        if not audio_chunks:
            logger.error("[TTS] Nenhum chunk de áudio recebido!")
            raise HTTPException(status_code=500, detail="Falha ao gerar áudio do podcast")
        
        # Combina todos os chunks (o primeiro já tem o header WAV)
        total_audio = b"".join(audio_chunks)
        logger.info(f"[TTS] Áudio gerado com sucesso! Total: {len(total_audio)} bytes, {chunk_count} chunks")
        return total_audio
        
    except Exception as e:
        logger.exception(f"[TTS] Erro ao gerar áudio: {e}")
        raise


# ============================================================
# API Endpoints
# ============================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    logger.debug("[API] Health check chamado")
    return {"status": "ok", "message": "Podcast Generator API"}


@app.post("/enhance", response_model=EnhanceResponse)
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
    texto_aprimorado = await enhance_text(texto)
    
    return EnhanceResponse(
        texto_original=texto,
        texto_aprimorado=texto_aprimorado
    )


@app.post("/podcast/script", response_model=PodcastScriptResponse)
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
    script = await generate_podcast_script(tema, duracao_minutos, num_hosts)
    logger.info("[API] /podcast/script concluído com sucesso")
    return PodcastScriptResponse(script=script)


@app.post("/podcast/generate")
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
    
    # Parse hosts_vozes do JSON string
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
    
    # Garante que temos vozes para todos os hosts
    if len(parsed_voices) < num_hosts:
        for i in range(len(parsed_voices) + 1, num_hosts + 1):
            default_voice = get_default_voice_configs(1)[0]
            default_voice.hostNumber = i
            parsed_voices.append(default_voice)
    
    # Processa documentos se houver
    documentos_conteudo = ""
    if documentos:
        for doc in documentos:
            content = await doc.read()
            try:
                text = content.decode("utf-8")
                documentos_conteudo += f"\n\n--- Conteúdo do documento {doc.filename} ---\n{text}"
            except UnicodeDecodeError:
                logger.warning(f"[API] Não foi possível ler documento {doc.filename} como texto")
    
    # Combina tema com conteúdo dos documentos
    tema_completo = tema
    if documentos_conteudo:
        tema_completo = f"{tema}\n\n## Material de Referência:{documentos_conteudo}"
    
    # Gera o script via LLM
    script = await generate_podcast_script(tema_completo, duracao_minutos, num_hosts)
    
    # Gera o áudio via TTS
    audio = generate_podcast_audio(script, parsed_voices)
    
    logger.info(f"[API] /podcast/generate concluído - Áudio: {len(audio)} bytes")
    
    # Retorna o áudio como WAV
    return Response(
        content=audio,
        media_type="audio/wav",
        headers={
            "Content-Disposition": "attachment; filename=podcast.wav"
        }
    )


@app.post("/podcast/generate-from-script")
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
    
    # Conta quantos speakers existem no script
    import re
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
    
    audio = generate_podcast_audio(script, parsed_voices)
    
    logger.info(f"[API] /podcast/generate-from-script concluído - Áudio: {len(audio)} bytes")
    
    return Response(
        content=audio,
        media_type="audio/wav",
        headers={
            "Content-Disposition": "attachment; filename=podcast.wav"
        }
    )


@app.get("/vozes")
async def list_voices():
    """
    Lista todas as vozes disponíveis do Gemini TTS.
    """
    voices = [
        {"id": "Achernar", "nome": "Achernar", "genero": "Feminino"},
        {"id": "Aoede", "nome": "Aoede", "genero": "Feminino"},
        {"id": "Autonoe", "nome": "Autonoe", "genero": "Feminino"},
        {"id": "Callirrhoe", "nome": "Callirrhoe", "genero": "Feminino"},
        {"id": "Despina", "nome": "Despina", "genero": "Feminino"},
        {"id": "Erinome", "nome": "Erinome", "genero": "Feminino"},
        {"id": "Gacrux", "nome": "Gacrux", "genero": "Feminino"},
        {"id": "Kore", "nome": "Kore", "genero": "Feminino"},
        {"id": "Laomedeia", "nome": "Laomedeia", "genero": "Feminino"},
        {"id": "Leda", "nome": "Leda", "genero": "Feminino"},
        {"id": "Pulcherrima", "nome": "Pulcherrima", "genero": "Feminino"},
        {"id": "Sulafat", "nome": "Sulafat", "genero": "Feminino"},
        {"id": "Vindemiatrix", "nome": "Vindemiatrix", "genero": "Feminino"},
        {"id": "Zephyr", "nome": "Zephyr", "genero": "Feminino"},
        {"id": "Achird", "nome": "Achird", "genero": "Masculino"},
        {"id": "Algenib", "nome": "Algenib", "genero": "Masculino"},
        {"id": "Algieba", "nome": "Algieba", "genero": "Masculino"},
        {"id": "Alnilam", "nome": "Alnilam", "genero": "Masculino"},
        {"id": "Charon", "nome": "Charon", "genero": "Masculino"},
        {"id": "Enceladus", "nome": "Enceladus", "genero": "Masculino"},
        {"id": "Fenrir", "nome": "Fenrir", "genero": "Masculino"},
        {"id": "Iapetus", "nome": "Iapetus", "genero": "Masculino"},
        {"id": "Orus", "nome": "Orus", "genero": "Masculino"},
        {"id": "Puck", "nome": "Puck", "genero": "Masculino"},
        {"id": "Rasalgethi", "nome": "Rasalgethi", "genero": "Masculino"},
        {"id": "Sadachbia", "nome": "Sadachbia", "genero": "Masculino"},
        {"id": "Sadaltager", "nome": "Sadaltager", "genero": "Masculino"},
        {"id": "Schedar", "nome": "Schedar", "genero": "Masculino"},
        {"id": "Umbriel", "nome": "Umbriel", "genero": "Masculino"},
        {"id": "Zubenelgenubi", "nome": "Zubenelgenubi", "genero": "Masculino"},
    ]
    return {"vozes": voices}


# ============================================================
# Run (para desenvolvimento)
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
