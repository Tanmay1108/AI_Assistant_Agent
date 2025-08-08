from .base import Base
from .feedback import Feedback
from .task import Task
from .user import User

# This ensures all models are registered with Base.metadata
__all__ = ["Base", "Feedback", "Task", "User"]
