import uuid
from sqlalchemy import String, Text, JSON, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, TimestampMixin, UUIDMixin


class Character(Base, UUIDMixin, TimestampMixin):
    """
    Persistent character profile. Not just a system prompt but a full state machine.
    """

    __tablename__ = "characters"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Big5 personality model (0.0-1.0 each)
    personality: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "openness": 0.7,
            "conscientiousness": 0.6,
            "extraversion": 0.5,
            "agreeableness": 0.7,
            "neuroticism": 0.3,
        },
    )

    # Speech characteristics
    speech_style: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "tone": "friendly",
            "formality": 0.5,  # 0=casual, 1=formal
            "sentence_patterns": [],
            "verbal_tics": [],
            "vocabulary_style": "standard",
        },
    )

    # Emotional baseline and current state
    emotion_baseline: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "joy": 0.5,
            "sadness": 0.2,
            "anger": 0.1,
            "fear": 0.2,
            "surprise": 0.3,
            "disgust": 0.1,
            "trust": 0.6,
            "anticipation": 0.4,
        },
    )
    emotion_current: Mapped[dict] = mapped_column(JSON, default=dict)

    # Beliefs and worldview
    beliefs: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "core_values": [],
            "worldview": "",
            "opinions": {},
            "taboos": [],
        },
    )

    # Background
    background: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "age": None,
            "gender": None,
            "occupation": None,
            "hobbies": [],
            "appearance": "",
            "backstory": "",
        },
    )

    # World setting
    world_setting: Mapped[str | None] = mapped_column(Text, nullable=True)

    # System prompt template (raw override, takes precedence if set)
    system_prompt_override: Mapped[str | None] = mapped_column(Text, nullable=True)

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="character")
    relationships: Mapped[list["CharacterRelationship"]] = relationship(
        back_populates="character", cascade="all, delete-orphan"
    )


class CharacterRelationship(Base, UUIDMixin, TimestampMixin):
    """Tracks character's relationship with each user."""

    __tablename__ = "character_relationships"

    character_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("characters.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Relationship state
    trust_level: Mapped[float] = mapped_column(Float, default=0.5)
    familiarity: Mapped[float] = mapped_column(Float, default=0.0)
    affection: Mapped[float] = mapped_column(Float, default=0.5)

    # What the character knows/remembers about this user
    user_knowledge: Mapped[dict] = mapped_column(JSON, default=dict)
    shared_experiences: Mapped[list] = mapped_column(JSON, default=list)
    nickname_for_user: Mapped[str | None] = mapped_column(String(64), nullable=True)

    character: Mapped["Character"] = relationship(back_populates="relationships")
