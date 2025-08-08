import json
from datetime import datetime
from typing import Any, Dict, Optional, Type, TypeVar

from sqlalchemy import Column, DateTime, Integer, String, event, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import Session

ModelType = TypeVar("ModelType", bound="Base")


@as_declarative()
class Base:
    """
    Base class for all SQLAlchemy models.
    Provides common attributes and methods for all models.
    """

    # Primary key for all tables
    id = Column(Integer, primary_key=True, index=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert model instance to dictionary."""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            elif hasattr(value, "value"):  # For Enum values
                value = value.value
            result[column.name] = value
        return result

    def to_json(self) -> str:
        """Convert model instance to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    async def get_by_id(
        cls: Type[ModelType], session: AsyncSession, id: int
    ) -> Optional[ModelType]:
        """Get model instance by ID."""
        return await session.get(cls, id)

    @classmethod
    async def create(
        cls: Type[ModelType], session: AsyncSession, **kwargs: Any
    ) -> ModelType:
        """Create new model instance."""
        instance = cls(**kwargs)
        session.add(instance)
        await session.flush()
        await session.refresh(instance)
        return instance

    @classmethod
    async def update_by_id(
        cls: Type[ModelType], session: AsyncSession, id: int, **kwargs: Any
    ) -> Optional[ModelType]:
        """Update model instance by ID."""
        instance = await cls.get_by_id(session, id)
        if instance:
            for key, value in kwargs.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            await session.flush()
            await session.refresh(instance)
        return instance

    @classmethod
    async def delete_by_id(
        cls: Type[ModelType], session: AsyncSession, id: int
    ) -> bool:
        """Delete model instance by ID."""
        instance = await cls.get_by_id(session, id)
        if instance:
            await session.delete(instance)
            await session.flush()
            return True
        return False
