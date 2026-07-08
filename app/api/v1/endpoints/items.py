from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser, DbSession
from app.models.item import Item as ItemModel
from app.schemas.item import Item, ItemCreate, ItemUpdate
from app.services.item_service import item_service

router = APIRouter()


async def _get_owned_item(item_id: int, db: DbSession, current_user: CurrentUser) -> ItemModel:
    item = await item_service.repository.get(db, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if item.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return item


@router.post("/", response_model=Item, status_code=status.HTTP_201_CREATED)
async def create_item(item_in: ItemCreate, db: DbSession, current_user: CurrentUser) -> Item:
    """Create an item owned by the current user."""
    return await item_service.create_item(db, item_in, owner_id=current_user.id)


@router.get("/", response_model=list[Item])
async def read_items(
    db: DbSession,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> list[Item]:
    """List items owned by the current user."""
    return await item_service.get_items_by_owner(db, current_user.id, skip=skip, limit=limit)


@router.get("/{item_id}", response_model=Item)
async def read_item(item_id: int, db: DbSession, current_user: CurrentUser) -> Item:
    """Get an item by ID. Only the owner may read it."""
    return await _get_owned_item(item_id, db, current_user)


@router.patch("/{item_id}", response_model=Item)
async def update_item(
    item_id: int,
    item_in: ItemUpdate,
    db: DbSession,
    current_user: CurrentUser,
) -> Item:
    """Update an item. Only the owner may update it."""
    item = await _get_owned_item(item_id, db, current_user)
    return await item_service.repository.update(db, item, item_in)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(item_id: int, db: DbSession, current_user: CurrentUser) -> None:
    """Delete an item. Only the owner may delete it."""
    item = await _get_owned_item(item_id, db, current_user)
    await item_service.repository.delete(db, item.id)
