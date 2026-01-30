from dotenv import load_dotenv
from pydantic_settings import BaseSettings
import os

load_dotenv()


class Settings(BaseSettings):
    """Application settings."""

    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://user:password@localhost:5432/instagram_tracker"
    )

    # Worker settings
    worker_interval_hours: int = int(os.getenv("WORKER_INTERVAL_HOURS", "6"))
    worker_reels_limit: int = int(os.getenv("WORKER_REELS_LIMIT", "2"))
    audio_dir: str = os.getenv("AUDIO_DIR", "audio")

    # Admin panel settings
    admin_port: int = int(os.getenv("ADMIN_PORT", "8000"))
    admin_host: str = os.getenv("ADMIN_HOST", "127.0.0.1")
    admin_debug: bool = os.getenv("ADMIN_DEBUG", "false").lower() == "true"

    # Instagram cookies
    instagram_sessionid: str = ""
    instagram_ds_user_id: str = ""
    instagram_csrftoken: str = ""
    instagram_mid: str = ""
    instagram_rur: str = ""
    instagram_ig_did: str = ""
    instagram_datr: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
