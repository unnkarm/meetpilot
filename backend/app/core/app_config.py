"""Single source for non-secret product and processing defaults.

Change model/provider choices here. Deployment addresses may be overridden by
environment variables; credentials remain in ``core.config``.
"""

import os
from dataclasses import dataclass, field


def _env_flag(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class AIConfig:
    provider: str = field(default_factory=lambda: os.getenv("AI_PROVIDER", "ollama"))
    model: str = field(default_factory=lambda: os.getenv("OLLAMA_CHAT_MODEL", "qwen3:4b-instruct"))
    temperature: float = 0.2
    max_tokens: int = 2048
    context_tokens: int = 8192
    retries: int = 2
    timeout_seconds: float = 180.0
    enabled: bool = True
    remote_model: str = "gemini-2.0-flash"
    remote_rpm_limit: int = 15


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str = field(default_factory=lambda: os.getenv("EMBEDDING_PROVIDER", "ollama"))
    model: str = field(default_factory=lambda: os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text-v2-moe"))
    dimensions: int = 768  # Existing pgvector schema. Changing this needs a migration and reindex.
    query_prefix: str = field(default_factory=lambda: os.getenv("EMBEDDING_QUERY_PREFIX", "search_query: "))
    document_prefix: str = field(default_factory=lambda: os.getenv("EMBEDDING_DOCUMENT_PREFIX", "search_document: "))
    batch_size: int = 16
    enabled: bool = True


@dataclass(frozen=True)
class TranscriptionConfig:
    provider: str = field(default_factory=lambda: os.getenv("TRANSCRIPTION_PROVIDER", "local"))
    model: str = field(default_factory=lambda: os.getenv("WHISPER_MODEL", "base"))
    device: str = "cpu"
    compute_type: str = "int8"
    diarization_provider: str = "single_speaker"
    chunk_seconds: int = 900
    overlap_seconds: int = 15
    remote_fallback: bool = False
    hf_space_id: str = "Subham05x/meetpilot-whisper-diarization"


@dataclass(frozen=True)
class LanguageConfig:
    default_language: str = field(default_factory=lambda: os.getenv("DEFAULT_LANGUAGE", "auto"))
    enable_detection: bool = field(default_factory=lambda: _env_flag("ENABLE_LANGUAGE_DETECTION", True))
    multilingual_transcription: bool = field(default_factory=lambda: _env_flag("MULTILINGUAL_TRANSCRIPTION", True))
    multilingual_llm: bool = field(default_factory=lambda: _env_flag("MULTILINGUAL_LLM", True))
    multilingual_embeddings: bool = field(default_factory=lambda: _env_flag("MULTILINGUAL_EMBEDDINGS", True))
    rag_cross_language: bool = field(default_factory=lambda: _env_flag("RAG_CROSS_LANGUAGE", True))
    summary_language_mode: str = field(default_factory=lambda: os.getenv("SUMMARY_LANGUAGE_MODE", "meeting"))
    qa_language_mode: str = field(default_factory=lambda: os.getenv("QA_LANGUAGE_MODE", "question"))
    minimum_confidence: float = field(default_factory=lambda: float(os.getenv("LANGUAGE_MIN_CONFIDENCE", "0.55")))
    prompt_version: str = "multilingual-v1"


@dataclass(frozen=True)
class RAGConfig:
    top_k: int = 6
    similarity_threshold: float = field(default_factory=lambda: float(os.getenv("RAG_MAX_COSINE_DISTANCE", "0.70")))
    max_context_chars: int = 16000


@dataclass(frozen=True)
class UploadConfig:
    max_audio_bytes: int = 250 * 1024 * 1024
    max_document_bytes: int = 30 * 1024 * 1024
    audio_extensions: tuple[str, ...] = (".mp3", ".mp4", ".m4a", ".aac", ".wav", ".webm", ".ogg", ".flac")
    document_extensions: tuple[str, ...] = (".pdf", ".docx", ".txt", ".md", ".markdown")


@dataclass(frozen=True)
class DocumentConfig:
    chunk_chars: int = 500
    overlap_chars: int = 100


@dataclass(frozen=True)
class PilotPhase1Config:
    enabled: bool = field(default_factory=lambda: _env_flag("PILOT_ENABLED", True))
    observability_enabled: bool = field(default_factory=lambda: _env_flag("PILOT_OBSERVABILITY_ENABLED", True))
    context_window: int = field(default_factory=lambda: max(1, min(100, int(os.getenv("PILOT_CONTEXT_WINDOW", "20")))))
    memory_enabled: bool = field(default_factory=lambda: _env_flag("PILOT_MEMORY_ENABLED", True))
    memory_confidence_threshold: float = field(default_factory=lambda: float(os.getenv("PILOT_MEMORY_CONFIDENCE_THRESHOLD", "0.85")))
    identity_confidence_threshold: float = field(default_factory=lambda: float(os.getenv("PILOT_IDENTITY_CONFIDENCE_THRESHOLD", "0.9")))
    memory_limit: int = 20
    wake_word: str = field(default_factory=lambda: os.getenv("PILOT_WAKE_WORD", "Hey Pilot"))
    stt_provider: str = field(default_factory=lambda: os.getenv("PILOT_STT_PROVIDER", "faster_whisper"))
    diarization_provider: str = field(default_factory=lambda: os.getenv("PILOT_DIARIZATION_PROVIDER", "single_speaker"))
    wakeword_provider: str = field(default_factory=lambda: os.getenv("PILOT_WAKEWORD_PROVIDER", "transcript_phrase"))
    tts_provider: str = field(default_factory=lambda: os.getenv("PILOT_TTS_PROVIDER", "piper"))
    audio_provider: str = field(default_factory=lambda: os.getenv("PILOT_AUDIO_PROVIDER", "vexa"))
    tts_enabled: bool = field(default_factory=lambda: _env_flag("PILOT_TTS_ENABLED", True))
    session_ttl_seconds: int = 3600
    vad_rms_threshold: int = 350
    silence_end_ms: int = 700
    partial_interval_ms: int = 2200
    max_utterance_ms: int = 15000
    audio_sample_rate: int = 16000


@dataclass(frozen=True)
class RuntimeConfig:
    ai: AIConfig = field(default_factory=AIConfig)
    embeddings: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    transcription: TranscriptionConfig = field(default_factory=TranscriptionConfig)
    language: LanguageConfig = field(default_factory=LanguageConfig)
    rag: RAGConfig = field(default_factory=RAGConfig)
    uploads: UploadConfig = field(default_factory=UploadConfig)
    documents: DocumentConfig = field(default_factory=DocumentConfig)
    pilot: PilotPhase1Config = field(default_factory=PilotPhase1Config)
    storage_provider: str = "local"
    storage_dir: str = "./storage"
    worker_concurrency: int = 1
    polling_interval_ms: int = 3000
    stale_processing_minutes: int = 120
    debug: bool = False
    ollama_url: str = field(default_factory=lambda: os.getenv("OLLAMA_URL", "http://localhost:11434"))


APP_CONFIG = RuntimeConfig()
