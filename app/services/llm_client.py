"""Thin wrapper around OpenRouter's OpenAI-compatible chat completions endpoint.

Model name is config-driven (settings.openrouter_model), so swapping providers
or models later — Gemini, GPT-4o, whatever's cheapest — is an env var change,
not a code change in any caller.
"""

import asyncio

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


async def post_with_retry(url: str, payload: dict, *, retries: int = 0, backoff: float = 1.0) -> httpx.Response:
    """POST via the shared client, retrying on timeout/network/non-200 failures.

    retries=0 means a single attempt, no retry — used by chat_completion's
    fallback path, where resilience means trying a *different* model, not
    repeating the same request against the same one. retries=1 (stt_client,
    tts_client) means one same-request retry after a short backoff — there's
    no second model to fall back to for STT/TTS.

    A raw httpx.TimeoutException/TransportError used to propagate uncaught
    here (that's exactly what crashed IA-002's first latency run — a 60s TTS
    timeout with no LLMError, no retry, nothing) — wrapping it is what makes
    the retry loop below actually reachable.
    """
    last_error: LLMError | None = None
    for attempt in range(retries + 1):
        try:
            response = await get_http_client().post(
                url,
                headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
                json=payload,
            )
        except (httpx.TimeoutException, httpx.TransportError) as e:
            last_error = LLMError(f"Request to {url} (model={payload.get('model')}) timed out or failed: {e}")
        else:
            if response.status_code == 200:
                return response
            last_error = LLMError(f"OpenRouter request failed ({response.status_code}): {response.text}")
        if attempt < retries:
            await asyncio.sleep(backoff)
    raise last_error


def _extract_content(data: dict) -> str:
    # A 200 response isn't a guarantee of the expected shape — free-tier
    # models can return an error/empty body with a 200 status. Validate
    # before indexing so a shape mismatch raises a clean LLMError instead of
    # an unhandled KeyError/IndexError (reproduced live during IA-002's
    # latency run against interview_llm_model). Mirrors stt_client.py's
    # existing "surface the raw payload, don't index blindly" convention.
    choices = data.get("choices")
    if not choices or "message" not in choices[0] or "content" not in choices[0]["message"]:
        raise LLMError(f"Unexpected chat completion response shape, no usable 'choices': {data}")
    return choices[0]["message"]["content"]


async def chat_completion(
    messages: list[dict],
    model: str | None = None,
    exclude_reasoning: bool = False,
    fallback_model: str | None = None,
) -> str:
    """fallback_model is opt-in per call site, not a global default — only the
    interview cascade (the one genuinely free-tier model, R-004) passes one.
    Every other caller (question generation, résumé parsing) keeps its
    existing single-attempt behavior against its own (paid) model."""
    if not settings.openrouter_api_key:
        raise LLMError("OPENROUTER_API_KEY is not set — add it to .env")

    def _payload(target_model: str) -> dict:
        payload = {"model": target_model, "messages": messages}
        if exclude_reasoning:
            # Reasoning models (e.g. Nemotron 3 Ultra) can otherwise leak their
            # internal "thinking" into message.content instead of a separate
            # reasoning field — fine for text scoring, not fine for something
            # that gets spoken aloud to a candidate.
            payload["reasoning"] = {"exclude": True}
        return payload

    url = f"{settings.openrouter_base_url}/chat/completions"
    primary_model = model or settings.openrouter_model

    try:
        response = await post_with_retry(url, _payload(primary_model))
        return _extract_content(response.json())
    except LLMError as primary_error:
        if fallback_model is None or fallback_model == primary_model:
            raise
        try:
            response = await post_with_retry(url, _payload(fallback_model))
            return _extract_content(response.json())
        except LLMError as fallback_error:
            raise LLMError(
                f"Both primary ({primary_model}) and fallback ({fallback_model}) failed. "
                f"Primary: {primary_error}. Fallback: {fallback_error}."
            ) from fallback_error
