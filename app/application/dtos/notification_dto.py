from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


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


class NotificationListItem(BaseModel):
    id: UUID
    schedule_id: Optional[UUID] = None
    category: str
    status: Optional[str] = None
    lifecycle_status: Optional[str] = None
    occurrence_status: Optional[str] = None
    title: Optional[str] = None
    body: Optional[str] = None
    remind_time: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    snoozed_until: Optional[datetime] = None
    medicine_name: Optional[str] = None
    dosage_per_time: Optional[str] = None
    profile_id: UUID
    profile_name: Optional[str] = None
    family_name: Optional[str] = None


class NotificationsListResponse(BaseModel):
    items: list[NotificationListItem]


class ScheduleComplianceRequest(BaseModel):
    """Record user response to a medicine schedule reminder."""

    outcome: Literal["taken", "skipped"]


class ScheduleComplianceResponse(BaseModel):
    success: bool
    message: str


class ScheduleSnoozeRequest(BaseModel):
    """Snooze a medicine schedule reminder from now by N minutes."""

    minutes: int = Field(default=10, ge=1, le=120)


class ScheduleSnoozeResponse(BaseModel):
    success: bool
    message: str
    snoozed_until: Optional[datetime] = None


class ScheduleDispatchResponse(BaseModel):
    """Result of running the due-schedule FCM dispatcher."""

    processed: int
    sent: int
    skipped_duplicate: int
    errors: int
