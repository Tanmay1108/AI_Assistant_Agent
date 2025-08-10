import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

import httpx
import structlog

from core.config import settings

logger = structlog.get_logger()


class WebhookService:
    def __init__(self):
        self.timeout = settings.WEBHOOK_TIMEOUT

    async def send_webhook(
        self, url: str, payload: Dict[str, Any], webhook_type: str = "notification"
    ) -> bool:
        """Send webhook notification"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": "AIAgent-Webhook/1.0",
                    "X-Webhook-Type": webhook_type,
                }

                response = await client.post(url, json=payload, headers=headers)

                if response.status_code == 200:
                    logger.info(f"Webhook sent successfully to {url}")
                    return True
                else:
                    logger.warning(
                        f"Webhook failed with status {response.status_code}: {url}"
                    )
                    return False

        except Exception as e:
            logger.error(f"Webhook error for {url}: {e}")
            return False

    async def send_completion_webhook(
        self, url: str, task_id: int, result: Dict[str, Any]
    ):
        """Send task completion webhook"""
        payload = {
            "event": "task_completed",
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "result": result,
            "success": result.get("success", False),
        }

        return await self.send_webhook(url, payload, "task_completion")

    async def send_failure_webhook(
        self, url: str, task_id: int, error_info: Dict[str, Any]
    ):
        """Send task failure webhook"""
        payload = {
            "event": "task_failed",
            "task_id": task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "error": error_info.get("error", "Unknown error"),
            "message": error_info.get("message", "Task failed"),
            "retry_info": error_info.get("retry_info"),
        }

        return await self.send_webhook(url, payload, "task_failure")

    async def send_reminder_webhook(self, url: str, reminder_data: Dict[str, Any]):
        """Send reminder notification webhook"""
        payload = {
            "event": "reminder",
            "reminder_id": reminder_data.get("reminder_id"),
            "user_id": reminder_data.get("user_id"),
            "timestamp": datetime.utcnow().isoformat(),
            "title": reminder_data.get("title"),
            "message": reminder_data.get("message"),
            "reminder_type": reminder_data.get("reminder_type"),
        }

        return await self.send_webhook(url, payload, "reminder")
