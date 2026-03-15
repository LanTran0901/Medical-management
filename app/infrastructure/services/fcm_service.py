from __future__ import annotations

import logging
from typing import Optional

from app.application.ports.notification_port import NotificationServicePort

logger = logging.getLogger(__name__)


class FCMService(NotificationServicePort):
    """Firebase Cloud Messaging implementation of NotificationServicePort."""

    def __init__(self) -> None:
        # firebase_admin must be initialized before using this service
        from firebase_admin import messaging  # noqa: F401

        self._messaging = messaging

    def send_to_device(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[dict[str, str]] = None,
    ) -> str:
        message = self._messaging.Message(
            notification=self._messaging.Notification(title=title, body=body),
            data=data,
            token=token,
        )
        response = self._messaging.send(message)
        logger.info("FCM sent to device, message_id=%s", response)
        return response

    def send_to_multiple(
        self,
        tokens: list[str],
        title: str,
        body: str,
        data: Optional[dict[str, str]] = None,
    ) -> tuple[int, int, list[str]]:
        messages = [
            self._messaging.Message(
                notification=self._messaging.Notification(title=title, body=body),
                data=data,
                token=token,
            )
            for token in tokens
        ]

        response = self._messaging.send_each(messages)

        failed_tokens: list[str] = []
        for i, send_response in enumerate(response.responses):
            if send_response.exception is not None:
                failed_tokens.append(tokens[i])
                logger.warning(
                    "FCM failed for token %s: %s",
                    tokens[i][:20],
                    send_response.exception,
                )

        success_count = response.success_count
        failure_count = response.failure_count
        logger.info(
            "FCM batch: %d success, %d failed", success_count, failure_count
        )
        return success_count, failure_count, failed_tokens
