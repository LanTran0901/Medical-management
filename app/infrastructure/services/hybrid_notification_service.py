from __future__ import annotations

import logging
from typing import Optional

from app.application.ports.notification_port import NotificationServicePort
from app.core.config import settings
from app.infrastructure.services.expo_push_service import send_expo_push_batch
from app.infrastructure.services.fcm_service import FCMService

logger = logging.getLogger(__name__)

EXPO_TOKEN_PREFIX = "ExponentPushToken["


def is_expo_push_token(token: str) -> bool:
    return bool(token and token.strip().startswith(EXPO_TOKEN_PREFIX))


class HybridNotificationService(NotificationServicePort):
    """Routes ExponentPushToken to Expo Push API; native FCM tokens to Firebase."""

    def __init__(self) -> None:
        self._fcm: FCMService | None = None

    def _fcm_service(self) -> FCMService:
        if self._fcm is None:
            self._fcm = FCMService()
        return self._fcm

    def send_to_device(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[dict[str, str]] = None,
        *,
        android_channel_id: Optional[str] = None,
        android_sound: Optional[str] = None,
    ) -> str:
        if is_expo_push_token(token):
            failed = send_expo_push_batch(
                [token],
                title,
                body,
                data,
                access_token=settings.expo_push_access_token,
            )[2]
            if failed:
                raise RuntimeError("Expo Push failed for token")
            return "expo-ok"
        return self._fcm_service().send_to_device(
            token,
            title,
            body,
            data,
            android_channel_id=android_channel_id,
            android_sound=android_sound,
        )

    def send_to_multiple(
        self,
        tokens: list[str],
        title: str,
        body: str,
        data: Optional[dict[str, str]] = None,
        *,
        android_channel_id: Optional[str] = None,
        android_sound: Optional[str] = None,
    ) -> tuple[int, int, list[str]]:
        expo_tokens = [t for t in tokens if is_expo_push_token(t)]
        fcm_tokens = [t for t in tokens if not is_expo_push_token(t)]

        failed_all: list[str] = []
        success_total = 0
        failure_total = 0

        if expo_tokens:
            s, f, failed = send_expo_push_batch(
                expo_tokens,
                title,
                body,
                data,
                access_token=settings.expo_push_access_token,
            )
            success_total += s
            failure_total += f
            failed_all.extend(failed)

        if fcm_tokens:
            s, f, failed = self._fcm_service().send_to_multiple(
                fcm_tokens,
                title,
                body,
                data,
                android_channel_id=android_channel_id,
                android_sound=android_sound,
            )
            success_total += s
            failure_total += f
            failed_all.extend(failed)

        return success_total, failure_total, failed_all
