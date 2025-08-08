from typing import Any, Dict, Optional

from .base import BaseTaskService
from .family_notificaiton_service import FamilyNotificationService
from .medicine_reminder_service import MedicineReminderService
from .restraunt_booking_service import RestaurantBookingService
from .salon_booking_service import SalonBookingService


class TaskManager:
    def __init__(self):
        self.services: Dict[str, BaseTaskService] = {
            "restaurant_booking": RestaurantBookingService(),
            "salon_booking": SalonBookingService(),
            "medicine_reminder": MedicineReminderService(),
            "family_notification": FamilyNotificationService(),
        }

    def get_service(self, task_type: str) -> Optional[BaseTaskService]:
        return self.services.get(task_type)

    async def execute_task(
        self, task_type: str, details: Dict[str, Any], user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        service = self.get_service(task_type)

        if not service:
            return {
                "success": False,
                "error": f"Unsupported task type: {task_type}",
                "available_tasks": list(self.services.keys()),
            }

        # Validate input
        validation_result = await service.validate_input(details)
        if not validation_result.get("valid", False):
            return {
                "success": False,
                "error": "Invalid input",
                "validation_details": validation_result,
            }

        # Execute task
        result = await service.execute(details, user_context)
        return result

    def register_service(self, task_type: str, service: BaseTaskService):
        """Register a new task service for extensibility"""
        self.services[task_type] = service

    def get_available_tasks(self) -> list:
        return list(self.services.keys())
