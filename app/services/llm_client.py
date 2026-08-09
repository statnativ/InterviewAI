"""Thin wrapper around OpenRouter's OpenAI-compatible chat completions endpoint.

Model name is config-driven (settings.openrouter_model), so swapping providers
or models later — Gemini, GPT-4o, whatever's cheapest — is an env var change,
not a code change in any caller.
"""

import httpx

from app.config import settings


class LLMError(RuntimeError):
    pass


# Shared across llm_client/stt_client/tts_client (all three OpenRouter legs of
# the interview cascade) instead of each opening its own client per call — a
# fresh httpx.AsyncClient() means a fresh TCP/TLS handshake every time, which
# is three extra handshakes per interview turn for no reason (ADR-007). Lazy
# module-level singleton: fine for both the FastAPI process and standalone
# scripts, never explicitly closed — connection reuse is the point, and
# process exit cleans it up.
_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=60)
    return _client


async def chat_completion(messages: list[dict], model: str | None = None, exclude_reasoning: bool = False) -> str:
    if not settings.openrouter_api_key:
        raise LLMError("OPENROUTER_API_KEY is not set — add it to .env")

    payload = {
        "model": model or settings.openrouter_model,
        "messages": messages,
    }
    if exclude_reasoning:
        # Reasoning models (e.g. Nemotron 3 Ultra) can otherwise leak their
        # internal "thinking" into message.content instead of a separate
        # reasoning field — fine for text scoring, not fine for something
        # that gets spoken aloud to a candidate.
        payload["reasoning"] = {"exclude": True}

    response = await get_http_client().post(
        f"{settings.openrouter_base_url}/chat/completions",
        headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
        json=payload,
    )

    if response.status_code != 200:
        raise LLMError(f"OpenRouter request failed ({response.status_code}): {response.text}")

    data = response.json()
    return data["choices"][0]["message"]["content"]
