from typing import Literal, Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator, field_validator
import os

class Settings(BaseSettings):
    # ===== Gemini & LLM Configuration =====
    GOOGLE_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.5-flash"
    LLM_TEMPERATURE: float = 0.0
    EMBEDDINGS_MODEL: str = "models/gemini-embedding-001"
    
    # ===== Langfuse Observability =====
    LANGFUSE_PUBLIC_KEY: str = ""
    LANGFUSE_SECRET_KEY: str = ""
    LANGFUSE_BASE_URL: str = "https://cloud.langfuse.com"

    # ===== QDRANT Configuration =====
    QDRANT_API_KEY: str = ""
    QDRANT_URL: str = ""
    QDRANT_COLLECTION_NAME: str = "financial_docs"
    QDRANT_SPARSE_MODEL: str = "Qdrant/bm25"
    RETRIEVAL_MODE: str = "hybrid"
    FETCH_SIZE: int = 5

    # ===== Document Processing =====
    BASE_RAG_DIR: str = "data/rag-data"
    DATA_DIR: str = "data/rag-data/pdfs"
    OUTPUT_MD_DIR: str = "data/rag-data/markdown"
    OUTPUT_IMAGES_DIR: str = "data/rag-data/images"
    OUTPUT_DESC_DIR: str = "data/rag-data/images_desc"
    OUTPUT_TABLES_DIR: str = "data/rag-data/tables"
    LOGS_DIR: str = "logs"
    AGENT_FILE_BASE_DIR: str = "agent_files"

    # ===== Reranking Configuration =====
    ALLOW_RERANKING: str = "False"
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"

    # ===== Graph Configuration =====
    MAX_RETRIES_PER_THEME: int = 2
    MAX_PARALLEL_RESEARCHERS: int = 3
    MAX_RESEARCH_TASK_TIMEOUT_SEC: int = 300
    # Total tool calls per researcher = MAX_PARALLEL_RESEARCHERS * (TOOL_CALLS)
    HYBRID_SEARCH_TOOL_CALLS_PER_RESEARCHER: int = 5
    LIVE_FINANCE_RESEARCHER_TOOL_CALLS_PER_RESEARCHER: int = 2

    model_config = SettingsConfigDict(
        env_file=".envs/.env.local",
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=True
    )

    @field_validator('GOOGLE_API_KEY')
    def validate_google_key(cls, v):
        if not v:
            raise ValueError("Google API key is required")
        if not v.startswith('AIzaSy'):
            raise ValueError("Google API key must start with 'AIzaSy'")
        if len(v) < 20:
            raise ValueError("Google API key must be at least 20 characters long")
        return v

    @field_validator('QDRANT_API_KEY')
    def validate_qdrant_key(cls, v):
        if not v:
            raise ValueError("Qdrant API key is required")
        if not v.startswith('eyJhbGciOi'):
            raise ValueError("Qdrant API key must start with 'eyJhbGciOi'")
        if len(v) < 20:
            raise ValueError("Qdrant API key must be at least 20 characters long")
        return v

settings = Settings()