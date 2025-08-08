from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    disability_type: Optional[str] = None
    accessibility_preferences: Optional[Dict[str, Any]] = None
    family_contacts: Optional[List[Dict[str, str]]] = None


class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: Optional[str] = None
    disability_type: Optional[str] = None
    accessibility_preferences: Optional[Dict[str, Any]] = None
    family_contacts: Optional[List[Dict[str, str]]] = None
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        orm_mode = True
