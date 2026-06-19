"""
ElevenLabs Text-to-Speech wrapper.

TTS is treated as a "nice to have" final step of the pipeline: if it fails
or isn't configured, the rest of the lesson (visual + explanation text)
still renders. We never let a TTS failure block the smart board.
"""

from __future__ import annotations

from elevenlabs.client import ElevenLabs

from config.settings import settings
from utils.logger import get_logger
from utils.retry import retry_with_backoff

logger = get_logger(__name__)


class TTSError(RuntimeError):
    """Raised when speech synthesis fails after all retries."""


class ElevenLabsTTS:
    def __init__(self, api_key: str | None = None, voice_id: str | None = None, model_id: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else settings.elevenlabs_api_key
        self._voice_id = voice_id or settings.elevenlabs_voice_id
        self._model_id = model_id or settings.elevenlabs_model_id
        self._client: ElevenLabs | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _get_client(self) -> ElevenLabs:
        if self._client is None:
            self._client = ElevenLabs(api_key=self._api_key)
        return self._client

    def synthesize(self, text: str, voice_id: str | None = None) -> bytes | None:
        """Return MP3 bytes for `text`, or None if TTS is unavailable/fails.

        Deliberately swallows errors (after retrying) rather than raising,
        since a missing audio clip should never prevent the visual +
        explanation from being shown.
        """
        if not self.is_configured:
            logger.info("ElevenLabs not configured; skipping speech synthesis.")
            return None
        if not text or not text.strip():
            return None

        try:
            return self._synthesize_with_retry(text.strip(), voice_id or self._voice_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("TTS synthesis failed after retries: %s", exc)
            return None

    @retry_with_backoff(retry_on=(Exception,))
    def _synthesize_with_retry(self, text: str, voice_id: str) -> bytes:
        client = self._get_client()
        audio_stream = client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id=self._model_id,
            output_format="mp3_44100_128",
        )
        # The SDK may return bytes directly or a generator of chunks.
        if isinstance(audio_stream, (bytes, bytearray)):
            return bytes(audio_stream)
        return b"".join(chunk for chunk in audio_stream)
