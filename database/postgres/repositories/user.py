import json
import logging
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import ValidationException
from database.postgres.models.user import User

logger = logging.getLogger(__name__)


class UserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create_user(self, user_data: Dict[str, Any]) -> User:
        try:
            stmt = select(User).where((User.email == user_data.get("email")))
            result = await self._session.execute(stmt)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                raise ValidationException(
                    f"User with email '{user_data.get('email')}' already exists."
                )

            user = User(
                name=user_data.get("name"),
                email=user_data.get("email"),
                phone=user_data.get("phone"),
                disability_type=user_data.get("disability_type"),
                accessibility_preferences=json.dumps(
                    user_data.get("accessibility_preferences", {})
                ),
                family_contacts=json.dumps(user_data.get("family_contacts", [])),
            )

            self._session.add(user)
            await self._session.flush()
            await self._session.refresh(user)

            return user

        except Exception as e:
            logger.error(f"Error creating booking: {str(e)}")
            raise
