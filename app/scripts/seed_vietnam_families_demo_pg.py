from __future__ import annotations

import argparse
import json
import hashlib
import random
import secrets
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any

import sqlalchemy as sa

from app.core.config import settings
from app.infrastructure.config.database.postgres.models.medical_dictionary_models import (
    DiseaseModel,
    DrugModel,
    VaccineModel,
)


RANDOM_SEED = 20260326


FIRST_NAMES = [
    "An",
    "Bình",
    "Chi",
    "Dũng",
    "Hà",
    "Hải",
    "Hiền",
    "Hòa",
    "Hưng",
    "Khánh",
    "Lan",
    "Linh",
    "Mai",
    "Minh",
    "Nam",
    "Ngân",
    "Ngọc",
    "Phúc",
    "Phương",
    "Quân",
    "Quỳnh",
    "Sơn",
    "Thảo",
    "Trang",
    "Tuấn",
    "Uyên",
    "Vân",
    "Việt",
]

LAST_NAMES = ["Nguyễn", "Trần", "Lê", "Phạm", "Hoàng", "Huỳnh", "Vũ", "Đặng", "Bùi", "Đỗ"]

CITIES = [
    "Hà Nội",
    "TP. Hồ Chí Minh",
    "Đà Nẵng",
    "Hải Phòng",
    "Cần Thơ",
    "Huế",
    "Nha Trang",
    "Buôn Ma Thuột",
]

FAMILY_NAMES = [
    "Gia đình An Khang",
    "Gia đình Bình Minh",
    "Gia đình Hạnh Phúc",
    "Gia đình Sum Vầy",
    "Gia đình Chăm Sóc",
    "Gia đình Phúc Lộc",
    "Gia đình Tâm An",
    "Gia đình Mặt Trời",
    "Gia đình Yêu Thương",
    "Gia đình Thành Đạt",
    "Gia đình Thanh Bình",
    "Gia đình Vạn Phúc",
]

MEDICINES = [
    ("Paracetamol 500mg", "Viên nén", "viên"),
    ("Vitamin C", "Viên sủi", "ống"),
    ("Amoxicillin", "Kháng sinh", "viên"),
    ("Siro ho Prospan", "Siro", "chai"),
    ("ORS", "Bù điện giải", "gói"),
    ("Nước muối sinh lý", "Dung dịch", "chai"),
    ("Ibuprofen 400mg", "Viên nén", "viên"),
    ("Canxi Nano", "Viên nang", "viên"),
    ("Omega-3", "Viên mềm", "viên"),
]

DIAGNOSES = [
    ("Viêm họng cấp", "viem-hong-cap"),
    ("Cảm cúm mùa", "cam-cum-mua"),
    ("Viêm mũi dị ứng", "viem-mui-di-ung"),
    ("Đau dạ dày", "dau-da-day"),
    ("Sốt siêu vi", "sot-sieu-vi"),
]

VACCINES = ["Viêm gan B", "5 trong 1", "MMR", "Cúm mùa", "COVID-19"]


def _rand_full_name(rnd: random.Random) -> str:
    return f"{rnd.choice(LAST_NAMES)} {rnd.choice(FIRST_NAMES)}"


def _rand_blood(rnd: random.Random) -> str:
    return rnd.choice(["A_POS", "A_NEG", "B_POS", "B_NEG", "O_POS", "O_NEG", "AB_POS", "AB_NEG"])


def _rand_gender(rnd: random.Random) -> str:
    return rnd.choice(["male", "female", "other"])


def _rand_dob(rnd: random.Random, min_age: int = 3, max_age: int = 80) -> date:
    today = date.today()
    age = rnd.randint(min_age, max_age)
    day_offset = rnd.randint(0, 364)
    return today - timedelta(days=(age * 365 + day_offset))


def _invite_code(rnd: random.Random, idx: int) -> str:
    return f"VN{idx:02d}{secrets.token_hex(4).upper()}"


def _token_hash(user_id: uuid.UUID, device_id: str, i: int) -> str:
    raw = f"{user_id}:{device_id}:{i}:{secrets.token_hex(8)}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _exec_many_chunked(
    conn: sa.Connection,
    stmt: sa.sql.elements.TextClause,
    rows: list[dict[str, Any]],
    chunk_size: int,
) -> None:
    if not rows:
        return
    for i in range(0, len(rows), chunk_size):
        conn.execute(stmt, rows[i : i + chunk_size])


def seed_demo(
    *,
    family_count: int,
    users_per_family: int,
    reset: bool,
    dictionary_rows: int,
    chunk_size: int,
) -> dict[str, int]:
    rnd = random.Random(RANDOM_SEED)
    now = datetime.now(timezone.utc)
    engine = sa.create_engine(settings.POSTGRES_SYNC_URL, future=True)

    counters: dict[str, int] = {}
    DiseaseModel.__table__.create(bind=engine, checkfirst=True)
    DrugModel.__table__.create(bind=engine, checkfirst=True)
    VaccineModel.__table__.create(bind=engine, checkfirst=True)

    table_order = [
        "schedule_logs",
        "schedules",
        "growth_records",
        "vaccine_history",
        "medical_records",
        "medicine_inventory",
        "activity_logs",
        "family_memberships",
        "health_details",
        "profiles",
        "families",
        "refresh_tokens",
        "user_devices",
        "users",
        "diseases",
        "drugs",
        "vaccines",
    ]

    with engine.begin() as conn:
        if reset:
            conn.execute(sa.text(f"TRUNCATE TABLE {', '.join(table_order)} RESTART IDENTITY CASCADE"))

        users: list[dict[str, Any]] = []
        user_devices: list[dict[str, Any]] = []
        refresh_tokens: list[dict[str, Any]] = []
        profiles: list[dict[str, Any]] = []
        health_details: list[dict[str, Any]] = []
        families: list[dict[str, Any]] = []
        memberships: list[dict[str, Any]] = []
        medicines: list[dict[str, Any]] = []
        records: list[dict[str, Any]] = []
        vaccine_history: list[dict[str, Any]] = []
        schedules: list[dict[str, Any]] = []
        schedule_logs: list[dict[str, Any]] = []
        growth_records: list[dict[str, Any]] = []
        activity_logs: list[dict[str, Any]] = []

        for fi in range(family_count):
            family_id = uuid.uuid4()
            family_name = FAMILY_NAMES[fi % len(FAMILY_NAMES)]
            invite_code = _invite_code(rnd, fi + 1)
            families.append(
                {
                    "id": family_id,
                    "family_name": family_name,
                    "invite_code": invite_code,
                    "created_at": now - timedelta(days=rnd.randint(1, 180)),
                }
            )

            owner_profile_id: uuid.UUID | None = None
            family_user_ids: list[uuid.UUID] = []
            family_profile_ids: list[uuid.UUID] = []

            for ui in range(users_per_family):
                user_id = uuid.uuid4()
                family_user_ids.append(user_id)
                full_name = _rand_full_name(rnd)
                email = f"{full_name.lower().replace(' ', '.').replace('đ', 'd')}.{fi}.{ui}@demo.vn".encode(
                    "utf-8"
                ).decode("utf-8")
                users.append(
                    {
                        "id": user_id,
                        "email": email,
                        "password_hash": hashlib.sha256(f"demo-{fi}-{ui}".encode("utf-8")).hexdigest(),
                        "google_id": None,
                        "status": "active",
                        "created_at": now - timedelta(days=rnd.randint(1, 365)),
                        "updated_at": now,
                        "deleted_at": None,
                    }
                )

                device_id = f"device-{fi:02d}-{ui:02d}"
                user_devices.append(
                    {
                        "id": device_id,
                        "user_id": user_id,
                        "fcm_token": f"fcm_{secrets.token_hex(10)}",
                        "device_name": rnd.choice(["iPhone 14", "Samsung A54", "Xiaomi Note", "iPad Air"]),
                        "platform": rnd.choice(["ios", "android"]),
                        "last_active": now - timedelta(hours=rnd.randint(1, 96)),
                    }
                )
                refresh_tokens.append(
                    {
                        "id": uuid.uuid4(),
                        "user_id": user_id,
                        "device_id": device_id,
                        "token_hash": _token_hash(user_id, device_id, fi * 100 + ui),
                        "expires_at": now + timedelta(days=30),
                        "status": "ACTIVE",
                    }
                )

                profile_id = uuid.uuid4()
                family_profile_ids.append(profile_id)
                if owner_profile_id is None:
                    owner_profile_id = profile_id
                profiles.append(
                    {
                        "id": profile_id,
                        "owner_user_id": user_id,
                        "linked_user_id": user_id,
                        "full_name": full_name,
                        "dob": _rand_dob(rnd),
                        "gender": _rand_gender(rnd),
                        "height_cm": Decimal(str(round(rnd.uniform(140, 178), 1))),
                        "weight_kg": Decimal(str(round(rnd.uniform(42, 82), 1))),
                        "address": f"{rnd.randint(1, 300)} {rnd.choice(['Lê Lợi', 'Nguyễn Huệ', 'Trần Hưng Đạo'])}, {rnd.choice(CITIES)}",
                        "avatar_url": f"https://demo.vn/avatar/{profile_id}",
                        "status": "active",
                        "created_at": now - timedelta(days=rnd.randint(1, 365)),
                        "updated_at": now,
                        "deleted_at": None,
                    }
                )
                health_details.append(
                    {
                        "id": uuid.uuid4(),
                        "profile_id": profile_id,
                        "blood_type": _rand_blood(rnd),
                        "chronic_diseases": rnd.sample(
                            ["Tiểu đường", "Tăng huyết áp", "Hen nhẹ", "Không"],
                            k=1,
                        ),
                        "allergies": rnd.sample(["Hải sản", "Phấn hoa", "Lông mèo", "Không"], k=1),
                        "emergency_contact": f"{_rand_full_name(rnd)} - 09{rnd.randint(10000000, 99999999)}",
                        "notes": "Theo dõi sức khỏe định kỳ 6 tháng/lần",
                        "updated_at": now,
                    }
                )

            for pi, profile_id in enumerate(family_profile_ids):
                role = "OWNER" if profile_id == owner_profile_id else ("ADMIN" if pi % 5 == 0 else "MEMBER")
                memberships.append(
                    {
                        "id": uuid.uuid4(),
                        "family_id": family_id,
                        "profile_id": profile_id,
                        "role": role,
                        "added_by": family_user_ids[0],
                        "created_at": now - timedelta(days=rnd.randint(1, 180)),
                    }
                )

            virtual_profile_id = uuid.uuid4()
            profiles.append(
                {
                    "id": virtual_profile_id,
                    "owner_user_id": family_user_ids[0],
                    "linked_user_id": None,
                    "full_name": f"Bé của {family_name}",
                    "dob": _rand_dob(rnd, min_age=1, max_age=12),
                    "gender": _rand_gender(rnd),
                    "height_cm": Decimal(str(round(rnd.uniform(75, 145), 1))),
                    "weight_kg": Decimal(str(round(rnd.uniform(9, 42), 1))),
                    "address": f"{rnd.randint(1, 300)} Đường Gia Đình, {rnd.choice(CITIES)}",
                    "avatar_url": f"https://demo.vn/avatar/{virtual_profile_id}",
                    "status": "virtual",
                    "created_at": now - timedelta(days=rnd.randint(1, 365)),
                    "updated_at": now,
                    "deleted_at": None,
                }
            )
            health_details.append(
                {
                    "id": uuid.uuid4(),
                    "profile_id": virtual_profile_id,
                    "blood_type": _rand_blood(rnd),
                    "chronic_diseases": ["Không"],
                    "allergies": ["Không"],
                    "emergency_contact": f"{_rand_full_name(rnd)} - 09{rnd.randint(10000000, 99999999)}",
                    "notes": "Hồ sơ trẻ em theo dõi tăng trưởng",
                    "updated_at": now,
                }
            )
            memberships.append(
                {
                    "id": uuid.uuid4(),
                    "family_id": family_id,
                    "profile_id": virtual_profile_id,
                    "role": "MEMBER",
                    "added_by": family_user_ids[0],
                    "created_at": now - timedelta(days=rnd.randint(1, 180)),
                }
            )
            family_profile_ids.append(virtual_profile_id)

            family_medicines: list[uuid.UUID] = []
            for mi in range(8):
                med_id = uuid.uuid4()
                family_medicines.append(med_id)
                med = MEDICINES[(fi + mi) % len(MEDICINES)]
                medicines.append(
                    {
                        "id": med_id,
                        "family_id": family_id,
                        "medicine_name": med[0],
                        "medicine_type": med[1],
                        "expiry_date": date.today() + timedelta(days=rnd.randint(90, 900)),
                        "quantity_stock": Decimal(str(round(rnd.uniform(1, 30), 3))),
                        "unit": med[2],
                        "min_stock_alert": Decimal("3.000"),
                        "instruction": "Uống sau ăn, bảo quản nơi khô ráo",
                    }
                )

            for p_idx, profile_id in enumerate(family_profile_ids):
                for ri in range(2):
                    diag = DIAGNOSES[(p_idx + ri) % len(DIAGNOSES)]
                    records.append(
                        {
                            "id": uuid.uuid4(),
                            "profile_id": profile_id,
                            "created_by": family_user_ids[0],
                            "diagnosis_name": diag[0],
                            "diagnosis_slug": diag[1],
                            "doctor_name": rnd.choice(["BS. Nguyễn Văn A", "BS. Trần Thu B", "BS. Lê Minh C"]),
                            "hospital_name": rnd.choice(
                                ["BV Bạch Mai", "BV Chợ Rẫy", "BV Nhi Đồng 1", "BV Đà Nẵng"]
                            ),
                            "visit_date": date.today() - timedelta(days=rnd.randint(1, 1200)),
                            "attachment_urls": json.dumps(
                                {"files": [f"https://demo.vn/records/{uuid.uuid4()}.pdf"]}
                            ),
                            "created_at": now - timedelta(days=rnd.randint(1, 800)),
                        }
                    )

                for vi in range(2):
                    vaccine_history.append(
                        {
                            "id": uuid.uuid4(),
                            "profile_id": profile_id,
                            "vaccine_name": VACCINES[(p_idx + vi) % len(VACCINES)],
                            "dose_number": vi + 1,
                            "vaccinated_date": date.today() - timedelta(days=rnd.randint(100, 1500)),
                            "next_due_date": date.today() + timedelta(days=rnd.randint(90, 365)),
                        }
                    )

                for gi in range(3):
                    growth_records.append(
                        {
                            "id": uuid.uuid4(),
                            "profile_id": profile_id,
                            "height_cm": Decimal(str(round(rnd.uniform(80, 180), 2))),
                            "weight_kg": Decimal(str(round(rnd.uniform(12, 80), 2))),
                            "recorded_at": date.today() - timedelta(days=gi * 90 + rnd.randint(0, 25)),
                        }
                    )

                for si in range(2):
                    schedule_id = uuid.uuid4()
                    schedules.append(
                        {
                            "id": schedule_id,
                            "profile_id": profile_id,
                            "medicine_id": family_medicines[(p_idx + si) % len(family_medicines)],
                            "title": rnd.choice(["Nhắc uống thuốc", "Nhắc tái khám", "Nhắc tiêm vaccine"]),
                            "category": rnd.choice(["MEDICINE", "CHECKUP", "VACCINE"]),
                            "remind_time": time(hour=rnd.randint(6, 21), minute=rnd.choice([0, 15, 30, 45])),
                            "dosage_per_time": Decimal(str(round(rnd.uniform(0.5, 2.0), 3))),
                            "rrule": "FREQ=DAILY",
                            "status": rnd.choice(["ACTIVE", "PAUSED"]),
                        }
                    )
                    for li in range(2):
                        schedule_logs.append(
                            {
                                "id": uuid.uuid4(),
                                "schedule_id": schedule_id,
                                "status": rnd.choice(["DONE", "SKIPPED", "LATE"]),
                                "action_by": family_user_ids[li % len(family_user_ids)],
                                "action_time": now - timedelta(days=rnd.randint(1, 60)),
                            }
                        )

            for ai in range(6):
                activity_logs.append(
                    {
                        "id": uuid.uuid4(),
                        "family_id": family_id,
                        "user_id": family_user_ids[ai % len(family_user_ids)],
                        "action_desc": rnd.choice(
                            [
                                "Đã tạo hồ sơ thành viên mới",
                                "Đã cập nhật thông tin sức khỏe",
                                "Đã thêm lịch nhắc uống thuốc",
                                "Đã bổ sung thuốc trong tủ gia đình",
                                "Đã ghi nhận mũi tiêm mới",
                            ]
                        ),
                        "created_at": now - timedelta(days=rnd.randint(1, 120)),
                    }
                )

        disease_rows = []
        drug_rows = []
        vaccine_rows = []
        for i in range(1, dictionary_rows + 1):
            disease_rows.append(
                {
                    "source_index": i,
                    "title": f"Bệnh demo {i}",
                    "aliases": [f"BenhDemo{i}"],
                    "summary": "Dữ liệu mẫu bệnh cho môi trường demo.",
                    "content": {"overview": f"Mô tả bệnh demo {i}", "lang": "vi"},
                    "source_file": "seed_vn_demo",
                }
            )
            drug_rows.append(
                {
                    "source_index": i,
                    "title": f"Thuốc demo {i}",
                    "aliases": [f"ThuocDemo{i}"],
                    "summary": "Dữ liệu mẫu thuốc cho môi trường demo.",
                    "content": {"indications": f"Chỉ định demo {i}", "lang": "vi"},
                    "source_file": "seed_vn_demo",
                }
            )
            vaccine_rows.append(
                {
                    "source_index": i,
                    "title": f"Vaccine demo {i}",
                    "aliases": [f"VaccineDemo{i}"],
                    "summary": "Dữ liệu mẫu vaccine cho môi trường demo.",
                    "content": {"prevents_disease": f"Ngừa bệnh demo {i}", "lang": "vi"},
                    "source_file": "seed_vn_demo",
                }
            )

        _exec_many_chunked(
            conn,
            sa.text(
                """
                INSERT INTO users (id, email, password_hash, google_id, status, created_at, updated_at, deleted_at)
                VALUES (:id, :email, :password_hash, :google_id, :status, :created_at, :updated_at, :deleted_at)
                ON CONFLICT (email) DO NOTHING
                """
            ),
            users,
            chunk_size,
        )
        _exec_many_chunked(
            conn,
            sa.text(
                """
                INSERT INTO user_devices (id, user_id, fcm_token, device_name, platform, last_active)
                VALUES (:id, :user_id, :fcm_token, :device_name, :platform, :last_active)
                ON CONFLICT (id, user_id) DO NOTHING
                """
            ),
            user_devices,
            chunk_size,
        )
        _exec_many_chunked(
            conn,
            sa.text(
                """
                INSERT INTO refresh_tokens (id, user_id, device_id, token_hash, expires_at, status)
                VALUES (:id, :user_id, :device_id, :token_hash, :expires_at, :status)
                ON CONFLICT (token_hash) DO NOTHING
                """
            ),
            refresh_tokens,
            chunk_size,
        )
        _exec_many_chunked(
            conn,
            sa.text(
                """
                INSERT INTO families (id, family_name, invite_code, created_at)
                VALUES (:id, :family_name, :invite_code, :created_at)
                ON CONFLICT (invite_code) DO NOTHING
                """
            ),
            families,
            chunk_size,
        )
        _exec_many_chunked(
            conn,
            sa.text(
                """
                INSERT INTO profiles (
                    id, owner_user_id, linked_user_id, full_name, dob, gender, height_cm, weight_kg,
                    address, avatar_url, status, created_at, updated_at, deleted_at
                )
                VALUES (
                    :id, :owner_user_id, :linked_user_id, :full_name, :dob, :gender, :height_cm, :weight_kg,
                    :address, :avatar_url, :status, :created_at, :updated_at, :deleted_at
                )
                ON CONFLICT (id) DO NOTHING
                """
            ),
            profiles,
            chunk_size,
        )
        _exec_many_chunked(
            conn,
            sa.text(
                """
                INSERT INTO health_details (id, profile_id, blood_type, chronic_diseases, allergies, emergency_contact, notes, updated_at)
                VALUES (:id, :profile_id, :blood_type, :chronic_diseases, :allergies, :emergency_contact, :notes, :updated_at)
                ON CONFLICT (profile_id) DO NOTHING
                """
            ),
            health_details,
            chunk_size,
        )
        _exec_many_chunked(
            conn,
            sa.text(
                """
                INSERT INTO family_memberships (id, family_id, profile_id, role, added_by, created_at)
                VALUES (:id, :family_id, :profile_id, :role, :added_by, :created_at)
                ON CONFLICT (family_id, profile_id) DO NOTHING
                """
            ),
            memberships,
            chunk_size,
        )
        _exec_many_chunked(
            conn,
            sa.text(
                """
                INSERT INTO medicine_inventory (
                    id, family_id, medicine_name, medicine_type, expiry_date, quantity_stock, unit, min_stock_alert, instruction
                )
                VALUES (
                    :id, :family_id, :medicine_name, :medicine_type, :expiry_date, :quantity_stock, :unit, :min_stock_alert, :instruction
                )
                ON CONFLICT (id) DO NOTHING
                """
            ),
            medicines,
            chunk_size,
        )
        _exec_many_chunked(
            conn,
            sa.text(
                """
                INSERT INTO medical_records (
                    id, profile_id, created_by, diagnosis_name, diagnosis_slug, doctor_name, hospital_name, visit_date, attachment_urls, created_at
                )
                VALUES (
                    :id, :profile_id, :created_by, :diagnosis_name, :diagnosis_slug, :doctor_name, :hospital_name, :visit_date, CAST(:attachment_urls AS jsonb), :created_at
                )
                ON CONFLICT (id) DO NOTHING
                """
            ),
            records,
            chunk_size,
        )
        _exec_many_chunked(
            conn,
            sa.text(
                """
                INSERT INTO vaccine_history (id, profile_id, vaccine_name, dose_number, vaccinated_date, next_due_date)
                VALUES (:id, :profile_id, :vaccine_name, :dose_number, :vaccinated_date, :next_due_date)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            vaccine_history,
            chunk_size,
        )
        _exec_many_chunked(
            conn,
            sa.text(
                """
                INSERT INTO schedules (
                    id, profile_id, medicine_id, title, category, remind_time, dosage_per_time, rrule, status
                )
                VALUES (
                    :id, :profile_id, :medicine_id, :title, :category, :remind_time, :dosage_per_time, :rrule, :status
                )
                ON CONFLICT (id) DO NOTHING
                """
            ),
            schedules,
            chunk_size,
        )
        _exec_many_chunked(
            conn,
            sa.text(
                """
                INSERT INTO schedule_logs (id, schedule_id, status, action_by, action_time)
                VALUES (:id, :schedule_id, :status, :action_by, :action_time)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            schedule_logs,
            chunk_size,
        )
        _exec_many_chunked(
            conn,
            sa.text(
                """
                INSERT INTO growth_records (id, profile_id, height_cm, weight_kg, recorded_at)
                VALUES (:id, :profile_id, :height_cm, :weight_kg, :recorded_at)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            growth_records,
            chunk_size,
        )
        _exec_many_chunked(
            conn,
            sa.text(
                """
                INSERT INTO activity_logs (id, family_id, user_id, action_desc, created_at)
                VALUES (:id, :family_id, :user_id, :action_desc, :created_at)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            activity_logs,
            chunk_size,
        )

        disease_stmt = sa.dialects.postgresql.insert(DiseaseModel).values(disease_rows)
        conn.execute(
            disease_stmt.on_conflict_do_update(
                index_elements=[DiseaseModel.source_index],
                set_={
                    "title": disease_stmt.excluded.title,
                    "aliases": disease_stmt.excluded.aliases,
                    "summary": disease_stmt.excluded.summary,
                    "content": disease_stmt.excluded.content,
                    "source_file": disease_stmt.excluded.source_file,
                    "updated_at": sa.text("now()"),
                },
            )
        )
        drug_stmt = sa.dialects.postgresql.insert(DrugModel).values(drug_rows)
        conn.execute(
            drug_stmt.on_conflict_do_update(
                index_elements=[DrugModel.source_index],
                set_={
                    "title": drug_stmt.excluded.title,
                    "aliases": drug_stmt.excluded.aliases,
                    "summary": drug_stmt.excluded.summary,
                    "content": drug_stmt.excluded.content,
                    "source_file": drug_stmt.excluded.source_file,
                    "updated_at": sa.text("now()"),
                },
            )
        )
        vac_stmt = sa.dialects.postgresql.insert(VaccineModel).values(vaccine_rows)
        conn.execute(
            vac_stmt.on_conflict_do_update(
                index_elements=[VaccineModel.source_index],
                set_={
                    "title": vac_stmt.excluded.title,
                    "aliases": vac_stmt.excluded.aliases,
                    "summary": vac_stmt.excluded.summary,
                    "content": vac_stmt.excluded.content,
                    "source_file": vac_stmt.excluded.source_file,
                    "updated_at": sa.text("now()"),
                },
            )
        )

        counters = {
            "users": len(users),
            "user_devices": len(user_devices),
            "refresh_tokens": len(refresh_tokens),
            "families": len(families),
            "profiles": len(profiles),
            "health_details": len(health_details),
            "family_memberships": len(memberships),
            "medicine_inventory": len(medicines),
            "medical_records": len(records),
            "vaccine_history": len(vaccine_history),
            "schedules": len(schedules),
            "schedule_logs": len(schedule_logs),
            "growth_records": len(growth_records),
            "activity_logs": len(activity_logs),
            "diseases": len(disease_rows),
            "drugs": len(drug_rows),
            "vaccines": len(vaccine_rows),
        }

    engine.dispose()
    return counters


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed large Vietnam-family demo data for PostgreSQL")
    parser.add_argument("--families", type=int, default=12, help="Number of families to create")
    parser.add_argument("--users-per-family", type=int, default=4, help="Users per family")
    parser.add_argument("--dictionary-rows", type=int, default=25, help="Rows per medical dictionary table")
    parser.add_argument("--reset", action="store_true", help="Truncate demo tables before seeding")
    parser.add_argument("--chunk-size", type=int, default=50, help="Batch size for executemany inserts")
    args = parser.parse_args()

    counters = seed_demo(
        family_count=max(1, args.families),
        users_per_family=max(2, args.users_per_family),
        reset=args.reset,
        dictionary_rows=max(5, args.dictionary_rows),
        chunk_size=max(10, args.chunk_size),
    )
    print("Seeded Vietnam demo data:")
    for name, count in counters.items():
        print(f"  - {name}: {count}")


if __name__ == "__main__":
    main()
