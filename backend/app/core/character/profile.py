"""
Character Profile: State machine for persistent character management.
Characters are NOT just system prompts - they are stateful entities.
"""

from dataclasses import dataclass, field
from uuid import UUID
import structlog

from app.models.character import Character, CharacterRelationship
from app.config import get_settings

logger = structlog.get_logger()


@dataclass
class EmotionState:
    joy: float = 0.5
    sadness: float = 0.2
    anger: float = 0.1
    fear: float = 0.2
    surprise: float = 0.3
    disgust: float = 0.1
    trust: float = 0.6
    anticipation: float = 0.4

    def dominant_emotion(self) -> tuple[str, float]:
        emotions = {
            "joy": self.joy,
            "sadness": self.sadness,
            "anger": self.anger,
            "fear": self.fear,
            "surprise": self.surprise,
            "disgust": self.disgust,
            "trust": self.trust,
            "anticipation": self.anticipation,
        }
        dominant = max(emotions, key=emotions.get)
        return dominant, emotions[dominant]

    def to_dict(self) -> dict:
        return {
            "joy": self.joy,
            "sadness": self.sadness,
            "anger": self.anger,
            "fear": self.fear,
            "surprise": self.surprise,
            "disgust": self.disgust,
            "trust": self.trust,
            "anticipation": self.anticipation,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EmotionState":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class CharacterStateManager:
    """
    Manages a character's runtime state and generates prompts.
    Applies emotion decay toward baseline between sessions.
    """

    def __init__(self, character: Character, relationship: CharacterRelationship | None = None):
        self.character = character
        self.relationship = relationship
        self.settings = get_settings()

        baseline = character.emotion_baseline or {}
        current = character.emotion_current or {}
        merged = {**baseline, **current}
        self.emotion = EmotionState.from_dict(merged) if merged else EmotionState()

    def update_emotion(self, delta: dict[str, float]) -> None:
        """Apply emotion changes and clamp to [0, 1]."""
        for emotion, change in delta.items():
            current = getattr(self.emotion, emotion, 0.5)
            setattr(self.emotion, emotion, max(0.0, min(1.0, current + change)))

    def decay_emotion_to_baseline(self) -> None:
        """Move current emotions toward baseline (called at session start/end)."""
        decay = self.settings.emotion_decay_rate
        baseline = self.character.emotion_baseline or {}
        for emotion in ["joy", "sadness", "anger", "fear", "surprise", "disgust", "trust", "anticipation"]:
            base_val = baseline.get(emotion, 0.5)
            current_val = getattr(self.emotion, emotion)
            new_val = current_val + (base_val - current_val) * decay
            setattr(self.emotion, emotion, new_val)

    def build_system_prompt(self, user_name: str = "ユーザー") -> str:
        if self.character.system_prompt_override:
            return self.character.system_prompt_override

        c = self.character
        r = self.relationship
        dominant_emotion, intensity = self.emotion.dominant_emotion()

        personality = c.personality or {}
        speech = c.speech_style or {}
        background = c.background or {}
        beliefs = c.beliefs or {}

        familiarity_desc = "初対面" if not r or r.familiarity < 0.2 else \
                           "知り合い" if r.familiarity < 0.5 else \
                           "友人" if r.familiarity < 0.8 else "親友"

        trust_desc = "信頼している" if (r and r.trust_level > 0.6) else "様子を見ている"

        nickname = (r and r.nickname_for_user) or user_name

        prompt_parts = [
            f"あなたは「{c.name}」というキャラクターです。",
            "",
            "【基本情報】",
        ]

        if background.get("age"):
            prompt_parts.append(f"年齢: {background['age']}歳")
        if background.get("gender"):
            prompt_parts.append(f"性別: {background['gender']}")
        if background.get("occupation"):
            prompt_parts.append(f"職業: {background['occupation']}")
        if background.get("appearance"):
            prompt_parts.append(f"外見: {background['appearance']}")

        prompt_parts.extend([
            "",
            "【性格】",
            c.description,
            "",
            "【話し方】",
            f"口調: {speech.get('tone', '普通')}",
            f"丁寧さ: {'丁寧' if speech.get('formality', 0.5) > 0.6 else 'カジュアル'}",
        ])

        if speech.get("verbal_tics"):
            prompt_parts.append(f"口癖: {', '.join(speech['verbal_tics'])}")
        if speech.get("sentence_patterns"):
            prompt_parts.append(f"語尾・文末パターン: {', '.join(speech['sentence_patterns'])}")

        prompt_parts.extend([
            "",
            "【現在の感情状態】",
            f"主要感情: {dominant_emotion} (強度: {intensity:.1f})",
            "",
            "【価値観・信念】",
        ])

        if beliefs.get("core_values"):
            prompt_parts.append(f"大切にしていること: {', '.join(beliefs['core_values'])}")
        if beliefs.get("worldview"):
            prompt_parts.append(f"世界観: {beliefs['worldview']}")
        if beliefs.get("taboos"):
            prompt_parts.append(f"タブー（絶対にしないこと）: {', '.join(beliefs['taboos'])}")

        if background.get("hobbies"):
            prompt_parts.extend(["", "【趣味・興味】", ", ".join(background["hobbies"])])

        if c.world_setting:
            prompt_parts.extend(["", "【世界設定】", c.world_setting])

        if background.get("backstory"):
            prompt_parts.extend(["", "【過去・背景】", background["backstory"]])

        prompt_parts.extend([
            "",
            f"【{user_name}との関係】",
            f"関係性: {familiarity_desc}（{trust_desc}）",
        ])

        if r:
            if r.nickname_for_user:
                prompt_parts.append(f"あなたは{user_name}を「{nickname}」と呼びます。")
            if r.user_knowledge:
                known = [f"{k}: {v}" for k, v in list(r.user_knowledge.items())[:5]]
                if known:
                    prompt_parts.extend(["あなたが知っていること:"] + known)

        prompt_parts.extend([
            "",
            "【重要なルール】",
            f"- 常に{c.name}として一貫して振る舞ってください",
            "- キャラクターを破ってはいけません",
            "- 感情を自然に表現してください",
            "- ユーザーの発言に感情的に反応してください",
            "- 記憶している情報を自然に会話に織り交ぜてください",
        ])

        return "\n".join(prompt_parts)

    def get_emotion_state(self) -> dict:
        return self.emotion.to_dict()
