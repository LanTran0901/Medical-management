from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import parse_qsl, quote_plus, urlencode, urlparse, urlunparse


class Settings(BaseSettings):
    app_name: str = "Medical Management API"

    mongodb_uri: str
    mongodb_db_name: str | None = None

    database_url: str | None = None
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "medical"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_SSLMODE: str = "require"

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
    def resolved_mongodb_uri(self) -> str:
        parsed = urlparse(self.mongodb_uri)
        if not parsed.username and not parsed.password:
            return self.mongodb_uri

        user = quote_plus(parsed.username or "")
        password = quote_plus(parsed.password or "")

        # Reconstruct netloc: user:password@host[:port]
        host_part = parsed.hostname or ""
        if parsed.port:
            host_part = f"{host_part}:{parsed.port}"
        netloc = f"{user}:{password}@{host_part}"

        return urlunparse(parsed._replace(netloc=netloc))

    @property
    def resolved_mongodb_db_name(self) -> str:
        if self.mongodb_db_name:
            return self.mongodb_db_name
        parsed = urlparse(self.mongodb_uri)
        db_from_uri = parsed.path.lstrip("/")
        return db_from_uri if db_from_uri else "medical_management"

    @property
    def POSTGRES_DATABASE_URL(self) -> str:
        """Async SQLAlchemy connection URL (asyncpg driver)."""
        if self.database_url:
            parsed = urlparse(self.database_url)
            scheme = parsed.scheme
            if scheme == "postgresql":
                scheme = "postgresql+asyncpg"
            elif scheme == "postgresql+psycopg2":
                scheme = "postgresql+asyncpg"

            query_items = []
            for key, value in parse_qsl(parsed.query, keep_blank_values=True):
                if key == "sslmode":
                    query_items.append(("ssl", value))
                else:
                    query_items.append((key, value))

            return urlunparse(parsed._replace(scheme=scheme, query=urlencode(query_items)))

        user = quote_plus(self.POSTGRES_USER)
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql+asyncpg://{user}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            f"?ssl={self.POSTGRES_SSLMODE}"
        )

    @property
    def POSTGRES_SYNC_URL(self) -> str:
        if self.database_url:
            parsed = urlparse(self.database_url)
            scheme = parsed.scheme
            if scheme == "postgresql+asyncpg":
                scheme = "postgresql+psycopg2"
            elif scheme not in {"postgresql", "postgresql+psycopg2"}:
                scheme = "postgresql"

            query_items = []
            for key, value in parse_qsl(parsed.query, keep_blank_values=True):
                if key == "ssl":
                    query_items.append(("sslmode", value))
                else:
                    query_items.append((key, value))

            return urlunparse(parsed._replace(scheme=scheme, query=urlencode(query_items)))

        user = quote_plus(self.POSTGRES_USER)
        password = quote_plus(self.POSTGRES_PASSWORD)
        return (
            f"postgresql://{user}:{password}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            f"?sslmode={self.POSTGRES_SSLMODE}"
        )


settings = Settings()
