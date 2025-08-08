# services/task_service.py
import logging
from typing import Any, Dict

from common.exceptions import ValidationException
from database.postgres.postgres_database import PostgresDatabase
from database.postgres.repositories.task import TaskRepository

logger = logging.getLogger(__name__)


class TaskService:
    async def create_task(self, task_data: Dict[str, Any]) -> Any:
        async with PostgresDatabase.get_session() as session:
            try:
                task_repo = TaskRepository(session)

                if not task_data.get("user_id"):
                    raise ValidationException("User ID is required to create a task")

                task = await task_repo.create_task(task_data)
                await session.commit()
                return task
            except Exception as e:
                logger.error(f"Error creating task: {str(e)}, rolling back")
                await session.rollback()
                raise

    async def get_task(self, task_id: int) -> Any:
        async with PostgresDatabase.get_session() as session:
            task_repo = TaskRepository(session)
            return await task_repo.get_task_by_id(task_id)
