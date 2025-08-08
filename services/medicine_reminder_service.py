import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import httpx

from .base import BaseTaskService


class MedicineReminderService(BaseTaskService):
    async def validate_input(self, details: Dict[str, Any]) -> Dict[str, Any]:
        required_fields = ["medicine_name", "schedule"]
        missing_fields = []

        for field in required_fields:
            if field not in details or not details[field]:
                missing_fields.append(field)

        if missing_fields:
            return {
                "valid": False,
                "missing_fields": missing_fields,
                "message": f"Missing required information: {', '.join(missing_fields)}",
            }

        return {"valid": True, "message": "All required information provided"}

    async def execute(
        self, details: Dict[str, Any], user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        try:
            reminder_data = {
                "medicine": details["medicine_name"],
                "dosage": details.get("dosage", "As prescribed"),
                "schedule": details["schedule"],
                "start_date": details.get(
                    "start_date", datetime.now().date().isoformat()
                ),
                "end_date": details.get("end_date"),
                "user_id": user_context.get("user_id"),
            }

            # In production, this would create calendar events or push notifications
            result = {
                "success": True,
                "reminder_id": f"MED_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "message": f"Successfully set up reminder for {details['medicine_name']} with schedule: {details['schedule']}",
                "details": reminder_data,
                "next_reminder": "Will remind according to your schedule",
            }

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to set up medicine reminder",
            }
