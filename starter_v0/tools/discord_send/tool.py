from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT


def send_discord(text: str = "", confirmed: bool = False) -> dict[str, Any]:
    """Send one confirmed plain-text message through a Discord webhook."""
    if not confirmed:
        return {
            "tool": "send_discord",
            "status": "needs_confirmation",
            "message": "Only send after the user explicitly confirms.",
        }

    clean_text = str(text or "").strip()
    if not clean_text:
        return {
            "tool": "send_discord",
            "status": "error",
            "error": "empty_text",
            "message": "Discord message text cannot be empty.",
        }
    if len(clean_text) > 2000:
        return {
            "tool": "send_discord",
            "status": "error",
            "error": "text_too_long",
            "message": "Discord text messages are limited to 2000 characters.",
        }

    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return {
            "tool": "send_discord",
            "status": "error",
            "error": "missing_configuration",
            "message": "Missing DISCORD_WEBHOOK_URL in .env.",
        }
    if not webhook_url.startswith(("https://discord.com/api/webhooks/", "https://discordapp.com/api/webhooks/")):
        return {
            "tool": "send_discord",
            "status": "error",
            "error": "invalid_configuration",
            "message": "DISCORD_WEBHOOK_URL is not a valid Discord webhook URL.",
        }

    try:
        response = requests.post(
            webhook_url,
            json={"content": clean_text, "allowed_mentions": {"parse": []}},
            timeout=TIMEOUT,
        )
        if response.status_code in {401, 403, 404}:
            return {
                "tool": "send_discord",
                "status": "error",
                "error": "webhook_rejected",
                "message": "Discord rejected the webhook. Check that it is active and belongs to the intended channel.",
            }
        response.raise_for_status()
        return {"tool": "send_discord", "status": "sent", "message": "Message sent to Discord."}
    except requests.RequestException:
        return {
            "tool": "send_discord",
            "status": "error",
            "error": "request_failed",
            "message": "Discord request failed. Check network access and webhook configuration.",
        }
