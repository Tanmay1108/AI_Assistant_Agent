from fastapi import APIRouter

from schemas.user import UserCreate, UserResponse
from services.user_service import UserService

router = APIRouter(tags=["Users"])


@router.post("/users", response_model=UserResponse)
async def create_user(user_data: UserCreate):
    """
    Create a new user in the system.

    Args:
        user_data (UserCreate): The details of the user to be created.

    Returns:
        UserResponse: The created user object.
    """
    user_service = UserService()
    user = await user_service.create_user(user_data.model_dump())
    return user
