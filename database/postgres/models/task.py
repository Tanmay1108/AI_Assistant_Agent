from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (Column, DateTime, ForeignKey, Integer, String, Text,
                        func)
from sqlalchemy.orm import relationship

from database.postgres.models.base import Base

from .common import TaskPriority, TaskStatus


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    task_type = Optional[Column(String, nullable=False)]
    priority = Column(String, default=TaskPriority.NORMAL)
    status = Column(String, default=TaskStatus.PENDING)
    queue_id = Column(String, nullable=True)  # Redis stream message ID
    input_text = Column(Text, nullable=False)
    processed_intent = Column(Text, nullable=True)  # JSON string
    execution_details = Column(Text, nullable=True)  # JSON string
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    ai_provider_used = Column(String, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    queued_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )
    completed_at = Column(
        DateTime(timezone=True), nullable=True, server_default=func.now()
    )

    user = relationship("User", back_populates="tasks")
    feedback = relationship("Feedback", back_populates="task")
