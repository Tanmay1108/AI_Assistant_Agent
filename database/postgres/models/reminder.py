from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Text, func)
from sqlalchemy.orm import relationship

from database.postgres.models.base import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    reminder_type = Column(String, nullable=False)  # medicine, appointment, etc.
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    schedule_pattern = Column(String, nullable=False)  # cron-like or simple patterns
    next_reminder_at = Column(DateTime, nullable=False)
    last_sent_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    webhook_url = Column(String, nullable=True)  # Override user's webhook
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="reminders")
