import os

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib.parse import urlparse


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Ollama Configuration
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", description="Ollama API base")

    # LLM Configuration (single node)
    LLM_MODEL: str = Field(default="qwen3:14b", description="LLM model name")
    LLM_STREAM: bool = Field(default=True, description="LLM stream mode")
    LLM_TEMPERATURE: float = Field(default=0.1, description="LLM temperature")
    LLM_NUM_CTX: int = Field(default=8192, description="LLM context window size")
    LLM_TOP_P: float = Field(default=0, description="top_p")
    LLM_TOP_K: int = Field(default=30, description="top_k")
    LLM_THINK: bool = Field(default=False, description="think (Ollama)")
    LLM_NUM_PREDICT: int = Field(default=-1, description="num_predict")

    # Backpressure / queueing to avoid concurrent overload
    # How many concurrent requests are allowed PER (model, base_url). Usually keep at 1 for fair benchmarking.
    LLM_MAX_CONCURRENT_REQUESTS: int = Field(default=1, description="Max concurrent LLM requests per model")
    # If set, a request will wait in queue up to this many seconds; then returns 429.
    # If empty/None, waits indefinitely.
    LLM_QUEUE_TIMEOUT_SECONDS: float | None = Field(default=None, description="Queue wait timeout (seconds)")

    RECURSION_LIMIT: int = Field(default=80,
                                 description="Максимум шагов графа (assistant/executor/coder/validator) за один запрос.")

    # Observability (optional)
    PHOENIX_COLLECTOR_ENDPOINT: str = Field(
        default="",
        description="OTLP endpoint Phoenix collector"
    )
    PHOENIX_PROJECT_NAME: str = Field(default="workshop")
    PHOENIX_AUTO_INSTRUMENT: bool = Field(default=True, description="Включить авто-инструментацию (OpenInference/LangChain и др.)")
    PHOENIX_OTLP_PROTOCOL: str = Field(
        default="",
        description="OTLP protocol: 'grpc' или 'http/protobuf'. Если пусто — определяем по endpoint.",
    )
    # Chat state
    CONVERSATION_TTL_SECONDS: int = Field(default=60 * 60)
    CONVERSATION_MAX_ITEMS: int = Field(default=10_000)

    STREAM_PROGRESS_EVENTS: bool = Field(
        default=True,
        description="Стримить ход графа (узлы, инструменты) в SSE по мере выполнения, не только финальный текст.",
    )

    STREAM_PROGRESS_HTML: bool = Field(
        default=True,
        description="Прогресс в HTML: многострочные <details>. Если false — текстовый префикс.",
    )

    @field_validator('OLLAMA_BASE_URL')
    def validate_ollama_url(cls, v):
        if v:
            parsed = urlparse(v)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError('Invalid OLLAMA_BASE_URL format')
        return v

    @field_validator("LLM_MODEL")
    def validate_llm_model(cls, v: str) -> str:
        # Empty model name will cause Ollama to fail with "model is required".
        vv = (v or "").strip()
        if not vv:
            raise ValueError("LLM_MODEL must be a non-empty model name (e.g. 'qwen3:14b')")
        return vv


settings = Settings()