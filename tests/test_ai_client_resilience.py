"""IA-009: LLM fallback + STT/TTS retry tests.

A fake httpx client double drives app.services.llm_client.get_http_client()
so these exercise the real retry/fallback code paths (post_with_retry,
chat_completion's fallback logic) rather than mocking chat_completion itself
the way test_question_generation.py does — this suite is specifically about
what happens when the underlying HTTP calls fail.
"""
import httpx
import pytest

from app.services import llm_client, stt_client, tts_client

pytestmark = pytest.mark.asyncio(loop_scope="session")


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, content=b""):
        self.status_code = status_code
        self._json = json_data
        self.text = "" if json_data is None else str(json_data)
        self.content = content

    def json(self):
        return self._json


class _FakeClient:
    """Each entry in `behaviors` is consumed in order per .post() call — an
    Exception instance to raise, or a _FakeResponse to return."""

    def __init__(self, behaviors: list):
        self.behaviors = list(behaviors)
        self.calls: list[dict] = []

    async def post(self, url, headers=None, json=None):
        self.calls.append({"url": url, "model": json.get("model")})
        behavior = self.behaviors.pop(0)
        if isinstance(behavior, Exception):
            raise behavior
        return behavior


@pytest.fixture
def fake_client(monkeypatch):
    def _install(behaviors: list) -> _FakeClient:
        client = _FakeClient(behaviors)
        monkeypatch.setattr(llm_client, "_client", client)
        monkeypatch.setattr(llm_client, "get_http_client", lambda: client)
        return client

    return _install


@pytest.fixture(autouse=True)
def no_real_backoff(monkeypatch):
    """post_with_retry sleeps between retries — skip the wait in tests."""

    async def instant(_seconds):
        return None

    monkeypatch.setattr(llm_client.asyncio, "sleep", instant)


def _completion_response(text="ok"):
    return _FakeResponse(200, {"choices": [{"message": {"content": text}}]})


async def test_chat_completion_falls_back_on_primary_timeout(fake_client):
    client = fake_client([httpx.ReadTimeout("slow"), _completion_response("fallback answer")])
    result = await llm_client.chat_completion(
        [{"role": "user", "content": "hi"}], model="free/model", fallback_model="paid/model"
    )
    assert result == "fallback answer"
    assert [c["model"] for c in client.calls] == ["free/model", "paid/model"]


async def test_chat_completion_falls_back_on_malformed_response(fake_client):
    """The exact shape mismatch IA-002 reproduced live: a 200 with no 'choices'."""
    client = fake_client([_FakeResponse(200, {"error": "internal"}), _completion_response("fallback answer")])
    result = await llm_client.chat_completion(
        [{"role": "user", "content": "hi"}], model="free/model", fallback_model="paid/model"
    )
    assert result == "fallback answer"


async def test_chat_completion_raises_when_both_primary_and_fallback_fail(fake_client):
    fake_client([httpx.ReadTimeout("slow"), _FakeResponse(500, content=b"")])
    with pytest.raises(llm_client.LLMError, match="Both primary .* and fallback .* failed"):
        await llm_client.chat_completion(
            [{"role": "user", "content": "hi"}], model="free/model", fallback_model="paid/model"
        )


async def test_chat_completion_without_fallback_configured_fails_immediately(fake_client):
    """Every non-cascade caller (question generation, résumé parsing) doesn't
    pass fallback_model — confirms they keep today's single-attempt behavior,
    not a new retry they never asked for."""
    client = fake_client([httpx.ReadTimeout("slow")])
    with pytest.raises(llm_client.LLMError):
        await llm_client.chat_completion([{"role": "user", "content": "hi"}], model="openai/gpt-4o-mini")
    assert len(client.calls) == 1


async def test_transcribe_retries_once_then_succeeds(fake_client):
    client = fake_client([httpx.ReadTimeout("slow"), _FakeResponse(200, {"text": "hello"})])
    result = await stt_client.transcribe(b"audio-bytes")
    assert result == "hello"
    assert len(client.calls) == 2


async def test_transcribe_raises_after_exhausting_retry(fake_client):
    fake_client([httpx.ReadTimeout("slow"), httpx.ReadTimeout("slow again")])
    with pytest.raises(llm_client.LLMError):
        await stt_client.transcribe(b"audio-bytes")


async def test_synthesize_retries_once_then_succeeds(fake_client):
    client = fake_client([httpx.ConnectError("refused"), _FakeResponse(200, content=b"mp3-bytes")])
    result = await tts_client.synthesize("hello world")
    assert result == b"mp3-bytes"
    assert len(client.calls) == 2


async def test_synthesize_raises_after_exhausting_retry(fake_client):
    fake_client([httpx.ReadTimeout("slow"), _FakeResponse(503, content=b"")])
    with pytest.raises(llm_client.LLMError):
        await tts_client.synthesize("hello world")
