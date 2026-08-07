"""
Atlas AI Financial Assistant - Configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # AI Models (fallback chain)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY") or os.getenv("SEED_KEYS_GOOGLE") or os.getenv("GOOGLE_API_KEY") or ""
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY") or os.getenv("SEED_KEYS_GROQ") or ""
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY") or os.getenv("SEED_KEYS_OPENAI") or ""
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY") or os.getenv("SEED_KEYS_OPENROUTER") or ""
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY") or os.getenv("SEED_KEYS_MISTRAL") or ""
    CEREBRAS_API_KEY: str = os.getenv("CEREBRAS_API_KEY") or os.getenv("SEED_KEYS_CEREBRAS") or ""
    GITHUB_API_KEY: str = os.getenv("GITHUB_API_KEY") or os.getenv("SEED_KEYS_GITHUB") or ""
    SAMBANOVA_API_KEY: str = os.getenv("SAMBANOVA_API_KEY") or os.getenv("SEED_KEYS_SAMBANOVA") or ""

    # Financial Data
    FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "")
    ALPHA_VANTAGE_API_KEY: str = os.getenv("ALPHA_VANTAGE_API_KEY", "")

    # Google OAuth2 Integration
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "https://atlas-ai-financial-assistant-f2m5.onrender.com/auth/google/callback")

    # Database — auto-converts Render's postgres:// to postgresql+psycopg:// for async SQLAlchemy
    # Uses psycopg[binary] (psycopg3) which has Python 3.14 pre-built wheels (unlike asyncpg)
    @property
    def DATABASE_URL(self) -> str:
        url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./atlas_financial.db")
        # Render provides postgres:// — convert to async-compatible postgresql+psycopg://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://") and "+psycopg" not in url and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    # Bot Settings
    BOT_NAME: str = os.getenv("BOT_NAME", "Atlas")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Limits
    MAX_CONVERSATION_HISTORY: int = 20  # Messages to include in AI context
    MAX_RESPONSE_LENGTH: int = 4000  # Telegram message limit ~4096 chars


settings = Settings()
