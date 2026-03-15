from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class NotificationServicePort(ABC):
    """Abstract interface for push notification services."""

    @abstractmethod
    def send_to_device(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[dict[str, str]] = None,
    ) -> str:
        """Send notification to a single device. Returns message ID."""
        raise NotImplementedError

    @abstractmethod
    def send_to_multiple(
        self,
        tokens: list[str],
        title: str,
        body: str,
        data: Optional[dict[str, str]] = None,
    ) -> tuple[int, int, list[str]]:
        """Send notification to multiple devices.
        Returns (success_count, failure_count, list_of_failed_tokens).
        """
        raise NotImplementedError
