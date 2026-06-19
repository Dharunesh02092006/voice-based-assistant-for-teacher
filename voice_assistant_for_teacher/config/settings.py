"""
Centralized, environment-driven configuration for the Voice Teaching Assistant.

Every external API key and tunable constant lives here so the rest of the
codebase never reads `os.environ` directly. This keeps configuration
auditable in one place and makes it trivial to point the app at different
keys/models for local dev vs. deployment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from dotenv import load_dotenv

# Load .env once, as early as possible. Safe to call even if no .env exists
# (e.g. when secrets are injected as real environment variables in prod).
load_dotenv()

BASE_DIR: Final[Path] = Path(__file__).resolve().parent.parent
PROMPTS_DIR: Final[Path] = BASE_DIR / "prompts"


def _get_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# Intents that ALWAYS go to Gemini regardless of complexity score, because
# they require deeper structural reasoning than a fast classifier-grade
# model reliably produces.
FORCE_GEMINI_INTENTS: Final[frozenset[str]] = frozenset(
    {
        "concept_map",
        "visual_schema",
        "reasoning",
        "personalized_teaching",
        "comparison",
    }
)

SUPPORTED_INTENTS: Final[frozenset[str]] = frozenset(
    {
        "explanation",
        "quiz",
        "translation",
        "dictation",
        "comparison",
        "concept_map",
        "visual_schema",
        "reasoning",
        "personalized_teaching",
        "timeline",
    }
)

SUPPORTED_VISUAL_TYPES: Final[frozenset[str]] = frozenset(
    {"process", "science_diagram", "math", "comparison", "timeline", "none"}
)


@dataclass(frozen=True)
class Settings:
    # --- Sarvam AI (STT) ---
    sarvam_api_key: str = field(default_factory=lambda: os.environ.get("SARVAM_API_KEY", ""))
    sarvam_stt_model: str = field(default_factory=lambda: os.environ.get("SARVAM_STT_MODEL", "saaras:v3"))

    # --- ElevenLabs (TTS) ---
    elevenlabs_api_key: str = field(default_factory=lambda: os.environ.get("ELEVENLABS_API_KEY", ""))
    elevenlabs_voice_id: str = field(
        default_factory=lambda: os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    )
    elevenlabs_model_id: str = field(
        default_factory=lambda: os.environ.get("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
    )

    # --- Groq (fast LLM) ---
    groq_api_key: str = field(default_factory=lambda: os.environ.get("GROQ_API_KEY", ""))
    groq_fast_model: str = field(default_factory=lambda: os.environ.get("GROQ_FAST_MODEL", "llama-3.1-8b-instant"))
    groq_main_model: str = field(
        default_factory=lambda: os.environ.get("GROQ_MAIN_MODEL", "llama-3.3-70b-versatile")
    )

    # --- Gemini (reasoning LLM) ---
    gemini_api_key: str = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY", ""))
    gemini_model: str = field(default_factory=lambda: os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"))

    # --- Routing / behaviour ---
    complexity_threshold: int = field(default_factory=lambda: _get_int("COMPLEXITY_THRESHOLD", 7))
    default_quiz_questions: int = field(default_factory=lambda: _get_int("DEFAULT_QUIZ_QUESTIONS", 5))
    explanation_language: str = field(
        default_factory=lambda: os.environ.get("EXPLANATION_LANGUAGE", "hinglish")
    )

    # --- Ops ---
    log_level: str = field(default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO"))
    cache_ttl_seconds: int = field(default_factory=lambda: _get_int("CACHE_TTL_SECONDS", 600))
    request_timeout_seconds: int = field(default_factory=lambda: _get_int("REQUEST_TIMEOUT_SECONDS", 30))
    max_retries: int = field(default_factory=lambda: _get_int("MAX_RETRIES", 3))

    # --- Convenience flags ---
    @property
    def has_sarvam(self) -> bool:
        return bool(self.sarvam_api_key)

    @property
    def has_elevenlabs(self) -> bool:
        return bool(self.elevenlabs_api_key)

    @property
    def has_groq(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def has_gemini(self) -> bool:
        return bool(self.gemini_api_key)

    def missing_required(self) -> list[str]:
        """Groq (classification) is the one hard dependency for the
        pipeline to run at all; everything else degrades gracefully."""
        missing = []
        if not self.has_groq:
            missing.append("GROQ_API_KEY")
        return missing

    def status_report(self) -> dict[str, bool]:
        return {
            "Sarvam AI (Speech-to-Text)": self.has_sarvam,
            "ElevenLabs (Text-to-Speech)": self.has_elevenlabs,
            "Groq (Fast LLM + Classifier)": self.has_groq,
            "Gemini (Reasoning LLM)": self.has_gemini,
        }


settings = Settings()
