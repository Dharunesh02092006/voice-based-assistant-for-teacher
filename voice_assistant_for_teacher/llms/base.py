"""
Shared data contracts and prompt-loading utilities for the LLM layer.

Both `groq_llm.py` and `gemini_llm.py` implement the same interface and
produce the same validated dataclasses, so `router/task_router.py` and the
Streamlit UI never need to know which provider actually answered a given
request.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config.settings import PROMPTS_DIR, SUPPORTED_VISUAL_TYPES, settings


# ---------------------------------------------------------------------------
# Data contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClassificationResult:
    intent: str
    complexity: int
    requires_visual: bool
    visual_type: str


@dataclass(frozen=True)
class ExplanationResult:
    title: str
    explanation: str
    visual_type: str
    key_points: list[str]
    diagram: dict[str, Any]
    provider: str = "unknown"


@dataclass(frozen=True)
class QuizQuestion:
    question: str
    options: list[str]
    answer: str


@dataclass(frozen=True)
class QuizResult:
    title: str
    questions: list[QuizQuestion] = field(default_factory=list)
    provider: str = "unknown"


class GenerationError(RuntimeError):
    """Raised when an LLM provider fails to produce a usable, valid result."""


# ---------------------------------------------------------------------------
# Prompt templating
# ---------------------------------------------------------------------------


def load_prompt(filename: str, **replacements: str) -> str:
    """Load prompts/<filename> and substitute {{TOKEN}} placeholders.

    Plain `str.replace` is used instead of `str.format` because the prompt
    files contain literal JSON braces (e.g. `{"intent": ...}`) that must NOT
    be treated as format placeholders.
    """
    path = PROMPTS_DIR / filename
    text = path.read_text(encoding="utf-8")
    for key, value in replacements.items():
        text = text.replace(f"{{{{{key.upper()}}}}}", str(value))
    return text


def visual_schema_doc() -> str:
    return (PROMPTS_DIR / "visual.txt").read_text(encoding="utf-8")


def language_instruction(language: str | None = None) -> str:
    lang = (language or settings.explanation_language).lower()
    if lang == "english":
        return "Write entirely in clear, simple English."
    return (
        "Write in natural Hinglish (Hindi mixed with common English words, written in "
        "Latin/Roman script, the way Haryana teachers actually speak in class) — e.g. "
        "'Photosynthesis ek process hai jisme plants sunlight ko energy mein convert karte hain.'"
    )


# ---------------------------------------------------------------------------
# Output validation/repair helpers
# ---------------------------------------------------------------------------


def coerce_classification(payload: dict[str, Any]) -> ClassificationResult:
    from config.settings import SUPPORTED_INTENTS  # local import avoids cycle at module load

    intent = str(payload.get("intent", "")).strip().lower()
    if intent not in SUPPORTED_INTENTS:
        intent = "explanation"

    try:
        complexity = int(payload.get("complexity", 5))
    except (TypeError, ValueError):
        complexity = 5
    complexity = max(1, min(10, complexity))

    requires_visual = bool(payload.get("requires_visual", False))

    visual_type = str(payload.get("visual_type", "none")).strip().lower()
    if visual_type not in SUPPORTED_VISUAL_TYPES:
        visual_type = "none"
    if not requires_visual:
        visual_type = "none"

    return ClassificationResult(
        intent=intent,
        complexity=complexity,
        requires_visual=requires_visual,
        visual_type=visual_type,
    )


def coerce_explanation(payload: dict[str, Any], fallback_visual_type: str, provider: str) -> ExplanationResult:
    title = str(payload.get("title") or "Untitled Topic").strip()
    explanation = str(payload.get("explanation") or "").strip()
    if not explanation:
        raise GenerationError("Model returned an empty explanation.")

    visual_type = str(payload.get("visual_type") or fallback_visual_type).strip().lower()
    if visual_type not in SUPPORTED_VISUAL_TYPES:
        visual_type = fallback_visual_type if fallback_visual_type in SUPPORTED_VISUAL_TYPES else "none"

    raw_points = payload.get("key_points") or []
    key_points = [str(p).strip() for p in raw_points if str(p).strip()] if isinstance(raw_points, list) else []

    diagram = payload.get("diagram")
    if not isinstance(diagram, dict):
        diagram = {}

    return ExplanationResult(
        title=title,
        explanation=explanation,
        visual_type=visual_type,
        key_points=key_points,
        diagram=diagram,
        provider=provider,
    )


def coerce_quiz(payload: dict[str, Any], provider: str) -> QuizResult:
    title = str(payload.get("title") or "Quiz").strip()
    raw_questions = payload.get("questions") or []
    questions: list[QuizQuestion] = []

    if isinstance(raw_questions, list):
        for item in raw_questions:
            if not isinstance(item, dict):
                continue
            q_text = str(item.get("question") or "").strip()
            options = item.get("options") or []
            options = [str(o).strip() for o in options if str(o).strip()] if isinstance(options, list) else []
            answer = str(item.get("answer") or "").strip()

            if not q_text or len(options) < 2:
                continue
            if answer not in options:
                # Defensive repair: if the model paraphrased the answer slightly,
                # fall back to the first option rather than silently breaking
                # grading downstream.
                answer = options[0]

            questions.append(QuizQuestion(question=q_text, options=options, answer=answer))

    if not questions:
        raise GenerationError("Model did not return any usable quiz questions.")

    return QuizResult(title=title, questions=questions, provider=provider)
