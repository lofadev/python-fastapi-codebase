from pydantic import BaseModel, ConfigDict, Field, field_validator


class ItemBase(BaseModel):
    title: str = Field(max_length=255)
    description: str | None = None


class ItemCreate(ItemBase):
    pass


class ItemUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None

    @field_validator("title")
    @classmethod
    def reject_null(cls, value: str | None) -> str | None:
        """Omitted title stays unchanged; explicit null is invalid (description may be null)."""
        if value is None:
            raise ValueError("must not be null")
        return value


class Item(ItemBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
