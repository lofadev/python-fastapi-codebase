from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, field_validator

BCRYPT_MAX_BYTES = 72


def _check_password_bytes(password: str) -> str:
    if len(password.encode("utf-8")) > BCRYPT_MAX_BYTES:
        raise ValueError(f"Password must be at most {BCRYPT_MAX_BYTES} bytes when UTF-8 encoded")
    return password


# bcrypt rejects passwords over 72 bytes; max_length alone counts characters, not bytes.
Password = Annotated[
    str, Field(min_length=8, max_length=72), AfterValidator(_check_password_bytes)
]


class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(max_length=255)


class UserCreate(UserBase):
    password: Password


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    name: str | None = Field(default=None, max_length=255)
    password: Password | None = None

    @field_validator("email", "name", "password")
    @classmethod
    def reject_null(cls, value: str | None) -> str | None:
        """Omitted fields stay unchanged; an explicit null is invalid for these columns."""
        if value is None:
            raise ValueError("must not be null")
        return value


class User(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
