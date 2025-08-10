from typing import Any, Dict, Optional

from ai_providers.base import BaseAIProvider
from core.task_config import SERVICE_MAP
from schemas.intent import IntentSchema


class IntentProcessorService:
    def __init__(self, provider: BaseAIProvider):
        """
        service_map: {intent_name: service_name}
        """
        self.provider = provider
        self.service_map = SERVICE_MAP

    async def process_intent(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        system_prompt = """
            You are an AI assistant for people with disabilities. Analyze the user input and extract:
            1. Intent (task type): restaurant_booking, salon_booking, medicine_reminder, family_notification, or other
            2. Key details needed for the task, as per function args.
            3. Accessibility considerations
            4. Confidence level (0-1)
            
            Available task types:
            - restaurant_booking: Book a table at a restaurant
            - salon_booking: Book an appointment at a hair salon
            - medicine_reminder: Set up medication reminders
            - family_notification: Notify family members about actions
            - unknown: Cannot determine intent
        """

        try:
            output_schema = IntentSchema
            user_prompt = text
            response = await self.provider.get_response(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                output_schema=output_schema,
            )
            return response
        except Exception as e:
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "details": {},
                "accessibility_notes": "",
                "can_perform": False,
                "reason": f"Error processing input: {str(e)}",
            }

    async def get_service_for_intent(self, user_input: str) -> str:
        intent_obj = await self.detect_intent(user_input)
        if intent_obj.intent in self.service_map:
            intent_obj.service_name = self.service_map[intent_obj.intent]
        else:
            intent_obj.service_name = None
        return intent_obj

    async def validate_task_feasibility(
        self, task_type: str, details: Dict[str, Any]
    ) -> Dict[str, Any]:
        supported_tasks = [
            "restaurant_booking",
            "salon_booking",
            "medicine_reminder",
            "family_notification",
        ]

        if task_type not in supported_tasks:
            return {
                "feasible": False,
                "reason": f"I don't know how to perform '{task_type}' tasks yet.",
                "suggestion": f"I can help with: {', '.join(supported_tasks)}",
            }

        # Add specific validation logic for each task type
        if task_type == "restaurant_booking":
            required_fields = ["restaurant_name", "date", "time", "party_size"]
            missing_fields = [
                field for field in required_fields if field not in details
            ]

            if missing_fields:
                return {
                    "feasible": True,
                    "needs_clarification": True,
                    "missing_info": missing_fields,
                    "reason": f"I need more information: {', '.join(missing_fields)}",
                }

        return {"feasible": True, "reason": "Task can be performed"}
