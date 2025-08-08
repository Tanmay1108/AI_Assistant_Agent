from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from database.postgres.models.base import Base

from .common import TaskStatus


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    task_type = Column(
        String, nullable=False
    )  # restaurant_booking, salon_booking, etc.
    status = Column(String, default=TaskStatus.PENDING)
    input_text = Column(Text, nullable=False)
    processed_intent = Column(Text, nullable=True)  # JSON string
    execution_details = Column(Text, nullable=True)  # JSON string
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    ai_provider_used = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="tasks")
    feedback = relationship("Feedback", back_populates="task")
