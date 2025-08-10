import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.postgres.models.common import TaskStatus
from database.postgres.models.task import Task

logger = logging.getLogger(__name__)


class TaskRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_task(self, task_data: Dict[str, Any]) -> Task:
        try:
            task = Task(**task_data)
            self._session.add(task)
            await self._session.flush()
            await self._session.refresh(task)
            return task
        except Exception as e:
            logger.error(f"Error creating task: {str(e)}")
            raise

    async def update_task_queue_info(self, task: Task, queue_id: str):
        task.queue_id = queue_id
        task.status = TaskStatus.QUEUED
        task.queued_at = task.created_at
        await self._session.flush()
        await self._session.refresh(task)

    async def get_task_by_id(self, task_id: int) -> Optional[Task]:
        stmt = select(Task).where(Task.id == task_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_task_status(
        self,
        task: Task,
        status: TaskStatus,
        started_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
        retry_count: Optional[int] = None,
    ):
        task.status = status
        if started_at:
            task.started_at = started_at
        if retry_count:
            task.retry_count = retry_count
        if error_message:
            task.error_message = error_message
        await self._session.flush()

    async def update_task_fields(self, task: Task, **kwargs):
        for key, value in kwargs.items():
            setattr(task, key, value)
        await self._session.flush()

    async def mark_task_failed(self, task, reason: str):
        task.status = TaskStatus.FAILED
        task.error_message = reason
        task.completed_at = datetime.now(timezone.utc)
        await self._session.flush()

    async def update_task_intent(
        self,
        task: Task,
        intent: str,
        confidence: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Update the intent, confidence, and execution details for a task.
        """
        task.processed_intent = intent
        if confidence is not None:
            task.confidence = confidence
        if details is not None:
            task.execution_details = json.dumps(details)
        task.updated_at = datetime.now(timezone.utc)
        await self._session.flush()
        await self._session.refresh(task)
        return task

    async def mark_task_completed(
        self,
        task: Task,
        result: Any,
    ):
        """
        Mark a task as completed, store the result as JSON string,
        and set completion timestamp.
        """
        task.status = TaskStatus.COMPLETED
        task.result = json.dumps(result) if not isinstance(result, str) else result
        task.completed_at = datetime.now(timezone.utc)

        await self._session.flush()
        await self._session.refresh(task)
        return task
