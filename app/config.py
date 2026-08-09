from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://interview:interview@localhost:5433/interview_platform"

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-4o-mini"

    # Interview cascade (STT -> LLM -> TTS), all via OpenRouter.
    interview_llm_model: str = "nvidia/nemotron-3-ultra-550b-a55b:free"
    # Paid fallback for interview_llm_model specifically — it's the one genuinely
    # free-tier leg of the cascade (R-004); IA-002 observed it return a malformed
    # response live. deepseek/deepseek-v4-pro was already the documented
    # contingency in R-003/R-004 before this fallback was actually built (IA-009).
    interview_llm_fallback_model: str = "deepseek/deepseek-v4-pro"
    stt_model: str = "qwen/qwen3-asr-flash-2026-02-10"
    tts_model: str = "hexgrad/kokoro-82m"
    tts_voice: str = "af_heart"

    resume_storage_dir: str = "./data/resumes"


settings = Settings()
