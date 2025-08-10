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
            # Create reminder instead of just storing data
            from database import SessionLocal
            from services.reminder_service import ReminderService

            db = SessionLocal()
            reminder_service = ReminderService()

            # Parse schedule from natural language to pattern
            schedule_pattern = self._parse_medicine_schedule(details["schedule"])

            reminder_data = {
                "user_id": user_context.get("user_id"),
                "reminder_type": "medicine",
                "title": f"Take {details['medicine_name']}",
                "message": f"Time to take your {details['medicine_name']} - {details.get('dosage', 'As prescribed')}",
                "schedule_pattern": schedule_pattern,
                "webhook_url": user_context.get("webhook_url"),
            }

            reminder_result = await reminder_service.create_reminder(reminder_data, db)
            db.close()

            if reminder_result.get("success"):
                result = {
                    "success": True,
                    "reminder_id": reminder_result["reminder_id"],
                    "message": f"Successfully set up reminder for {details['medicine_name']} with schedule: {details['schedule']}",
                    "details": {
                        "medicine": details["medicine_name"],
                        "dosage": details.get("dosage", "As prescribed"),
                        "schedule": details["schedule"],
                        "next_reminder": reminder_result.get("next_reminder_at"),
                    },
                }
            else:
                result = {
                    "success": False,
                    "error": reminder_result.get("error"),
                    "message": "Failed to set up medicine reminder",
                }

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to set up medicine reminder",
            }

    def _parse_medicine_schedule(self, schedule: str) -> str:
        """Convert natural language schedule to pattern"""
        schedule = schedule.lower().strip()

        # Common medicine schedules
        if "once a day" in schedule or "daily" in schedule:
            if "morning" in schedule:
                return "daily_at_09:00"
            elif "evening" in schedule or "night" in schedule:
                return "daily_at_21:00"
            else:
                return "daily_at_12:00"

        if "twice a day" in schedule or "every 12 hours" in schedule:
            return "every_12_hours"

        if "three times a day" in schedule or "every 8 hours" in schedule:
            return "every_8_hours"

        if "four times a day" in schedule or "every 6 hours" in schedule:
            return "every_6_hours"

        if "weekly" in schedule:
            return "weekly_monday_09:00"  # Default to Monday morning

        # Default to daily
        return "daily_at_12:00"
