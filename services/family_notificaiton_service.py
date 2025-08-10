import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx

from .base import BaseTaskService


class FamilyNotificationService(BaseTaskService):
    async def validate_input(self, details: Dict[str, Any]) -> Dict[str, Any]:
        if "message" not in details or not details["message"]:
            return {
                "valid": False,
                "missing_fields": ["message"],
                "message": "Please provide a message to send to family members",
            }

        return {"valid": True, "message": "Notification message provided"}

    async def execute(
        self, details: Dict[str, Any], user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            family_contacts = user_context.get("family_contacts", [])

            if not family_contacts:
                return {
                    "success": False,
                    "message": "No family contacts configured. Please add family members first.",
                }

            # Send webhooks to family members
            from services.webhook_service import WebhookService

            webhook_service = WebhookService()

            sent_count = 0
            failed_contacts = []

            for contact in family_contacts:
                webhook_url = contact.get("webhook_url")
                if webhook_url:
                    notification_data = {
                        "message": details["message"],
                        "sender_name": user_context.get("name", "User"),
                        "sender_id": user_context.get("user_id"),
                        "timestamp": datetime.now().isoformat(),
                        "contact_name": contact.get("name", "Family Member"),
                    }

                    success = await webhook_service.send_webhook(
                        webhook_url, notification_data, "family_notification"
                    )

                    if success:
                        sent_count += 1
                    else:
                        failed_contacts.append(contact.get("name", "Unknown"))

            if sent_count > 0:
                result = {
                    "success": True,
                    "notification_id": f"FAM_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "message": f"Successfully notified {sent_count} family members: {details['message']}",
                    "details": {
                        "sent_to": sent_count,
                        "failed": len(failed_contacts),
                        "failed_contacts": failed_contacts,
                    },
                }
            else:
                result = {
                    "success": False,
                    "message": "Failed to notify any family members. Check webhook configurations.",
                    "details": {"failed_contacts": failed_contacts},
                }

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to send family notification",
            }
