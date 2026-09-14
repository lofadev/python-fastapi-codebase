from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item
from app.repositories.base_repository import BaseRepository
from app.schemas.item import ItemCreate, ItemUpdate


class ItemRepository(BaseRepository[Item, ItemCreate, ItemUpdate]):
    async def get_multi_by_owner(
        self, db: AsyncSession, owner_id: int, *, skip: int = 0, limit: int = 100
    ) -> Sequence[Item]:
        stmt = (
            select(self.model)
            .filter(Item.owner_id == owner_id)
            .order_by(Item.id)
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        return result.scalars().all()


item_repository = ItemRepository(Item)
