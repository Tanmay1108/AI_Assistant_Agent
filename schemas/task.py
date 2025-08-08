from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel


class TaskStatusEnum(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskRequest(BaseModel):
    user_id: int
    input_text: str
    accessibility_mode: Optional[bool] = False


class TaskResponse(BaseModel):
    task_id: int
    status: TaskStatusEnum
    message: str
    details: Optional[Dict[str, Any]] = None
    accessibility_feedback: Optional[str] = None
