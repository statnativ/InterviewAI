"""Text-to-speech via OpenRouter's OpenAI-compatible /audio/speech endpoint.

Unlike chat completions and transcription, this endpoint returns raw audio
bytes directly (not JSON) — Content-Type tells you mp3 vs pcm.
"""

from app.config import settings
from app.services.llm_client import LLMError, get_http_client


async def synthesize(text: str, voice: str | None = None) -> bytes:
    if not settings.openrouter_api_key:
        raise LLMError("OPENROUTER_API_KEY is not set — add it to .env")

    payload = {
        "model": settings.tts_model,
        "input": text,
        "voice": voice or settings.tts_voice,
        "response_format": "mp3",
    }

    response = await get_http_client().post(
        f"{settings.openrouter_base_url}/audio/speech",
        headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
        json=payload,
    )

    if response.status_code != 200:
        raise LLMError(f"OpenRouter TTS failed ({response.status_code}): {response.text}")

    return response.content
