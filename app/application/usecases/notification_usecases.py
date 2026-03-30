from __future__ import annotations

from uuid import UUID

from app.application.dtos.notification_dto import (
    SendNotificationRequest,
    SendNotificationToDeviceRequest,
    NotificationResponse,
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
