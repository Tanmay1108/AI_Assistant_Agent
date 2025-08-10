import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import HTTPException

from ai_providers.router import AIProviderRouter
from common.exceptions import ValidationException
from core.config import settings
from database.postgres.postgres_database import PostgresDatabase
from database.postgres.repositories.task import TaskRepository
from database.postgres.repositories.user import UserRepository
from schemas.task import QueuedTask, TaskResponse, TaskStatusEnum
from services.feedback_service import FeedbackService
from services.intent_processing_service import IntentProcessorService
from services.task_manager import TaskManager
from services.webhook_service import WebhookService

logger = logging.getLogger(__name__)


class TaskService:
    def __init__(self, task_queue):
        self.task_queue = task_queue
        self.ai_router = AIProviderRouter()
        self.task_manager = TaskManager()
        self.feedback_service = FeedbackService(self.ai_router)
        self.webhook_service = WebhookService()
        self.intent_processing_service = IntentProcessorService(
            provider=self.ai_router.default_provider
        )

    async def create_task(self, request_data: Dict[str, Any]) -> TaskResponse:
        async with PostgresDatabase.get_session() as session:
            try:
                task_repo = TaskRepository(session)
                user_repo = UserRepository(session=session)

                if not request_data.get("user_id"):
                    raise ValidationException("User ID is required to create a task")

                user = await user_repo.get_user_by_id(request_data["user_id"])
                if not user:
                    raise HTTPException(status_code=404, detail="User not found")

                user_context = {
                    "user_id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "phone": user.phone,
                    "disability_type": user.disability_type,
                    "accessibility_preferences": json.loads(
                        user.accessibility_preferences or "{}"
                    ),
                    "family_contacts": json.loads(user.family_contacts or "[]"),
                    "webhook_url": settings.WEBHOOK_URL,
                }

                task_data = {
                    "user_id": user.id,
                    "input_text": request_data["input_text"],
                    "priority": request_data["priority"],
                    "status": TaskStatusEnum.PENDING,
                }
                task = await task_repo.create_task(task_data)

                queued_task = QueuedTask(
                    task_id=task.id,
                    user_id=user.id,
                    task_type="unknown",
                    priority=request_data["priority"],
                    input_text=request_data["input_text"],
                    user_context=user_context,
                    accessibility_mode=request_data.get("accessibility_mode"),
                    webhook_url=request_data.get("webhook_url") or user.webhook_url,
                )

                queue_id = await self.task_queue.enqueue_task(queued_task)

                await task_repo.update_task_queue_info(task, queue_id)
                await session.commit()

                queue_length = await self.task_queue.get_queue_length(
                    request_data["priority"]
                )

                return TaskResponse(
                    task_id=task.id,
                    status=TaskStatusEnum.QUEUED,
                    message=f"Task queued successfully. Position in {request_data['priority']} priority queue: {queue_length}",
                    queue_position=queue_length,
                    estimated_completion=f"Estimated completion in {queue_length * 30} seconds",
                )

            except Exception as e:
                logger.error(f"Error creating and queuing task: {str(e)}, rolling back")
                await session.rollback()
                raise

    async def get_task(self, task_id: int) -> Any:
        async with PostgresDatabase.get_session() as session:
            task_repo = TaskRepository(session)
            return await task_repo.get_task_by_id(task_id)

    async def process_task(self, task_data: QueuedTask) -> bool:
        """Process a queued task"""
        async with PostgresDatabase.get_session() as session:
            task_repo = TaskRepository(session)

            try:
                task = await task_repo.get_task_by_id(task_data.task_id)
                if not task:
                    logger.error(f"Task {task_data.task_id} not found in database")
                    return False
                await task_repo.update_task_status(
                    task,
                    TaskStatusEnum.IN_PROGRESS,
                    started_at=datetime.now(timezone.utc),
                    retry_count=task_data.retry_count,
                )

                result = await self._execute_task_logic(task_data, task_repo)

                if result.get("success", False):
                    await task_repo.mark_task_completed(task, result)
                    if task_data.webhook_url:
                        await self.webhook_service.send_completion_webhook(
                            task_data.webhook_url, task_data.task_id, result
                        )
                else:
                    await task_repo.mark_task_failed(
                        task, result.get("error", "Unknown error")
                    )
                    if task_data.webhook_url:
                        await self.webhook_service.send_failure_webhook(
                            task_data.webhook_url, task_data.task_id, result
                        )

                await session.commit()
                return result.get("success", False)

            except Exception as e:
                logger.error(f"Error processing task {task_data.task_id}: {e}")
                if task:
                    await task_repo.mark_task_failed(task, str(e))
                    await session.commit()
                return False

    async def _execute_task_logic(
        self, task_data: QueuedTask, task_repo: TaskRepository
    ) -> Dict[str, Any]:
        """Core task processing logic"""
        try:
            # intent_result = await self.intent_processing_service.process_intent(text=task_data.input_text, context=task_data.user_context)

            task = await task_repo.get_task_by_id(task_data.task_id)
            # await task_repo.update_task_intent(task, intent_result, self.ai_router.default_provider)

            # if not intent_result.get("can_perform", True):
            #     return {
            #         "success": False,
            #         "error": intent_result.get("reason", "Cannot perform this task"),
            #         "message": intent_result.get("reason", "Cannot perform this task")
            #     }

            # feasibility = await self.intent_processing_service.validate_task_feasibility(intent_result["intent"], intent_result.get("details", {}))

            # if not feasibility.get("feasible", False):
            #     return {
            #         "success": False,
            #         "error": feasibility.get("reason", "Task not feasible"),
            #         "message": feasibility.get("reason", "Task not feasible")
            #     }

            # if feasibility.get("needs_clarification", False):
            #     return {
            #         "success": False,
            #         "needs_clarification": True,
            #         "error": "Missing information",
            #         "missing_info": feasibility.get("missing_info", []),
            #         "message": feasibility.get("reason", "Need more information")
            #     }

            # execution_result = await self.task_manager.execute_task(
            #     intent_result["intent"],
            #     intent_result.get("details", {}),
            #     task_data.user_context
            # )

            # await task_repo.update_task_execution_details(task, execution_result)

            # dummy execution result (tested the flow)
            execution_result = {
                "success": True,
                "booking_id": f"REST_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "confirmation_code": "ABC123",
                "message": f"Successfully booked a table for 5 at Zoreko on 10-08-2025 at 9:00 PM IST",
                "details": "dummy details",
            }
            return execution_result

        except Exception as e:
            logger.error(f"Task execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Task execution failed due to internal error",
            }
