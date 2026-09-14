from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser, DbSession
from app.schemas.user import User, UserCreate, UserUpdate
from app.services.user_service import EmailAlreadyRegisteredError, user_service

router = APIRouter()


@router.post("/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user_in: UserCreate, db: DbSession) -> User:
    """Register a new user."""
    try:
        return await user_service.create_user(db, user_in)
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        ) from None


@router.get("/me", response_model=User)
async def read_current_user(current_user: CurrentUser) -> User:
    """Get the currently authenticated user."""
    return current_user


@router.get("/{user_id}", response_model=User)
async def read_user(user_id: int, current_user: CurrentUser) -> User:
    """Get a user by ID. Users may only read themselves."""
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return current_user


@router.patch("/{user_id}", response_model=User)
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> User:
    """Update a user. Users may only update themselves."""
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    try:
        user = await user_service.update_user(db, user_id, user_in)
    except EmailAlreadyRegisteredError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        ) from None
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: DbSession, current_user: CurrentUser) -> None:
    """Delete a user. Users may only delete themselves."""
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    deleted = await user_service.repository.delete(db, user_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
