"""
Groq generation provider.

Used by the rule engine for intents/complexity that don't need Gemini's
deeper reasoning — i.e. the fast path for everyday explanations and quizzes.
"""

from __future__ import annotations

from groq import Groq

from config.settings import settings
from llms.base import (
    ExplanationResult,
    GenerationError,
    QuizResult,
    coerce_explanation,
    coerce_quiz,
    language_instruction,
    load_prompt,
    visual_schema_doc,
)
from utils.json_parsing import safe_json_parse
from utils.logger import get_logger
from utils.retry import retry_with_backoff

logger = get_logger(__name__)

PROVIDER_NAME = "groq"


class GroqLLM:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else settings.groq_api_key
        self._model = model or settings.groq_main_model
        self._client: Groq | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _get_client(self) -> Groq:
        if self._client is None:
            self._client = Groq(api_key=self._api_key)
        return self._client

    def _require_configured(self) -> None:
        if not self.is_configured:
            raise GenerationError("GROQ_API_KEY is not configured.")

    @retry_with_backoff(retry_on=(Exception,))
    def _complete_json(self, prompt: str, max_tokens: int) -> dict:
        client = self._get_client()
        completion = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.4,
            max_completion_tokens=max_tokens,
        )
        raw_text = completion.choices[0].message.content or ""
        return safe_json_parse(raw_text)

    def generate_explanation(
        self, query: str, intent: str, complexity: int, visual_type: str, language: str | None = None
    ) -> ExplanationResult:
        self._require_configured()
        prompt = load_prompt(
            "simplify.txt",
            query=query,
            intent=intent,
            complexity=complexity,
            visual_type=visual_type,
            language_instruction=language_instruction(language),
            visual_schema_doc=visual_schema_doc(),
        )
        payload = self._complete_json(prompt, max_tokens=900)
        result = coerce_explanation(payload, fallback_visual_type=visual_type, provider=PROVIDER_NAME)
        logger.info("Groq generated explanation: '%s'", result.title)
        return result

    def generate_quiz(
        self, query: str, complexity: int, num_questions: int, language: str | None = None
    ) -> QuizResult:
        self._require_configured()
        prompt = load_prompt(
            "quiz.txt",
            query=query,
            complexity=complexity,
            num_questions=num_questions,
            language_instruction=language_instruction(language),
        )
        payload = self._complete_json(prompt, max_tokens=200 + 150 * num_questions)
        result = coerce_quiz(payload, provider=PROVIDER_NAME)
        logger.info("Groq generated quiz '%s' with %d questions", result.title, len(result.questions))
        return result
