from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    name: str


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=72)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    name: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=72)


class User(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
