from functools import lru_cache
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "submission-file-service"
    host: str = "127.0.0.1"
    port: int = 8105
    api_prefix: str = "/api/submissions"
    database_path: str = "./storage/submissions.db"
    upload_dir: str = "./storage/uploads"
    max_upload_bytes: int = 10 * 1024 * 1024
    allowed_extensions: str = ".pdf,.doc,.docx,.txt,.zip,.png,.jpg,.jpeg"
    allowed_mime_types: str = ""
    dependency_timeout_seconds: float = 3.0
    auth_service_url: str = "http://127.0.0.1:8102"
    auth_validate_path: str = "/api/v1/auth/me"
    auth_token_header: str = "Authorization"
    assignment_service_url: str = "http://127.0.0.1:8104"
    assignment_validate_path: str = "/api/assignments/{assignment_id}"
    notification_service_url: str = "http://127.0.0.1:8106"
    notification_submission_path: str = "/api/notifications"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def extensions(self) -> set[str]:
        return {item.strip().lower() for item in self.allowed_extensions.split(",") if item.strip()}

    @property
    def mime_types(self) -> set[str]:
        return {item.strip().lower() for item in self.allowed_mime_types.split(",") if item.strip()}

    @property
    def db_path(self) -> Path:
        return Path(self.database_path)

    @property
    def uploads_path(self) -> Path:
        return Path(self.upload_dir).resolve()


@lru_cache
def get_settings() -> Settings:
    # Tests can opt out of developer-local .env files while retaining normal
    # environment variable overrides. Runtime keeps the existing .env behavior.
    return Settings(_env_file=None if os.getenv("SUBMISSION_TESTING") == "1" else ".env")
