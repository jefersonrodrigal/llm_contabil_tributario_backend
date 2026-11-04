"""Configurações do backend, lidas de variáveis de ambiente / .env.

Config do núcleo de IA (Ollama, embeddings, Chroma, chunking, retrieval,
base documental) vive em `ai_engine.config` — esse módulo só tem o que é
específico do backend (hoje: armazenamento de documentos enviados).
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    documents_storage_dir: Path = BASE_DIR / "database" / "documents"
    documents_max_size_bytes: int = 15 * 1024 * 1024  # 15 MB


settings = Settings()
