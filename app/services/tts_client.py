"""Text-to-speech via OpenRouter's OpenAI-compatible /audio/speech endpoint.

Unlike chat completions and transcription, this endpoint returns raw audio
bytes directly (not JSON) — Content-Type tells you mp3 vs pcm.
"""

from app.config import settings
from app.services.llm_client import LLMError, post_with_retry


async def synthesize(text: str, voice: str | None = None) -> bytes:
    if not settings.openrouter_api_key:
        raise LLMError("OPENROUTER_API_KEY is not set — add it to .env")

    payload = {
        "model": settings.tts_model,
        "input": text,
        "voice": voice or settings.tts_voice,
        "response_format": "mp3",
    }

    # One same-model retry after a short backoff (IA-009) — kokoro-82m is a
    # paid model (~$0.62/M chars per AI Architecture.md), not free-tier, so a
    # timeout here (observed live during IA-002) reads as transient service
    # trouble, not rate-limiting; there's no second TTS model on record to
    # fall back to, so retrying is the honest fix, not a model swap.
    response = await post_with_retry(
        f"{settings.openrouter_base_url}/audio/speech", payload, retries=1
    )

    return response.content
