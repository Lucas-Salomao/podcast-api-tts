"""
Text-to-Speech service using Gemini TTS.
"""

import logging
import mimetypes
from typing import List

from google import genai
from google.genai import types
from fastapi import HTTPException

from app.core.config import settings
from app.models.schemas import HostVoice
from app.models.voices import VOZES_DISPONIVEIS, get_default_voice_configs
from app.utils.audio import convert_to_wav

logger = logging.getLogger(__name__)


def build_speaker_voice_configs(hosts_vozes: List[HostVoice]) -> List[types.SpeakerVoiceConfig]:
    """
    Builds voice configuration for each speaker.
    
    Args:
        hosts_vozes: List of voice configurations per host
        
    Returns:
        List of SpeakerVoiceConfig for Gemini TTS
    """
    configs = []
    for hv in sorted(hosts_vozes, key=lambda x: x.hostNumber):
        # Validate if voice exists
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


class TTSService:
    """Service for converting text to speech using Gemini TTS."""
    
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    def generate_audio(self, script: str, hosts_vozes: List[HostVoice]) -> bytes:
        """
        Converts podcast script to WAV audio using Gemini TTS.
        
        Args:
            script: Formatted script with Speaker 1, Speaker 2, ..., Speaker N
            hosts_vozes: Voice configuration per host
            
        Returns:
            WAV audio in bytes
        """
        logger.info(f"[TTS] Iniciando geração de áudio, script tem {len(script)} chars, {len(hosts_vozes)} hosts")
        
        try:
            logger.debug(f"[TTS] Usando modelo: {settings.TTS_MODEL}")
            
            # Build voice configuration dynamically
            # NOTE: Gemini TTS multi-speaker API only supports exactly 2 speakers
            speaker_configs = build_speaker_voice_configs(hosts_vozes)
            
            if len(speaker_configs) != 2:
                logger.warning(f"[TTS] Gemini TTS requer exatamente 2 speakers, ajustando de {len(speaker_configs)} para 2")
                # Take first 2 or pad to 2
                if len(speaker_configs) > 2:
                    speaker_configs = speaker_configs[:2]
                elif len(speaker_configs) < 2:
                    # Add default second speaker if only 1
                    default_voices = get_default_voice_configs(2)
                    while len(speaker_configs) < 2:
                        idx = len(speaker_configs)
                        speaker_configs.append(
                            types.SpeakerVoiceConfig(
                                speaker=f"Speaker {idx + 1}",
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name=default_voices[idx].vozId
                                    )
                                ),
                            )
                        )
            
            logger.debug(f"[TTS] Configuração de vozes: {[(s.speaker, s.voice_config.prebuilt_voice_config.voice_name) for s in speaker_configs]}")
            
            # Build prompt with explicit speaker instructions
            tts_prompt = f"""TTS Instructions: This is a multi-speaker podcast dialogue. 
Use different voices for Speaker 1 and Speaker 2 as configured.
Read aloud naturally, respecting the dialogue format where each line starts with "Speaker 1:" or "Speaker 2:".

Podcast Script:
{script}"""
            
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=tts_prompt),
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
            
            # Collect all audio chunks
            audio_chunks = []
            chunk_count = 0
            
            for chunk in self.client.models.generate_content_stream(
                model=settings.TTS_MODEL,
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
                    
                    # Convert to WAV if necessary
                    file_extension = mimetypes.guess_extension(inline_data.mime_type)
                    if file_extension is None:
                        data_buffer = convert_to_wav(inline_data.data, inline_data.mime_type)
                    
                    audio_chunks.append(data_buffer)
                    chunk_count += 1
                    logger.debug(f"[TTS] Chunk {chunk_count} recebido, tamanho: {len(data_buffer)} bytes")
            
            if not audio_chunks:
                logger.error("[TTS] Nenhum chunk de áudio recebido!")
                raise HTTPException(status_code=500, detail="Falha ao gerar áudio do podcast")
            
            # Combine all chunks (first one already has WAV header)
            total_audio = b"".join(audio_chunks)
            logger.info(f"[TTS] Áudio gerado com sucesso! Total: {len(total_audio)} bytes, {chunk_count} chunks")
            return total_audio
            
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"[TTS] Erro ao gerar áudio: {e}")
            raise HTTPException(status_code=500, detail=f"Erro ao gerar áudio: {str(e)}")


# Service instance for import
tts_service = TTSService()
