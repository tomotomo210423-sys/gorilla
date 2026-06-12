import uuid
from sqlalchemy import String, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # User profile learned from conversations
    profile: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        comment="Learned user preferences, interests, communication style",
    )

    # Conversations and memories
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    memories: Mapped[list["MemoryEntry"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
