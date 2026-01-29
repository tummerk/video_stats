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

    # Instagram cookies
    instagram_sessionid: str = os.getenv("INSTAGRAM_SESSIONID", "")
    instagram_ds_user_id: str = os.getenv("INSTAGRAM_DS_USER_ID", "")
    instagramcsrftoken: str = os.getenv("INSTAGRAM_CSRFTOKEN", "")
    instagram_mid: str = os.getenv("INSTAGRAM_MID", "")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
