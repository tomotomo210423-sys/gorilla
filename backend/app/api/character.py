from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.character import Character
from app.schemas.character import CharacterCreate, CharacterUpdate, CharacterOut
from app.db.session import get_db

router = APIRouter(prefix="/api/characters", tags=["characters"])


@router.post("/", response_model=CharacterOut, status_code=201)
async def create_character(
    data: CharacterCreate,
    db: AsyncSession = Depends(get_db),
) -> CharacterOut:
    character = Character(
        name=data.name,
        description=data.description,
        personality=data.personality or {},
        speech_style=data.speech_style or {},
        emotion_baseline=data.emotion_baseline or {},
        emotion_current={},
        beliefs=data.beliefs or {},
        background=data.background or {},
        world_setting=data.world_setting,
        system_prompt_override=data.system_prompt_override,
    )
    db.add(character)
    await db.commit()
    await db.refresh(character)
    return character


@router.get("/", response_model=list[CharacterOut])
async def list_characters(db: AsyncSession = Depends(get_db)) -> list[CharacterOut]:
    result = await db.execute(select(Character).order_by(Character.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{character_id}", response_model=CharacterOut)
async def get_character(character_id: UUID, db: AsyncSession = Depends(get_db)) -> CharacterOut:
    result = await db.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character


@router.patch("/{character_id}", response_model=CharacterOut)
async def update_character(
    character_id: UUID,
    data: CharacterUpdate,
    db: AsyncSession = Depends(get_db),
) -> CharacterOut:
    result = await db.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(character, field, value)

    await db.commit()
    await db.refresh(character)
    return character


@router.delete("/{character_id}", status_code=204)
async def delete_character(character_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    result = await db.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()
    if character:
        await db.delete(character)
        await db.commit()
