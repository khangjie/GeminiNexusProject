from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "AI Expense Operations Hub"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database (Cloud SQL)
    DATABASE_URL: str = "sqlite:///./dev.db"  # Override with Cloud SQL in production

    # Google Cloud
    GCP_PROJECT_ID: str = ""
    GCP_REGION: str = "us-central1"
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # Gemini / Vertex AI
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "Gemini 3.1 Flash Lite"

    # Cloud Vision
    VISION_API_ENDPOINT: str = ""

    # Firebase Auth
    FIREBASE_PROJECT_ID: str = ""
    ENABLE_DEV_AUTH: bool = False

    # Qdrant Vector Database (RAG)
    QDRANT_URL: str = ""             # e.g. http://localhost:6333  or  https://xyz.qdrant.tech
    QDRANT_API_KEY: str = ""         # Leave blank for local/unauthenticated instances

    # JWT (internal service tokens)
    SECRET_KEY: str = "change-this-secret-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Rate limiting
    ENABLE_RATE_LIMIT: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 120
    RATE_LIMIT_AI_REQUESTS_PER_MINUTE: int = 20

    # Input safety guardrails
    ENABLE_SAFETY_GUARDRAILS: bool = True
    MAX_ANALYTICS_QUERY_LENGTH: int = 500
    MAX_SEARCH_QUERY_LENGTH: int = 200


@lru_cache
def get_settings() -> Settings:
    return Settings()
