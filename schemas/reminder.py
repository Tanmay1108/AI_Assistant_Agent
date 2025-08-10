from typing import Optional

from pydantic import BaseModel


class ReminderRequest(BaseModel):
    user_id: int
    reminder_type: str
    title: str
    message: str
    schedule_pattern: (
        str  # e.g., "daily_at_09:00", "every_6_hours", "cron:0 9,21 * * *"
    )
    webhook_url: Optional[str] = None
