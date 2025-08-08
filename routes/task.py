import logging

from fastapi import APIRouter

from schemas.task import TaskRequest, TaskResponse
from services.task_service import TaskService

router = APIRouter(tags=["Tasks"])
logger = logging.getLogger(__name__)


@router.post("/tasks", response_model=TaskResponse)
async def create_task(task_data: TaskRequest):
    task_service = TaskService()
    task = await task_service.create_task(task_data.model_dump())
    return task


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int):
    task_service = TaskService()
    task = await task_service.get_task(task_id)
    if not task:
        return {"message": "Task not found"}
    return task
