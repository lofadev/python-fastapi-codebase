from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.repositories.user_repository import user_repository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """Business logic for users."""

    def __init__(self) -> None:
        self.repository = user_repository

    async def create_user(self, db: AsyncSession, user_in: UserCreate) -> User:
        existing = await self.repository.get_by_email(db, user_in.email)
        if existing is not None:
            raise ValueError("Email already registered")

        data = user_in.model_dump(exclude={"password"})
        data["hashed_password"] = get_password_hash(user_in.password)
        return await self.repository.create(db, data)

    async def authenticate(self, db: AsyncSession, email: str, password: str) -> User | None:
        user = await self.repository.get_by_email(db, email)
        if user is None:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def update_user(
        self,
        db: AsyncSession,
        user_id: int,
        user_in: UserUpdate,
    ) -> User | None:
        user = await self.repository.get(db, user_id)
        if user is None:
            return None

        data = user_in.model_dump(exclude_unset=True)
        if password := data.pop("password", None):
            data["hashed_password"] = get_password_hash(password)
        return await self.repository.update(db, user, data)


user_service = UserService()
