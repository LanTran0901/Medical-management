from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class SendNotificationRequest(BaseModel):
    """Send notification to all devices of the authenticated user (no user_id in body)."""

    title: str
    body: str
    data: Optional[dict[str, str]] = None


class SendNotificationToDeviceRequest(BaseModel):
    """Send notification to a specific device by FCM token."""
    fcm_token: str
    title: str
    body: str
    data: Optional[dict[str, str]] = None


class NotificationResponse(BaseModel):
    success: bool
    message: str
    failed_tokens: list[str] = []
