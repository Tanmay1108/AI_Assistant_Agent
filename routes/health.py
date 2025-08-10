from fastapi import APIRouter, Request

from ai_providers.router import AIProviderRouter
from queue_infra.redis_queue import RedisTaskQueue
from services.feedback_service import FeedbackService
from services.task_manager import TaskManager

router = APIRouter()

ai_router = AIProviderRouter()
task_manager = TaskManager()
feedback_service = FeedbackService(ai_router)


@router.get("/health")
async def health_check(request: Request):

    task_queue = request.app.state.task_queue
    queue_stats = await task_queue.get_queue_stats() if task_queue else {}
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0",
        "queue_stats": queue_stats,
        "services": {
            "ai_providers": list(ai_router.providers.keys()),
            "available_tasks": task_manager.get_available_tasks(),
        },
    }
