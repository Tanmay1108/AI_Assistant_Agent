# import asyncio
# import json
# from datetime import datetime
# from sqlalchemy.orm import Session
# from typing import Dict, Any

# from database.postgres.postgres_database import SessionLocal
# from database.postgres.models.task import Task
# from database.postgres.models.common import TaskStatus
# from database.postgres.models.user import User
# from schemas.task import QueuedTask
# from ai_providers.router import AIProviderRouter
# from services.task_manager import TaskManager
# from services.feedback_service import FeedbackService
# from services.webhook_service import WebhookService
# import structlog

# logger = structlog.get_logger()

# class TaskProcessor:
#     def __init__(self):
#         self.ai_router = AIProviderRouter()
#         self.task_manager = TaskManager()
#         self.feedback_service = FeedbackService(self.ai_router)
#         self.webhook_service = WebhookService()

#     async def process_task(self, task_data: QueuedTask) -> bool:
#         """Process a queued task"""
#         db = SessionLocal()
#         try:
#             task = db.query(Task).filter(Task.id == task_data.task_id).first()
#             if not task:
#                 logger.error(f"Task {task_data.task_id} not found in database")
#                 return False

#             task.status = TaskStatus.IN_PROGRESS
#             task.started_at = datetime.now(datetime.timezone.utc)
#             task.retry_count = task_data.retry_count
#             db.commit()

#             # Process the task using the existing orchestrator logic
#             result = await self._execute_task_logic(task_data, db)

#             # Update task with results
#             if result.get("success", False):
#                 task.status = TaskStatus.COMPLETED
#                 task.result = json.dumps(result)
#                 task.completed_at = datetime.utcnow()

#                 # Send success webhook
#                 if task_data.webhook_url:
#                     await self.webhook_service.send_completion_webhook(
#                         task_data.webhook_url, task_data.task_id, result
#                     )
#             else:
#                 task.status = TaskStatus.FAILED
#                 task.error_message = result.get("error", "Unknown error")

#                 # Send failure webhook
#                 if task_data.webhook_url:
#                     await self.webhook_service.send_failure_webhook(
#                         task_data.webhook_url, task_data.task_id, result
#                     )

#             db.commit()
#             return result.get("success", False)

#         except Exception as e:
#             logger.error(f"Error processing task {task_data.task_id}: {e}")

#             # Update task status to failed
#             task = db.query(Task).filter(Task.id == task_data.task_id).first()
#             if task:
#                 task.status = TaskStatus.FAILED
#                 task.error_message = str(e)
#                 db.commit()

#             return False
#         finally:
#             db.close()

#     async def _execute_task_logic(self, task_data: QueuedTask, db: Session) -> Dict[str, Any]:
#         """Execute the core task processing logic"""
#         try:
#             # Step 1: Process intent with AI
#             intent_result = await self.ai_router.process_with_fallback(
#                 "process_intent",
#                 task_data.input_text,
#                 {"user_context": task_data.user_context}
#             )

#             # Update task with processed intent
#             task = db.query(Task).filter(Task.id == task_data.task_id).first()
#             task.processed_intent = json.dumps(intent_result)
#             task.ai_provider_used = self.ai_router.default_provider
#             task.task_type = intent_result.get("intent", "unknown")
#             db.commit()

#             # Step 2: Check if task can be performed
#             if not intent_result.get("can_perform", True):
#                 return {
#                     "success": False,
#                     "error": intent_result.get("reason", "Cannot perform this task"),
#                     "message": intent_result.get("reason", "Cannot perform this task")
#                 }

#             # Step 3: Validate task feasibility
#             feasibility = await self.ai_router.process_with_fallback(
#                 "validate_task_feasibility",
#                 intent_result["intent"],
#                 intent_result.get("details", {})
#             )

#             if not feasibility.get("feasible", False):
#                 return {
#                     "success": False,
#                     "error": feasibility.get("reason", "Task not feasible"),
#                     "message": feasibility.get("reason", "Task not feasible")
#                 }

#             # Step 4: Handle clarification if needed
#             if feasibility.get("needs_clarification", False):
#                 return {
#                     "success": False,
#                     "needs_clarification": True,
#                     "error": "Missing information",
#                     "missing_info": feasibility.get("missing_info", []),
#                     "message": feasibility.get("reason", "Need more information")
#                 }

#             # Step 5: Execute the task
#             execution_result = await self.task_manager.execute_task(
#                 intent_result["intent"],
#                 intent_result.get("details", {}),
#                 task_data.user_context
#             )

#             # Update task execution details
#             task.execution_details = json.dumps(execution_result)
#             db.commit()

#             return execution_result

#         except Exception as e:
#             logger.error(f"Task execution error: {e}")
#             return {
#                 "success": False,
#                 "error": str(e),
#                 "message": "Task execution failed due to internal error"
#             }


from ai_providers.router import AIProviderRouter
from services.feedback_service import FeedbackService
from services.task_manager import TaskManager
from services.task_service import TaskService
from services.webhook_service import WebhookService


class TaskProcessor:
    def __init__(self, task_queue):
        self.task_service = TaskService(task_queue=task_queue)

    async def process_task(self, task_data):
        return await self.task_service.process_task(task_data)
