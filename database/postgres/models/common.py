from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AIProvider(str, Enum):
    OPENAI = "openai"
    CLAUDE = "claude"


class TaskPriority(str, Enum):
    HIGH = "high"  # Immediate actions (restaurant/salon booking)
    NORMAL = "normal"  # Regular tasks (family notifications)
    LOW = "low"  # Background tasks (medicine reminders)
