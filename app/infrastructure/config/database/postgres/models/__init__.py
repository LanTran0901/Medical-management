# Import all ORM models here so that Alembic's env.py auto-discovers them
# when it imports this package. Any new model file MUST be added here.
from app.infrastructure.config.database.postgres.models.user_model import UserModel
from app.infrastructure.config.database.postgres.models.auth_models import UserDeviceModel, RefreshTokenModel
from app.infrastructure.config.database.postgres.models.family_models import FamilyModel, FamilyMembershipModel
from app.infrastructure.config.database.postgres.models.profile_models import HealthDetailModel, ProfileModel
from app.infrastructure.config.database.postgres.models.medical_dictionary_models import (
    DiseaseModel,
    DrugModel,
    VaccineModel,
)

__all__ = [
    "UserModel",
    "UserDeviceModel",
    "RefreshTokenModel",
    "FamilyModel",
    "FamilyMembershipModel",
    "ProfileModel",
    "HealthDetailModel",
    "DiseaseModel",
    "DrugModel",
    "VaccineModel",
]
