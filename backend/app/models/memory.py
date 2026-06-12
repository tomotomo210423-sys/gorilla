import uuid
from enum import Enum
from sqlalchemy import String, Text, JSON, ForeignKey, Float, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin, UUIDMixin


class MemoryType(str, Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"


class MemoryEntry(Base, UUIDMixin, TimestampMixin):
    """
    Unified memory entry that spans all 4 memory layers.
    Vector embeddings stored separately in Qdrant; this holds metadata.
    """

    __tablename__ = "memory_entries"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    character_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("characters.id", ondelete="SET NULL"), nullable=True
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )

    memory_type: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Forgetting curve variables
    importance_score: Mapped[float] = mapped_column(Float, default=0.5)
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    retention_score: Mapped[float] = mapped_column(Float, default=1.0)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    # Semantic tags for retrieval
    tags: Mapped[list] = mapped_column(JSON, default=list)
    entities: Mapped[dict] = mapped_column(JSON, default=dict)  # {persons, places, events}
    topic: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Qdrant vector ID for cross-reference
    qdrant_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    user: Mapped["User"] = relationship(back_populates="memories")
