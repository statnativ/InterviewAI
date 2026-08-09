"""Speech-to-text via OpenRouter's dedicated transcription endpoint.

Separate from llm_client.py's /chat/completions calls — transcription has its
own endpoint and JSON shape (base64 audio in, plain text out).
"""

import base64

import httpx

from app.config import settings
from app.services.llm_client import LLMError


async def transcribe(audio_bytes: bytes, audio_format: str = "wav") -> str:
    if not settings.openrouter_api_key:
        raise LLMError("OPENROUTER_API_KEY is not set — add it to .env")

    payload = {
        "model": settings.stt_model,
        "input_audio": {
            "data": base64.b64encode(audio_bytes).decode("ascii"),
            "format": audio_format,
        },
    }

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{settings.openrouter_base_url}/audio/transcriptions",
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
            json=payload,
        )

    if response.status_code != 200:
        raise LLMError(f"OpenRouter transcription failed ({response.status_code}): {response.text}")

    data = response.json()
    # Field name isn't independently confirmed from OpenRouter's docs at time of
    # writing (OpenAI-compatible transcription APIs return {"text": ...}); fall
    # back to surfacing the raw payload so a shape mismatch is obvious, not silent.
    if "text" in data:
        return data["text"]
    raise LLMError(f"Unexpected transcription response shape, no 'text' field: {data}")
