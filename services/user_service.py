import json
import logging
from typing import Any, Dict

from common.exceptions import ValidationException
from database.postgres.models.user import User
from database.postgres.postgres_database import PostgresDatabase
from database.postgres.repositories.user import UserRepository

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self):
        # we might need this for initializing notification service later.
        pass

    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """
        Creates a new user after checking for duplicates.

        Args:
            user_data: Dictionary containing user details (name, email, phone, etc.).

        Returns:
            The created User object.

        Raises:
            ValidationException: If email or phone already exists.
            Exception: Any other DB or processing error.
        """
        async with PostgresDatabase.get_session() as session:
            try:
                if not user_data.get("email") or not user_data.get("name"):
                    raise ValidationException(
                        "User must have at least a name and an email"
                    )

                user_repo = UserRepository(session)
                user = await user_repo.create_user(user_data)
                await session.commit()

                logger.info(f"User created successfully: {user.id}")
                user.accessibility_preferences = json.loads(
                    user.accessibility_preferences or "{}"
                )
                user.family_contacts = json.loads(user.family_contacts or "[]")
                return user

            except ValidationException:
                await session.rollback()
                raise
            except Exception as e:
                logger.error(
                    f"Error creating user: {str(e)}, rolling back the transaction"
                )
                await session.rollback()
                raise
