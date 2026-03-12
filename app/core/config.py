from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import urlparse


class Settings(BaseSettings):
    app_name: str = "Medical Management API"
    mongodb_uri: str
    mongodb_db_name: str | None = None
    groq_api_key: str
    groq_model: str = "llama-3.1-8b-instant"
    rag_knowledge_collection: str = "rag_knowledge"
    rag_chat_history_collection: str = "rag_chat_history"
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
