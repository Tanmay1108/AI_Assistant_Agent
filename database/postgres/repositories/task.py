import logging
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

    async def get_task_by_id(self, task_id: int) -> Optional[Task]:
        result = await self._session.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()
