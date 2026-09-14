from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.repositories.user_repository import user_repository
from app.schemas.user import UserCreate, UserUpdate

UNIQUE_VIOLATION = "23505"


class EmailAlreadyRegisteredError(Exception):
    """Raised when an email address is already used by another user."""


@contextmanager
def _email_conflict_as_domain_error() -> Iterator[None]:
    """Translate a unique violation on `users` into EmailAlreadyRegisteredError.

    Besides the primary key, the only unique index on `users` is `email`, so a unique
    violation here always means a duplicate email (e.g. a concurrent registration).
    """
    try:
        yield
    except IntegrityError as exc:
        if getattr(exc.orig, "sqlstate", None) == UNIQUE_VIOLATION:
            raise EmailAlreadyRegisteredError from exc
        raise


class UserService:
    """Business logic for users."""

    def __init__(self) -> None:
        self.repository = user_repository

    async def create_user(self, db: AsyncSession, user_in: UserCreate) -> User:
        existing = await self.repository.get_by_email(db, user_in.email)
        if existing is not None:
            raise EmailAlreadyRegisteredError

        data = user_in.model_dump(exclude={"password"})
        data["hashed_password"] = get_password_hash(user_in.password)
        with _email_conflict_as_domain_error():
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
        if "email" in data:
            existing = await self.repository.get_by_email(db, data["email"])
            if existing is not None and existing.id != user.id:
                raise EmailAlreadyRegisteredError
        if password := data.pop("password", None):
            data["hashed_password"] = get_password_hash(password)
        with _email_conflict_as_domain_error():
            return await self.repository.update(db, user, data)


user_service = UserService()
