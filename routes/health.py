from fastapi import APIRouter

from ai_providers.router import AIProviderRouter
from services.agent_orchestrator import AgentOrchestrator
from services.feedback_service import FeedbackService
from services.task_manager import TaskManager

router = APIRouter()

ai_router = AIProviderRouter()
task_manager = TaskManager()
feedback_service = FeedbackService(ai_router)
agent_orchestrator = AgentOrchestrator(ai_router, task_manager, feedback_service)


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "version": "1.0.0",
        "services": {
            "ai_providers": list(ai_router.providers.keys()),
            "available_tasks": task_manager.get_available_tasks(),
        },
    }
