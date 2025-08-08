from typing import Optional

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    task_id: Optional[int] = None
    feedback_type: str
    rating: Optional[float] = Field(None, ge=1, le=5)
    comment: Optional[str] = None
    accessibility_issue: Optional[str] = None
    improvement_suggestion: Optional[str] = None
