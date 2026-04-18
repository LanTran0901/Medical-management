from __future__ import annotations

import argparse
import uuid
import random
from datetime import time

from sqlalchemy import create_engine, text

from app.core.config import settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed demo notifications data.")
    parser.add_argument(
        "--user-email",
        default="demo.notification@homemedai.local",
        help="Email for demo user (created if not exists).",
    )
    return parser.parse_args()


def ensure_user(conn, email: str) -> uuid.UUID:
    existing = conn.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": email},
    ).scalar_one_or_none()
    if existing:
        return existing

    user_id = uuid.uuid4()
    conn.execute(
        text(
            """
            INSERT INTO users (id, email, status)
            VALUES (:id, :email, 'active')
            """
        ),
        {"id": user_id, "email": email},
    )
    return user_id


def ensure_family(conn, user_id: uuid.UUID) -> uuid.UUID:
    existing = conn.execute(
        text(
            """
            SELECT id FROM families
            WHERE created_by = :user_id AND family_name = :name
            """
        ),
        {"user_id": user_id, "name": "Demo Notifications Family"},
    ).scalar_one_or_none()
    if existing:
        return existing

    family_id = uuid.uuid4()
    invite_code = f"DEMO{random.randint(1000, 9999)}"
    conn.execute(
        text(
            """
            INSERT INTO families (id, family_name, invite_code, created_by)
            VALUES (:id, :name, :invite_code, :created_by)
            """
        ),
        {
            "id": family_id,
            "name": "Demo Notifications Family",
            "invite_code": invite_code,
            "created_by": user_id,
        },
    )
    return family_id


def ensure_profile(conn, user_id: uuid.UUID) -> uuid.UUID:
    existing = conn.execute(
        text(
            """
            SELECT id FROM profiles
            WHERE owner_user_id = :user_id AND full_name = :name
            """
        ),
        {"user_id": user_id, "name": "Demo User"},
    ).scalar_one_or_none()
    if existing:
        return existing

    profile_id = uuid.uuid4()
    conn.execute(
        text(
            """
            INSERT INTO profiles (id, owner_user_id, full_name)
            VALUES (:id, :owner_user_id, :full_name)
            """
        ),
        {"id": profile_id, "owner_user_id": user_id, "full_name": "Demo User"},
    )
    return profile_id


def ensure_membership(conn, family_id: uuid.UUID, profile_id: uuid.UUID, user_id: uuid.UUID) -> None:
    existing = conn.execute(
        text(
            """
            SELECT id FROM family_memberships
            WHERE family_id = :family_id AND profile_id = :profile_id
            """
        ),
        {"family_id": family_id, "profile_id": profile_id},
    ).scalar_one_or_none()
    if existing:
        return

    membership_id = uuid.uuid4()
    conn.execute(
        text(
            """
            INSERT INTO family_memberships (id, family_id, profile_id, role, added_by)
            VALUES (:id, :family_id, :profile_id, 'OWNER', :added_by)
            """
        ),
        {
            "id": membership_id,
            "family_id": family_id,
            "profile_id": profile_id,
            "added_by": user_id,
        },
    )


def ensure_medicine(conn, family_id: uuid.UUID, name: str) -> uuid.UUID:
    existing = conn.execute(
        text(
            """
            SELECT id FROM medicine_inventory
            WHERE family_id = :family_id AND medicine_name = :name
            """
        ),
        {"family_id": family_id, "name": name},
    ).scalar_one_or_none()
    if existing:
        return existing

    medicine_id = uuid.uuid4()
    conn.execute(
        text(
            """
            INSERT INTO medicine_inventory (id, family_id, medicine_name)
            VALUES (:id, :family_id, :name)
            """
        ),
        {"id": medicine_id, "family_id": family_id, "name": name},
    )
    return medicine_id


def ensure_schedule(
    conn,
    profile_id: uuid.UUID,
    medicine_id: uuid.UUID,
    title: str,
    remind_time: time,
    dosage_per_time: float,
) -> uuid.UUID:
    existing = conn.execute(
        text(
            """
            SELECT id FROM schedules
            WHERE profile_id = :profile_id AND title = :title
            """
        ),
        {"profile_id": profile_id, "title": title},
    ).scalar_one_or_none()
    if existing:
        return existing

    schedule_id = uuid.uuid4()
    conn.execute(
        text(
            """
            INSERT INTO schedules (
                id, profile_id, medicine_id, title, category,
                remind_time, dosage_per_time, rrule, status
            )
            VALUES (
                :id, :profile_id, :medicine_id, :title, 'MEDICINE',
                :remind_time, :dosage_per_time, :rrule, 'ACTIVE'
            )
            """
        ),
        {
            "id": schedule_id,
            "profile_id": profile_id,
            "medicine_id": medicine_id,
            "title": title,
            "remind_time": remind_time,
            "dosage_per_time": dosage_per_time,
            "rrule": "FREQ=DAILY",
        },
    )
    return schedule_id


def insert_schedule_log(conn, schedule_id: uuid.UUID, user_id: uuid.UUID, status: str) -> None:
    conn.execute(
        text(
            """
            INSERT INTO schedule_logs (id, schedule_id, status, action_by)
            VALUES (:id, :schedule_id, :status, :action_by)
            """
        ),
        {
            "id": uuid.uuid4(),
            "schedule_id": schedule_id,
            "status": status,
            "action_by": user_id,
        },
    )


def main() -> None:
    args = parse_args()
    engine = create_engine(settings.POSTGRES_SYNC_URL)

    with engine.begin() as conn:
        user_id = ensure_user(conn, args.user_email)
        family_id = ensure_family(conn, user_id)
        profile_id = ensure_profile(conn, user_id)
        ensure_membership(conn, family_id, profile_id, user_id)

        med1 = ensure_medicine(conn, family_id, "Metformin 500mg")
        med2 = ensure_medicine(conn, family_id, "Amlodipine 5mg")

        sched1 = ensure_schedule(
            conn,
            profile_id,
            med1,
            "Nhac uong thuoc - Metformin",
            time(hour=7, minute=0),
            1.0,
        )
        sched2 = ensure_schedule(
            conn,
            profile_id,
            med1,
            "Nhac uong thuoc - Metformin (toi)",
            time(hour=18, minute=0),
            1.0,
        )
        sched3 = ensure_schedule(
            conn,
            profile_id,
            med2,
            "Nhac uong thuoc - Amlodipine",
            time(hour=9, minute=0),
            1.0,
        )

        insert_schedule_log(conn, sched1, user_id, "CREATED")
        insert_schedule_log(conn, sched2, user_id, "CREATED")
        insert_schedule_log(conn, sched3, user_id, "CREATED")

    print("Seeded demo notifications data.")


if __name__ == "__main__":
    main()
