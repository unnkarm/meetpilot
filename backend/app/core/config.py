import os
from functools import lru_cache

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseModel
    class BaseSettings(BaseModel):  # type: ignore[no-redef]
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            for field in self.model_fields:
                env_val = os.getenv(field)
                if env_val is not None:
                    try:
                        f_type = self.model_fields[field].annotation
                        if f_type is int:
                            setattr(self, field, int(env_val))
                        elif f_type is bool:
                            setattr(self, field, env_val.lower() in ("true", "1", "yes"))
                        else:
                            setattr(self, field, env_val)
                    except Exception:
                        setattr(self, field, env_val)

    def SettingsConfigDict(**kwargs):  # type: ignore[no-redef]
        return kwargs


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://meetpilot:meetpilot@localhost:5432/meetpilot"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Auth (Legacy JWT & Clerk)
    JWT_SECRET_KEY: str = "dev-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # Clerk Auth
    CLERK_PUBLISHABLE_KEY: str = ""
    CLERK_SECRET_KEY: str = ""
    CLERK_JWKS_URL: str = ""
    CLERK_ISSUER_URL: str = ""


    # Gemini & AI Configuration (Configurable Quotas & Models)
    GEMINI_API_KEY: str = ""
    GEMINI_TEXT_MODEL: str = "gemini-2.0-flash"
    GEMINI_AUDIO_MODEL: str = "gemini-2.0-flash"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    GEMINI_RPM_LIMIT: int = 15
    GEMINI_TPM_LIMIT: int = 1000000
    GEMINI_RPD_LIMIT: int = 1500

    # Local Zero-Cost Inference Engines
    USE_LOCAL_WHISPER: bool = True
    USE_LOCAL_EMBEDDINGS: bool = True

    # Hugging Face ZeroGPU Space (Self-Hosted Whisper + PyAnnote Diarization)
    HF_SPACE_ID: str = "Subham05x/meetpilot-whisper-diarization"
    HF_API_TOKEN: str = ""
    HF_SPACE_TIMEOUT_SECONDS: int = 600


    # Storage
    STORAGE_DIR: str = "./storage"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Third-Party Integrations & Encryption at rest
    ENCRYPTION_SECRET_KEY: str = "meetpilot-super-fernet-secret-32-chars-long!"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/oauth/google/callback"
    ZOOM_CLIENT_ID: str = ""
    ZOOM_CLIENT_SECRET: str = ""
    ZOOM_REDIRECT_URI: str = "http://localhost:3000/oauth/zoom/callback"

    # Vexa.ai Self-Hosted Live Meeting Capture
    VEXA_API_URL: str = "http://host.docker.internal:18056"
    VEXA_WS_URL: str = "ws://host.docker.internal:18056/ws"
    VEXA_API_KEY: str = "vxa_bot_NPdcTll20UtK1d1FJBq6xJlQ3j5qfzvu"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]



@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
