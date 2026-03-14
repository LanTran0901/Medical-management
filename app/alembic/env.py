"""
Alembic env.py for Medical-management.

Working directory when running: app/
  → cd d:\\WDA\\Medical-management\\app
  → alembic upgrade head

Mirrors the KIMS (KMS) Alembic pattern:
  - Sync URL built from env vars (with fallback defaults)
  - Sequences synced after each migration run
  - Docker host auto-correction (localhost → postgres service name)
"""
from __future__ import with_statement

import os
import socket
import sys
from logging.config import fileConfig
from urllib.parse import quote_plus

from alembic import context
from sqlalchemy import create_engine, inspect, text

# ── sys.path: add project root so `from app.*` imports resolve ────────────────
# __file__ = <project_root>/app/alembic/env.py
_HERE = os.path.abspath(__file__)                # .../app/alembic/env.py
_ALEMBIC_DIR = os.path.dirname(_HERE)            # .../app/alembic/
_APP_DIR = os.path.dirname(_ALEMBIC_DIR)          # .../app/
_PROJECT_ROOT = os.path.dirname(_APP_DIR)         # .../Medical-management/

for _p in (_PROJECT_ROOT, _APP_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Import Base + all models (triggers model registration in Base.metadata) ───
from app.infrastructure.config.database.base import Base                         # noqa: E402
import app.infrastructure.config.database.postgres.models                        # noqa: E402, F401

# ── Alembic config ────────────────────────────────────────────────────────────
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# ── Build DB URL from environment (Docker-aware) ──────────────────────────────

def _build_sync_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        if database_url.startswith("postgresql+asyncpg://"):
            return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        return database_url

    is_docker = os.path.exists("/.dockerenv") or os.path.exists("/proc/1/cgroup")

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db   = os.getenv("POSTGRES_DB",   "medical")
    user = os.getenv("POSTGRES_USER", "postgres")
    pwd  = os.getenv("POSTGRES_PASSWORD", "postgres")
    sslmode = os.getenv("POSTGRES_SSLMODE", "require")

    # Inside Docker: force service name instead of localhost
    if is_docker and host in ("localhost", "127.0.0.1", ""):
        host = "postgres"

    hostaddr = ""
    try:
        if host not in ("localhost", "127.0.0.1", "postgres"):
            ipv4_infos = socket.getaddrinfo(host, int(port), socket.AF_INET, socket.SOCK_STREAM)
            if ipv4_infos:
                hostaddr = ipv4_infos[0][4][0]
    except Exception:  # noqa: BLE001
        hostaddr = ""

    hostaddr_param = f"&hostaddr={hostaddr}" if hostaddr else ""

    return (
        f"postgresql://{quote_plus(user)}:{quote_plus(pwd)}"
        f"@{host}:{port}/{db}?sslmode={sslmode}"
        f"{hostaddr_param}"
    )


# ── Sequence sync (keep auto-increment in sync after data seeding) ────────────

def sync_all_sequences(connection) -> None:
    """Sync PostgreSQL sequences with actual max values from their tables."""
    inspector = inspect(connection)
    tables = inspector.get_table_names()

    sequences_to_sync: list[tuple[str, str, str]] = [
        # (sequence_name, table_name, id_column)
        # Add more as new tables are created.
    ]

    synced = 0
    for seq_name, table_name, id_col in sequences_to_sync:
        if table_name not in tables:
            continue
        try:
            result = connection.execute(
                text(
                    f"SELECT EXISTS ("
                    f"  SELECT 1 FROM pg_sequences"
                    f"  WHERE schemaname = 'public' AND sequencename = '{seq_name}'"
                    f");"
                )
            )
            if result.scalar():
                connection.execute(
                    text(
                        f"SELECT setval('{seq_name}', "
                        f"  COALESCE((SELECT MAX({id_col}) FROM {table_name}), 1), "
                        f"  true);"
                    )
                )
                synced += 1
                print(f"[Alembic] Synced sequence: {seq_name}")
        except Exception as exc:  # noqa: BLE001
            print(f"[Alembic] Warning: could not sync {seq_name}: {exc}")

    if synced:
        print(f"[Alembic] {synced} sequence(s) synced.")


# ── Migration runners ─────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """Run in 'offline' mode — emit SQL to stdout without a live DB connection."""
    context.configure(
        url=_build_sync_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run in 'online' mode — connect to DB and apply migrations."""
    connectable = create_engine(_build_sync_url(), future=True)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()
            sync_all_sequences(connection)


# ── Entry point ───────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
