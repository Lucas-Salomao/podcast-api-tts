"""
Voice configuration and available voices for Gemini TTS.
"""

from typing import List
from app.models.schemas import HostVoice


# Vozes disponíveis do Gemini TTS
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

# Lista completa de vozes com metadados
VOZES_LISTA = [
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

# Vozes padrão para hosts (alternando entre feminino e masculino)
DEFAULT_VOICES = ["Zephyr", "Puck", "Aoede", "Charon", "Leda", "Fenrir", "Kore", "Orus", "Gacrux", "Algenib"]


def get_voice_by_id(voice_id: str) -> str:
    """
    Returns the voice ID if valid, otherwise returns default voice.
    
    Args:
        voice_id: The voice ID to validate
        
    Returns:
        Valid voice ID or "Zephyr" as fallback
    """
    return voice_id if voice_id in VOZES_DISPONIVEIS else "Zephyr"


def get_default_voice_configs(num_hosts: int) -> List[HostVoice]:
    """
    Generates default voice configuration alternating between female and male voices.
    
    Args:
        num_hosts: Number of hosts to generate configs for
        
    Returns:
        List of HostVoice configurations
    """
    return [
        HostVoice(hostNumber=i+1, vozId=DEFAULT_VOICES[i % len(DEFAULT_VOICES)])
        for i in range(num_hosts)
    ]
