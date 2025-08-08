import json
from typing import Any, Dict, Optional

import openai

from core.config import settings

from .base import BaseAIProvider


class OpenAIProvider(BaseAIProvider):
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def process_intent(
        self, text: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        system_prompt = """
        You are an AI assistant for people with disabilities. Analyze the user input and extract:
        1. Intent (task type): restaurant_booking, salon_booking, medicine_reminder, family_notification, or other
        2. Key details needed for the task
        3. Accessibility considerations
        4. Confidence level (0-1)
        
        Available task types:
        - restaurant_booking: Book a table at a restaurant
        - salon_booking: Book an appointment at a hair salon
        - medicine_reminder: Set up medication reminders
        - family_notification: Notify family members about actions
        - unknown: Cannot determine intent
        
        Return JSON format:
        {
            "intent": "task_type",
            "confidence": 0.9,
            "details": {"key": "value"},
            "accessibility_notes": "any special considerations",
            "can_perform": true/false,
            "reason": "explanation if cannot perform"
        }
        """

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"User input: {text}"},
                ],
                temperature=0.2,
            )

            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            return {
                "intent": "unknown",
                "confidence": 0.0,
                "details": {},
                "accessibility_notes": "",
                "can_perform": False,
                "reason": f"Error processing input: {str(e)}",
            }

    async def generate_response(
        self, prompt: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant for people with disabilities. Be clear, supportive, and provide step-by-step guidance when needed.",
                }
            ]

            if context:
                messages.append(
                    {"role": "system", "content": f"Context: {json.dumps(context)}"}
                )

            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo", messages=messages, temperature=0.3
            )

            return response.choices[0].message.content
        except Exception as e:
            return f"I apologize, but I encountered an error while processing your request: {str(e)}"

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
