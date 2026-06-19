"""
The multi-LLM routing system described in the architecture:

    Teacher Voice -> Sarvam STT -> Groq Classifier -> Rule Engine
    -> Groq OR Gemini -> Structured Educational JSON -> Visual Router
    -> Smart Board UI -> ElevenLabs Audio

This module owns the "Rule Engine" + orchestration steps: given a
transcribed query, it classifies intent/complexity, decides which LLM
should generate the actual content, calls it, and returns a single
structured result the UI can render without caring which provider answered.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from classifier.groq_classifier import QueryClassifier
from config.settings import FORCE_GEMINI_INTENTS, settings
from llms.base import ClassificationResult, ExplanationResult, GenerationError, QuizResult
from llms.gemini_llm import GeminiLLM
from llms.groq_llm import GroqLLM
from utils.logger import get_logger

logger = get_logger(__name__)

GenerationResult = Union[ExplanationResult, QuizResult]


@dataclass(frozen=True)
class RouterResult:
    classification: ClassificationResult
    provider_requested: str
    provider_used: str
    fallback_applied: bool
    content: GenerationResult


def choose_provider(intent: str, complexity: int) -> str:
    """The rule engine:

        if intent in FORCE_GEMINI: use Gemini
        elif complexity >= threshold: use Gemini
        else: use Groq
    """
    if intent in FORCE_GEMINI_INTENTS:
        return "gemini"
    if complexity >= settings.complexity_threshold:
        return "gemini"
    return "groq"


class TaskRouter:
    def __init__(
        self,
        classifier: QueryClassifier | None = None,
        groq_llm: GroqLLM | None = None,
        gemini_llm: GeminiLLM | None = None,
    ) -> None:
        self.classifier = classifier or QueryClassifier()
        self.groq_llm = groq_llm or GroqLLM()
        self.gemini_llm = gemini_llm or GeminiLLM()

    def handle_query(
        self,
        query: str,
        language: str | None = None,
        num_quiz_questions: int | None = None,
    ) -> RouterResult:
        classification = self.classifier.classify(query)
        provider_requested = choose_provider(classification.intent, classification.complexity)
        provider_used = provider_requested
        fallback_applied = False

        # Graceful degradation: if the rule engine wants Gemini but it isn't
        # configured, fall back to Groq rather than hard-failing the request.
        if provider_used == "gemini" and not self.gemini_llm.is_configured:
            logger.warning("Gemini requested but not configured; falling back to Groq.")
            provider_used = "groq"
            fallback_applied = True

        llm = self.gemini_llm if provider_used == "gemini" else self.groq_llm

        if classification.intent == "quiz":
            n = num_quiz_questions or settings.default_quiz_questions
            content: GenerationResult = llm.generate_quiz(
                query=query, complexity=classification.complexity, num_questions=n, language=language
            )
        else:
            content = llm.generate_explanation(
                query=query,
                intent=classification.intent,
                complexity=classification.complexity,
                visual_type=classification.visual_type,
                language=language,
            )

        return RouterResult(
            classification=classification,
            provider_requested=provider_requested,
            provider_used=provider_used,
            fallback_applied=fallback_applied,
            content=content,
        )
