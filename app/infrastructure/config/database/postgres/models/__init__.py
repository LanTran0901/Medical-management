# Import all ORM models here so that Alembic's env.py auto-discovers them
# when it imports this package. Any new model file MUST be added here.
from app.infrastructure.config.database.postgres.models.user_model import UserModel  # noqa: F401

__all__ = ["UserModel"]
