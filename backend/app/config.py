from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass
class Settings:
    app_name: str = "JobSpy Platform API"
    api_prefix: str = "/api"
    schedule_cron: str = "0 19 * * *"
    database_url: str = f"sqlite:///{PROJECT_ROOT / 'data' / 'jobs.db'}"
    llm_base_url: str = ""
    llm_api_key: str = ""
    model_name: str = "glm-4.7"
    cors_origins: list[str] = None

    def __init__(self) -> None:
        self.app_name = os.getenv("APP_NAME", self.app_name)
        self.api_prefix = os.getenv("API_PREFIX", self.api_prefix)
        self.schedule_cron = os.getenv("SCHEDULE_CRON", self.schedule_cron)
        self.database_url = os.getenv("DATABASE_URL", self.database_url)
        self.llm_base_url = os.getenv("LLM_BASE_URL", self.llm_base_url)
        self.llm_api_key = os.getenv("LLM_API_KEY", self.llm_api_key)
        self.model_name = os.getenv("MODEL_NAME", self.model_name)
        cors_origins = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
        )
        self.cors_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]


def get_settings() -> Settings:
    return Settings()
