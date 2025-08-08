import json
from datetime import datetime
from typing import Any, Dict

from sqlalchemy.orm import Session

from ai_providers.router import AIProviderRouter
from database.postgres.models.common import TaskStatus
from database.postgres.models.task import Task
from database.postgres.models.user import User

from .feedback_service import FeedbackService
from .task_manager import TaskManager


class AgentOrchestrator:
    def __init__(
        self,
        ai_router: AIProviderRouter,
        task_manager: TaskManager,
        feedback_service: FeedbackService,
    ):
        self.ai_router = ai_router
        self.task_manager = task_manager
        self.feedback_service = feedback_service

    async def process_request(
        self, request_data: Dict[str, Any], db: Session
    ) -> Dict[str, Any]:
        """Main orchestration method for processing user requests"""

        # Get user context
        user = db.query(User).filter(User.id == request_data["user_id"]).first()
        if not user:
            return {
                "success": False,
                "error": "User not found",
                "message": "Please register first before making requests",
            }

        user_context = {
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "phone": user.phone,
            "disability_type": user.disability_type,
            "accessibility_preferences": json.loads(user.accessibility_preferences),
            "family_contacts": json.loads(user.family_contacts),
        }

        # Create task record
        task = Task(
            user_id=user.id,
            input_text=request_data["input_text"],
            status=TaskStatus.PENDING,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        try:
            # Step 1: Process intent with AI
            task.status = TaskStatus.IN_PROGRESS
            db.commit()

            intent_result = await self.ai_router.process_with_fallback(
                "process_intent",
                request_data["input_text"],
                {"user_context": user_context},
            )

            task.processed_intent = json.dumps(intent_result)
            task.ai_provider_used = self.ai_router.default_provider
            db.commit()

            # Step 2: Check if task can be performed
            if not intent_result.get("can_perform", True):
                task.status = TaskStatus.FAILED
                task.error_message = intent_result.get(
                    "reason", "Cannot perform this task"
                )
                db.commit()

                response = await self._generate_rejection_response(
                    intent_result,
                    user_context,
                    request_data.get("accessibility_mode", False),
                )
                return response

            # Step 3: Validate task feasibility
            feasibility = await self.ai_router.process_with_fallback(
                "validate_task_feasibility",
                intent_result["intent"],
                intent_result.get("details", {}),
            )

            if not feasibility.get("feasible", False):
                task.status = TaskStatus.FAILED
                task.error_message = feasibility.get("reason", "Task not feasible")
                db.commit()

                response = await self._generate_rejection_response(
                    feasibility,
                    user_context,
                    request_data.get("accessibility_mode", False),
                )
                return response

            # Step 4: Handle clarification if needed
            if feasibility.get("needs_clarification", False):
                task.status = TaskStatus.PENDING
                db.commit()

                return await self._generate_clarification_response(
                    feasibility,
                    user_context,
                    task.id,
                    request_data.get("accessibility_mode", False),
                )

            # Step 5: Execute the task
            execution_result = await self.task_manager.execute_task(
                intent_result["intent"], intent_result.get("details", {}), user_context
            )

            task.execution_details = json.dumps(execution_result)

            if execution_result.get("success", False):
                task.status = TaskStatus.COMPLETED
                task.result = json.dumps({"success": True, "details": execution_result})
                task.completed_at = datetime.utcnow()

                # Step 6: Notify family if this was a significant action
                if intent_result["intent"] in ["restaurant_booking", "salon_booking"]:
                    await self._notify_family_about_task(
                        user_context, intent_result, execution_result
                    )

            else:
                task.status = TaskStatus.FAILED
                task.error_message = execution_result.get(
                    "error", "Task execution failed"
                )

            db.commit()

            # Step 7: Generate response
            response = await self._generate_completion_response(
                intent_result,
                execution_result,
                user_context,
                task.id,
                request_data.get("accessibility_mode", False),
            )

            return response

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            db.commit()

            return {
                "success": False,
                "error": str(e),
                "message": "I encountered an error while processing your request. Please try again.",
                "task_id": task.id,
            }

    async def _generate_rejection_response(
        self,
        result: Dict[str, Any],
        user_context: Dict[str, Any],
        accessibility_mode: bool,
    ) -> Dict[str, Any]:
        """Generate a helpful rejection response"""

        # Get accessibility guidance
        accessibility_guidance = await self.feedback_service.get_accessibility_guidance(
            user_context.get("disability_type", ""), "general"
        )

        prompt = f"""
        The user requested something I cannot do. Generate a helpful, empathetic response that:
        1. Explains clearly why I cannot help
        2. Suggests alternatives if possible
        3. Remains supportive and encouraging
        
        Reason I cannot help: {result.get('reason', 'Unknown')}
        Available alternatives: {result.get('suggestion', 'None specified')}
        User disability type: {user_context.get('disability_type', 'Not specified')}
        Accessibility mode: {accessibility_mode}
        
        {"Use simple, clear language with step-by-step structure." if accessibility_mode else ""}
        """

        try:
            response_text = await self.ai_router.process_with_fallback(
                "generate_response", prompt, user_context
            )
        except Exception:
            response_text = f"I'm sorry, but I cannot help with this request. {result.get('reason', '')}"

        return {
            "success": False,
            "message": response_text,
            "reason": result.get("reason"),
            "alternatives": result.get("suggestion"),
            "accessibility_guidance": (
                accessibility_guidance if accessibility_mode else None
            ),
        }

    async def _generate_clarification_response(
        self,
        feasibility: Dict[str, Any],
        user_context: Dict[str, Any],
        task_id: int,
        accessibility_mode: bool,
    ) -> Dict[str, Any]:
        """Generate a clarification request"""

        missing_info = feasibility.get("missing_info", [])

        prompt = f"""
        I need more information from the user to complete their request. Generate a helpful response that:
        1. Explains what additional information is needed
        2. Asks specific questions to get the missing details
        3. Provides examples if helpful
        
        Missing information: {', '.join(missing_info)}
        User disability type: {user_context.get('disability_type', 'Not specified')}
        
        {"Use simple questions with clear examples. Number each question." if accessibility_mode else ""}
        """

        try:
            response_text = await self.ai_router.process_with_fallback(
                "generate_response", prompt, user_context
            )
        except Exception:
            response_text = f"I need more information to help you. Please provide: {', '.join(missing_info)}"

        return {
            "success": False,
            "needs_clarification": True,
            "message": response_text,
            "missing_info": missing_info,
            "task_id": task_id,
        }

    async def _generate_completion_response(
        self,
        intent_result: Dict[str, Any],
        execution_result: Dict[str, Any],
        user_context: Dict[str, Any],
        task_id: int,
        accessibility_mode: bool,
    ) -> Dict[str, Any]:
        """Generate a completion response"""

        if execution_result.get("success", False):
            # Success response
            prompt = f"""
            The user's request was completed successfully. Generate a clear, positive response that:
            1. Confirms what was accomplished
            2. Provides relevant details (confirmation numbers, dates, etc.)
            3. Offers next steps if appropriate
            
            Task type: {intent_result['intent']}
            Result details: {execution_result.get('message', '')}
            Confirmation info: {execution_result.get('details', {})}
            
            {"Use clear, simple language with important details highlighted." if accessibility_mode else ""}
            """

            try:
                response_text = await self.ai_router.process_with_fallback(
                    "generate_response", prompt, user_context
                )
            except Exception:
                response_text = f"✅ {execution_result.get('message', 'Task completed successfully!')}"

            # Get accessibility guidance for successful completion
            accessibility_guidance = None
            if accessibility_mode:
                accessibility_guidance = (
                    await self.feedback_service.get_accessibility_guidance(
                        user_context.get("disability_type", ""), intent_result["intent"]
                    )
                )

            return {
                "success": True,
                "message": response_text,
                "task_id": task_id,
                "details": execution_result.get("details", {}),
                "confirmation_info": {
                    "booking_id": execution_result.get("booking_id"),
                    "confirmation_code": execution_result.get("confirmation_code"),
                },
                "accessibility_guidance": accessibility_guidance,
            }
        else:
            # Failure response
            prompt = f"""
            The user's request failed to complete. Generate a helpful, empathetic response that:
            1. Acknowledges the problem
            2. Explains what went wrong (if appropriate)
            3. Suggests what to try next
            
            Task type: {intent_result['intent']}
            Error: {execution_result.get('error', 'Unknown error')}
            
            {"Use encouraging language and provide clear next steps." if accessibility_mode else ""}
            """

            try:
                response_text = await self.ai_router.process_with_fallback(
                    "generate_response", prompt, user_context
                )
            except Exception:
                response_text = f"I encountered a problem: {execution_result.get('message', 'Something went wrong')}. Please try again or contact support."

            return {
                "success": False,
                "message": response_text,
                "task_id": task_id,
                "error": execution_result.get("error"),
                "suggested_action": "Please try again with more specific details or contact support.",
            }

    async def _notify_family_about_task(
        self,
        user_context: Dict[str, Any],
        intent_result: Dict[str, Any],
        execution_result: Dict[str, Any],
    ):
        """Automatically notify family about important completed tasks"""
        try:
            task_type = intent_result["intent"]

            if task_type == "restaurant_booking":
                message = f"{user_context['name']} has booked a restaurant table: {execution_result.get('message', 'Booking confirmed')}"
            elif task_type == "salon_booking":
                message = f"{user_context['name']} has booked a salon appointment: {execution_result.get('message', 'Appointment confirmed')}"
            else:
                return  # Don't notify for other task types automatically

            # Use the family notification service
            notification_result = await self.task_manager.execute_task(
                "family_notification", {"message": message}, user_context
            )

            # Log notification result (in production, use proper logging)
            print(f"Family notification result: {notification_result}")

        except Exception as e:
            # Don't fail the main task if family notification fails
            print(f"Failed to send family notification: {e}")
