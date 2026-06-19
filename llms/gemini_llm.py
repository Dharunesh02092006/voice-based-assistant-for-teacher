"""
Gemini 2.5 Flash generation provider.

Used by the rule engine for intents that need deeper structural reasoning
(concept maps, visual schemas, multi-step reasoning, personalized teaching,
comparisons) or whenever the classifier scores complexity >= threshold.
"""

from __future__ import annotations

from google import genai

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

PROVIDER_NAME = "gemini"


class GeminiLLM:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else settings.gemini_api_key
        self._model = model or settings.gemini_model
        self._client: genai.Client | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _get_client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def _require_configured(self) -> None:
        if not self.is_configured:
            raise GenerationError("GEMINI_API_KEY is not configured.")

    @retry_with_backoff(retry_on=(Exception,))
    def _complete_json(self, prompt: str) -> dict:
        client = self._get_client()
        response = client.models.generate_content(
            model=self._model,
            contents=prompt,
            config={"response_mime_type": "application/json", "temperature": 0.5},
        )
        raw_text = response.text or ""
        return safe_json_parse(raw_text)

    def generate_raw(self, prompt: str, temperature: float = 0.7) -> str:
        """Freeform (non-JSON-mode) generation, e.g. for the bonus SVG
        illustration feature which needs raw markup rather than a JSON
        envelope."""
        self._require_configured()
        return self._generate_raw_with_retry(prompt, temperature)

    @retry_with_backoff(retry_on=(Exception,))
    def _generate_raw_with_retry(self, prompt: str, temperature: float) -> str:
        client = self._get_client()
        response = client.models.generate_content(
            model=self._model,
            contents=prompt,
            config={"temperature": temperature},
        )
        return response.text or ""

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
        payload = self._complete_json(prompt)
        result = coerce_explanation(payload, fallback_visual_type=visual_type, provider=PROVIDER_NAME)
        logger.info("Gemini generated explanation: '%s'", result.title)
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
        payload = self._complete_json(prompt)
        result = coerce_quiz(payload, provider=PROVIDER_NAME)
        logger.info("Gemini generated quiz '%s' with %d questions", result.title, len(result.questions))
        return result
