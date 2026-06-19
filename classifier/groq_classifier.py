"""
Step 1 of the architecture: a lightweight Groq classifier.

Input: the teacher's transcribed query.
Output: {"intent", "complexity", "requires_visual", "visual_type"} — consumed
by router/task_router.py's rule engine to pick Groq vs Gemini for the actual
generation step.
"""

from __future__ import annotations

from groq import Groq

from config.settings import settings
from llms.base import ClassificationResult, coerce_classification, load_prompt
from utils.cache import TTLCache, cached
from utils.json_parsing import safe_json_parse
from utils.logger import get_logger
from utils.retry import retry_with_backoff

logger = get_logger(__name__)
_classification_cache = TTLCache()


class ClassifierError(RuntimeError):
    """Raised when the classifier cannot produce a usable result."""


class QueryClassifier:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else settings.groq_api_key
        self._model = model or settings.groq_fast_model
        self._client: Groq | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _get_client(self) -> Groq:
        if self._client is None:
            self._client = Groq(api_key=self._api_key)
        return self._client

    @cached(_classification_cache, prefix="classify")
    def classify(self, query: str) -> ClassificationResult:
        if not self.is_configured:
            raise ClassifierError(
                "GROQ_API_KEY is not configured. This key is required for the classifier "
                "that powers the whole routing pipeline."
            )
        if not query or not query.strip():
            raise ClassifierError("Cannot classify an empty query.")

        return self._classify_with_retry(query.strip())

    @retry_with_backoff(retry_on=(Exception,))
    def _classify_with_retry(self, query: str) -> ClassificationResult:
        prompt = load_prompt("classify.txt", query=query)
        client = self._get_client()

        completion = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_completion_tokens=200,
        )
        raw_text = completion.choices[0].message.content or ""
        payload = safe_json_parse(raw_text)
        result = coerce_classification(payload)

        logger.info(
            "Classified query as intent=%s complexity=%d requires_visual=%s visual_type=%s",
            result.intent,
            result.complexity,
            result.requires_visual,
            result.visual_type,
        )
        return result
