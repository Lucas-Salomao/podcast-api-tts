"""
Configuration module for the Podcast Generator API.
Centralizes all configuration settings and environment variables.
"""

import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # CORS Settings
    CORS_ORIGINS: list[str] = ["*"]  # Em produção, especifique os domínios permitidos
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG")
    
    # App Info
    APP_TITLE: str = "Podcast Generator API"
    APP_DESCRIPTION: str = "API para geração de podcasts usando LLM para criar scripts e TTS para gerar áudio"
    APP_VERSION: str = "1.0.0"
    
    # LLM Models
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    TTS_MODEL: str = os.getenv("TTS_MODEL", "gemini-2.5-pro-preview-tts")


@lru_cache()
def get_settings() -> Settings:
    """Returns cached settings instance."""
    return Settings()


settings = get_settings()
