from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import urlparse


class Settings(BaseSettings):
    app_name: str = "Medical Management API"
    mongodb_uri: str
    mongodb_db_name: str | None = None
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    @property
    def resolved_mongodb_db_name(self) -> str:
        if self.mongodb_db_name:
            return self.mongodb_db_name

        parsed = urlparse(self.mongodb_uri)
        db_from_uri = parsed.path.lstrip("/")
        if db_from_uri:
            return db_from_uri

        return "medical_management"


settings = Settings()
