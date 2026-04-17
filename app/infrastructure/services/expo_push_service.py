from __future__ import annotations

import logging
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

# Expo Push API (works with ExponentPushToken[...] from expo-notifications)
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def _stringify_data(data: Optional[dict[str, str]]) -> dict[str, str]:
    if not data:
        return {}
    out: dict[str, str] = {}
    for k, v in data.items():
        out[str(k)] = v if isinstance(v, str) else str(v)
    return out


def send_expo_push_batch(
    tokens: list[str],
    title: str,
    body: str,
    data: Optional[dict[str, str]] = None,
    *,
    access_token: Optional[str] = None,
) -> tuple[int, int, list[str]]:
    """Send to Expo Push API. Returns (success_count, failure_count, failed_tokens)."""
    if not tokens:
        return 0, 0, []

    payload: list[dict[str, Any]] = []
    str_data = _stringify_data(data)
    for to in tokens:
        msg: dict[str, Any] = {
            "to": to,
            "title": title,
            "body": body,
            "sound": "default",
        }
        if str_data:
            msg["data"] = str_data
        payload.append(msg)

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    try:
        resp = requests.post(
            EXPO_PUSH_URL,
            json=payload,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.exception("Expo Push HTTP error: %s", e)
        return 0, len(tokens), list(tokens)

    try:
        body_json = resp.json()
    except ValueError:
        logger.error("Expo Push invalid JSON: %s", resp.text[:500])
        return 0, len(tokens), list(tokens)

    # Response shape: {"data": [{"status": "ok", "id": "..."}, ...]} or per-item errors
    items = body_json.get("data")
    if not isinstance(items, list):
        logger.error("Expo Push unexpected response: %s", body_json)
        return 0, len(tokens), list(tokens)

    failed: list[str] = []
    success = 0
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            failed.append(tokens[i] if i < len(tokens) else "")
            continue
        status = item.get("status")
        if status == "ok":
            success += 1
        else:
            tok = tokens[i] if i < len(tokens) else ""
            failed.append(tok)
            logger.warning("Expo Push ticket error: %s", item)

    failure_count = len(failed)
    return success, failure_count, failed
