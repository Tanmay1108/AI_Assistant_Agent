from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel


class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriorityEnum(str, Enum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class TaskRequest(BaseModel):
    user_id: int
    input_text: str
    priority: Optional[TaskPriorityEnum] = TaskPriorityEnum.NORMAL
    accessibility_mode: Optional[bool] = False
    webhook_url: Optional[str] = None  # Override user's default webhook


class TaskResponse(BaseModel):
    task_id: int
    status: TaskStatusEnum
    message: str
    queue_position: Optional[int] = None
    estimated_completion: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    accessibility_feedback: Optional[str] = None


# for now added this class here, in production this should be in a separate folder.
class QueuedTask(BaseModel):
    task_id: int
    user_id: int
    task_type: str
    priority: str
    input_text: str
    user_context: Dict[str, Any]
    accessibility_mode: bool = False
    webhook_url: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
