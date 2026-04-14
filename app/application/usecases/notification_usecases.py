from __future__ import annotations

from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.notification_dto import (
    SendNotificationRequest,
    SendNotificationToDeviceRequest,
    NotificationResponse,
    NotificationsListResponse,
    NotificationListItem,
)
from app.application.ports.auth_port import AuthRepositoryPort
from app.application.ports.notification_port import NotificationServicePort


class SendNotificationToUserUseCase:
    """Send push notification to all devices of a specific user."""

    def __init__(
        self,
        auth_repository: AuthRepositoryPort,
        notification_service: NotificationServicePort,
    ):
        self.auth_repository = auth_repository
        self.notification_service = notification_service

    async def execute(
        self, request: SendNotificationRequest, sender_user_id: UUID
    ) -> NotificationResponse:
        devices = await self.auth_repository.get_devices_by_user_id(sender_user_id)

        fcm_tokens = [d.fcm_token for d in devices if d.fcm_token]

        if not fcm_tokens:
            return NotificationResponse(
                success=False,
                message="User has no devices with FCM token registered.",
            )

        # Add target_user_id to data payload for frontend routing
        payload_data = request.data or {}
        payload_data["target_user_id"] = str(sender_user_id)

        if len(fcm_tokens) == 1:
            try:
                self.notification_service.send_to_device(
                    fcm_tokens[0], request.title, request.body, payload_data
                )
                return NotificationResponse(success=True, message="Notification sent.")
            except Exception as e:
                return NotificationResponse(
                    success=False,
                    message=f"Failed to send: {str(e)}",
                    failed_tokens=fcm_tokens,
                )

        success_count, failure_count, failed_tokens = (
            self.notification_service.send_to_multiple(
                fcm_tokens, request.title, request.body, payload_data
            )
        )

        return NotificationResponse(
            success=failure_count == 0,
            message=f"Sent to {success_count}/{success_count + failure_count} devices.",
            failed_tokens=failed_tokens,
        )


class SendNotificationToDeviceUseCase:
    """Send push notification to a single device by FCM token (must belong to sender)."""

    def __init__(
        self,
        auth_repository: AuthRepositoryPort,
        notification_service: NotificationServicePort,
    ):
        self.auth_repository = auth_repository
        self.notification_service = notification_service

    async def execute(
        self, request: SendNotificationToDeviceRequest, sender_user_id: UUID
    ) -> NotificationResponse:
        owns = await self.auth_repository.user_owns_fcm_token(
            sender_user_id, request.fcm_token
        )
        if not owns:
            raise ValueError("FCM token is not registered for this user.")

        try:
            self.notification_service.send_to_device(
                request.fcm_token, request.title, request.body, request.data
            )
            return NotificationResponse(success=True, message="Notification sent.")
        except Exception as e:
            return NotificationResponse(
                success=False,
                message=f"Failed to send: {str(e)}",
                failed_tokens=[request.fcm_token],
            )


class ListNotificationsUseCase:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def execute(self, user_id: UUID) -> NotificationsListResponse:
        query = text(
            """
            SELECT
                s.id AS schedule_id,
                s.category::text AS category,
                                s.status::text AS lifecycle_status,
                                latest_log.status AS occurrence_status,
                s.title AS title,
                s.remind_time AS remind_time,
                s.dosage_per_time AS dosage_per_time,
                                so.snooze_until_utc AS snoozed_until,
                mi.medicine_name AS medicine_name,
                p.id AS profile_id,
                p.full_name AS profile_name,
                f.family_name AS family_name
            FROM schedules s
            JOIN profiles p ON p.id = s.profile_id
            LEFT JOIN medicine_inventory mi ON mi.id = s.medicine_id
            LEFT JOIN families f ON f.id = mi.family_id
                        LEFT JOIN LATERAL (
                                SELECT sl.status
                                FROM schedule_logs sl
                                WHERE sl.schedule_id = s.id
                                    AND (sl.action_time AT TIME ZONE 'UTC')::date = (now() AT TIME ZONE 'UTC')::date
                                ORDER BY sl.action_time DESC
                                LIMIT 1
                        ) latest_log ON TRUE
                        LEFT JOIN LATERAL (
                                SELECT o.snooze_until_utc
                                FROM schedule_snooze_overrides o
                                WHERE o.schedule_id = s.id
                                    AND o.occurrence_date = (now() AT TIME ZONE 'UTC')::date
                                    AND o.consumed_at IS NULL
                                ORDER BY o.created_at DESC
                                LIMIT 1
                        ) so ON TRUE
            WHERE s.category = 'MEDICINE'
              AND (p.owner_user_id = :user_id OR p.linked_user_id = :user_id)
            ORDER BY s.remind_time NULLS LAST
            """
        )

        result = await self.session.execute(query, {"user_id": user_id})
        rows = result.mappings().all()

        today = datetime.now(timezone.utc).date()
        items: list[NotificationListItem] = []
        for row in rows:
            remind_time = row.get("remind_time")
            scheduled_at = None
            if remind_time is not None:
                scheduled_at = datetime.combine(
                    today, remind_time, tzinfo=timezone.utc
                )
            remind_time_str = (
                remind_time.strftime("%H:%M") if remind_time is not None else None
            )
            dosage_value = row.get("dosage_per_time")

            occurrence_status = row.get("occurrence_status")
            snoozed_until = row.get("snoozed_until")
            if snoozed_until is not None:
                occurrence_status = "SNOOZED"

            lifecycle_status = row.get("lifecycle_status")
            status_compat = lifecycle_status
            if occurrence_status == "TAKEN":
                status_compat = "COMPLETED"
            elif occurrence_status == "SKIPPED":
                status_compat = "PAUSED"
            elif occurrence_status == "SNOOZED":
                status_compat = "SNOOZED"

            items.append(
                NotificationListItem(
                    id=row["schedule_id"],
                    schedule_id=row["schedule_id"],
                    category=row.get("category") or "MEDICINE",
                    status=status_compat,
                    lifecycle_status=lifecycle_status,
                    occurrence_status=occurrence_status,
                    title=row.get("title") or "Nhac uong thuoc",
                    body=row.get("medicine_name"),
                    remind_time=remind_time_str,
                    scheduled_at=scheduled_at,
                    snoozed_until=snoozed_until,
                    medicine_name=row.get("medicine_name"),
                    dosage_per_time=str(dosage_value) if dosage_value is not None else None,
                    profile_id=row["profile_id"],
                    profile_name=row.get("profile_name"),
                    family_name=row.get("family_name"),
                )
            )

        return NotificationsListResponse(items=items)
