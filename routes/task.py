import logging

from fastapi import APIRouter, Request

from schemas.task import TaskRequest, TaskResponse
from services.task_service import TaskService

router = APIRouter(tags=["Tasks"])
logger = logging.getLogger(__name__)


@router.post("/tasks", response_model=TaskResponse)
async def create_task_endpoint(request_data: TaskRequest, request: Request):
    task_queue = request.app.state.task_queue
    service = TaskService(task_queue)
    return await service.create_task(request_data.model_dump())


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int):
    task_service = TaskService()
    task = await task_service.get_task(task_id)
    if not task:
        return {"message": "Task not found"}
    return task
