from typing import Dict, Optional

from pydantic import BaseModel


class IntentSchema(BaseModel):
    intent: str
    confidence: float
    service_name: Optional[str]
    details: Dict = {}
