from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import parse_qsl, quote_plus, urlencode, urlparse, urlunparse


class Settings(BaseSettings):
    app_name: str = "Medical Management API"
    data_dir: str = "app/data"

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
    rag_embedding_model: str = "intfloat/multilingual-e5-small"
    rag_embedding_dimensions: int = 384
    rag_top_k: int = 6
    rag_per_type_limit: int = 3

    jwt_secret: str = "super_secret_key_change_me_in_production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30
    bcrypt_rounds: int = Field(
        default=14,
        validation_alias=AliasChoices("BCRYPT_ROUNDS", "bcrypt_rounds"),
    )
    google_client_id: str | None = None
    google_redirect_uri: str | None = None
    firebase_credentials_path: str | None = None

    # Schedule → FCM dispatch (optional background loop + manual trigger)
    schedule_dispatch_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "SCHEDULE_DISPATCH_ENABLED",
            "schedule_dispatch_enabled",
        ),
        description="When true and Firebase is configured, poll due MEDICINE schedules and send FCM.",
    )
    schedule_dispatch_interval_seconds: int = Field(
        default=60,
        ge=10,
        validation_alias=AliasChoices(
            "SCHEDULE_DISPATCH_INTERVAL_SECONDS",
            "schedule_dispatch_interval_seconds",
        ),
    )
    schedule_dispatch_due_grace_minutes: int = Field(
        default=3,
        ge=0,
        le=15,
        validation_alias=AliasChoices(
            "SCHEDULE_DISPATCH_DUE_GRACE_MINUTES",
            "schedule_dispatch_due_grace_minutes",
        ),
        description="Allow dispatching a reminder if it is due within the last N minutes to avoid missing exact-minute ticks.",
    )
    fcm_android_channel_schedule: str = Field(
        default="medicine_reminders",
        validation_alias=AliasChoices(
            "FCM_ANDROID_CHANNEL_SCHEDULE",
            "fcm_android_channel_schedule",
        ),
        description="Must match a notification channel id on the Android app.",
    )
    internal_dispatch_secret: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "INTERNAL_DISPATCH_SECRET",
            "internal_dispatch_secret",
        ),
        description="If set, POST /notifications/dispatch/schedules requires header X-Internal-Secret.",
    )

    # Expo Push (ExponentPushToken[...]) — enables dispatch without Firebase when true
    expo_push_enabled: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "EXPO_PUSH_ENABLED",
            "expo_push_enabled",
        ),
        description="When true, background dispatch can run without Firebase (Expo tokens only).",
    )
    expo_push_access_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "EXPO_PUSH_ACCESS_TOKEN",
            "expo_push_access_token",
        ),
        description="Optional Expo access token for higher push API limits.",
    )

    # SMTP Config for Emails
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool = True

    # Medical file uploads (FR-007) — env MEDICAL_UPLOAD_DIR maps here (see tasks T001)
    medical_upload_dir: str = Field(
        default="uploads/medical",
        validation_alias=AliasChoices("MEDICAL_UPLOAD_DIR", "medical_upload_dir"),
        description="Directory on disk for medical record attachment bytes (MVP local disk).",
    )
    medical_upload_max_mb: int | None = Field(
        default=10,
        validation_alias=AliasChoices("MEDICAL_UPLOAD_MAX_MB", "medical_upload_max_mb"),
        description="Max upload size per file in MB; None disables limit in settings (enforce in handler).",
    )
    family_public_invite_ttl_seconds: int = Field(
        default=86_400,
        validation_alias=AliasChoices(
            "FAMILY_PUBLIC_INVITE_TTL_SECONDS",
            "family_public_invite_ttl_seconds",
        ),
        description="TTL for new public family invite codes (single-use); default 24h.",
    )

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

    def resolved_medical_upload_path(self) -> Path:
        """Absolute path for medical uploads (creates parent dirs is caller's responsibility)."""
        return Path(self.medical_upload_dir).expanduser().resolve()


settings = Settings()
