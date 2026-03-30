# Import all ORM models here so that Alembic's env.py auto-discovers them
# when it imports this package. Any new model file MUST be added here.
from app.infrastructure.config.database.postgres.models.user_model import UserModel
from app.infrastructure.config.database.postgres.models.auth_models import UserDeviceModel, RefreshTokenModel
from app.infrastructure.config.database.postgres.models.family_models import (
    FamilyInviteModel,
    FamilyMembershipModel,
    FamilyModel,
)
from app.infrastructure.config.database.postgres.models.profile_models import HealthDetailModel, ProfileModel
from app.infrastructure.config.database.postgres.models.medicine_inventory_model import MedicineInventoryModel
from app.infrastructure.config.database.postgres.models.medical_record_models import (
    FollowUpAppointmentModel,
    FollowUpReminderActionModel,
    MedicalRecordAttachmentModel,
    MedicalRecordModel,
)
from app.infrastructure.config.database.postgres.models.vaccination_models import (
    UserVaccinationModel,
    VaccinationDoseModel,
    VaccinationRecommendationModel,
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
    "FamilyInviteModel",
    "ProfileModel",
    "HealthDetailModel",
    "MedicineInventoryModel",
    "MedicalRecordModel",
    "MedicalRecordAttachmentModel",
    "FollowUpAppointmentModel",
    "FollowUpReminderActionModel",
    "VaccinationRecommendationModel",
    "UserVaccinationModel",
    "VaccinationDoseModel",
    "DiseaseModel",
    "DrugModel",
    "VaccineModel",
]
