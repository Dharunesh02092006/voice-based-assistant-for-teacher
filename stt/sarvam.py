"""
Sarvam AI Speech-to-Text wrapper.

Uses the Saaras v3 REST endpoint (POST /speech-to-text), which supports
flexible output modes. We default to "codemix" mode because Indian
classroom speech is naturally Hindi-English code-switched (e.g. a teacher
saying "aaj hum photosynthesis padhenge"), and codemix mode preserves that
mixing instead of forcing a single-language normalization — giving the
downstream classifier/LLMs the most faithful transcript to reason over.

Docs: https://docs.sarvam.ai/api-reference-docs/speech-to-text/transcribe
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests

from config.settings import settings
from utils.logger import get_logger
from utils.retry import retry_with_backoff

logger = get_logger(__name__)

_SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text"


class STTError(RuntimeError):
    """Raised when transcription fails after all retries."""


@dataclass(frozen=True)
class TranscriptionResult:
    transcript: str
    language_code: str | None
    language_probability: float | None
    raw: dict[str, Any]


class SarvamSTT:
    """Thin, retrying wrapper around the Sarvam AI speech-to-text REST API."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else settings.sarvam_api_key
        self._model = model or settings.sarvam_stt_model

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def transcribe(
        self,
        audio_bytes: bytes,
        filename: str = "speech.wav",
        language_code: str = "unknown",
        mode: str = "codemix",
    ) -> TranscriptionResult:
        """Transcribe a short (<30s) audio clip.

        Args:
            audio_bytes: raw audio file bytes (wav/mp3/ogg/webm/etc).
            filename: filename hint sent with the multipart upload, used by
                Sarvam to help detect the codec.
            language_code: BCP-47 code, or "unknown" to auto-detect.
            mode: one of transcribe | translate | verbatim | translit |
                codemix. Only honored by the saaras:v3 model.
        """
        if not self.is_configured:
            raise STTError(
                "SARVAM_API_KEY is not configured. Add it to your .env file to enable voice input."
            )
        if not audio_bytes:
            raise STTError("No audio data was captured. Please try recording again.")

        return self._transcribe_with_retry(audio_bytes, filename, language_code, mode)

    @retry_with_backoff(retry_on=(requests.RequestException, STTError))
    def _transcribe_with_retry(
        self, audio_bytes: bytes, filename: str, language_code: str, mode: str
    ) -> TranscriptionResult:
        headers = {"api-subscription-key": self._api_key}
        data: dict[str, str] = {"model": self._model, "language_code": language_code}
        if self._model.startswith("saaras"):
            data["mode"] = mode

        files = {"file": (filename, audio_bytes, "audio/wav")}

        try:
            response = requests.post(
                _SARVAM_STT_URL,
                headers=headers,
                data=data,
                files=files,
                timeout=settings.request_timeout_seconds,
            )
        except requests.RequestException as exc:
            logger.error("Sarvam STT request failed: %s", exc)
            raise

        if response.status_code == 429:
            raise STTError("Sarvam API rate limit hit; retrying.")
        if response.status_code >= 500:
            raise STTError(f"Sarvam API server error ({response.status_code}); retrying.")
        if response.status_code != 200:
            # 400/403/422 are not worth retrying — surface immediately.
            logger.error("Sarvam STT error %s: %s", response.status_code, response.text[:300])
            raise STTError(
                f"Speech-to-text failed ({response.status_code}). "
                "Check that your audio is under 30 seconds and SARVAM_API_KEY is valid."
            )

        payload = response.json()
        transcript = (payload.get("transcript") or "").strip()
        if not transcript:
            raise STTError("Could not detect any speech in the recording. Please try again.")

        return TranscriptionResult(
            transcript=transcript,
            language_code=payload.get("language_code"),
            language_probability=payload.get("language_probability"),
            raw=payload,
        )
