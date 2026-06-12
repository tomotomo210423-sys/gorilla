from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.memory import MemoryEntry
from app.schemas.memory import MemoryEntryOut
from app.db.session import get_db

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/{user_id}", response_model=list[MemoryEntryOut])
async def list_memories(
    user_id: UUID,
    memory_type: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
) -> list[MemoryEntryOut]:
    stmt = (
        select(MemoryEntry)
        .where(MemoryEntry.user_id == user_id, MemoryEntry.is_archived == False)
        .order_by(MemoryEntry.retention_score.desc(), MemoryEntry.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if memory_type:
        stmt = stmt.where(MemoryEntry.memory_type == memory_type)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(MemoryEntry).where(MemoryEntry.id == memory_id))
    entry = result.scalar_one_or_none()
    if entry:
        entry.is_archived = True
        await db.commit()
    return {"status": "archived", "id": str(memory_id)}
