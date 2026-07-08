from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item
from app.repositories.item_repository import item_repository
from app.schemas.item import ItemCreate


class ItemService:
    """Business logic for items."""

    def __init__(self) -> None:
        self.repository = item_repository

    async def create_item(
        self,
        db: AsyncSession,
        item_in: ItemCreate,
        owner_id: int,
    ) -> Item:
        data = item_in.model_dump()
        data["owner_id"] = owner_id
        return await self.repository.create(db, data)

    async def get_items_by_owner(
        self,
        db: AsyncSession,
        owner_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[Item]:
        return await self.repository.get_multi_by_owner(db, owner_id, skip=skip, limit=limit)


item_service = ItemService()
