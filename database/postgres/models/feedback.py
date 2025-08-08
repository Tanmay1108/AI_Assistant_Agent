from datetime import datetime, timezone

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.orm import relationship

from database.postgres.models.base import Base


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    feedback_type = Column(String, nullable=False)  # success, error, suggestion
    rating = Column(Float, nullable=True)  # 1-5 scale
    comment = Column(Text, nullable=True)
    accessibility_issue = Column(Text, nullable=True)
    improvement_suggestion = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    processed = Column(Boolean, default=False)

    user = relationship("User", back_populates="feedback")
    task = relationship("Task", back_populates="feedback")
