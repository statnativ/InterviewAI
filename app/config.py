from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://interview:interview@localhost:5433/interview_platform"

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-4o-mini"

    # Interview cascade (STT -> LLM -> TTS), all via OpenRouter.
    interview_llm_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    stt_model: str = "qwen/qwen3-asr-flash-2026-02-10"
    tts_model: str = "hexgrad/kokoro-82m"
    tts_voice: str = "af_heart"

    resume_storage_dir: str = "./data/resumes"


settings = Settings()
