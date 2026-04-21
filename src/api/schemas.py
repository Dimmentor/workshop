from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool", "function"]
    content: Any | None = None
    name: Optional[str] = None
    model_config = ConfigDict(extra="allow")


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    model: str = "graph"
    messages: List[ChatMessage]

    # --- OpenAI-like knobs (kept for compatibility; mapped to Ollama options) ---
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None  # mapped to Ollama num_predict if provided

    # --- ChatOllama / Ollama native params (all optional, default None) ---
    reasoning: Optional[Union[bool, str]] = None
    validate_model_on_init: Optional[bool] = None

    mirostat: Optional[int] = None
    mirostat_eta: Optional[float] = None
    mirostat_tau: Optional[float] = None
    num_ctx: Optional[int] = None
    num_gpu: Optional[int] = None
    num_thread: Optional[int] = None
    num_predict: Optional[int] = None
    repeat_last_n: Optional[int] = None
    repeat_penalty: Optional[float] = None
    seed: Optional[int] = None
    stop: Optional[List[str]] = None
    tfs_z: Optional[float] = None
    top_k: Optional[int] = None

    format: Optional[Any] = None  # Literal["", "json"] | JSON schema (dict) | None
    keep_alive: Optional[Union[int, str]] = None
    base_url: Optional[str] = None
    client_kwargs: Optional[Dict[str, Any]] = None
    async_client_kwargs: Optional[Dict[str, Any]] = None
    sync_client_kwargs: Optional[Dict[str, Any]] = None

    # Raw Ollama options passthrough (has priority over individual option fields)
    options: Optional[Dict[str, Any]] = None

    stream: bool = False
    # Идентификатор диалога/потока состояния (LangGraph checkpoint key).
    # Поддерживаем оба поля для обратной совместимости.
    thread_id: Optional[str] = None
    conversation_id: Optional[str] = None
    # OpenWebUI/другие клиенты могут присылать chat_id
    chat_id: Optional[str] = None
    # Когда нет thread_id/conversation_id/chat_id, многие клиенты всё же шлют session_id — используем как ключ чата.
    session_id: Optional[str] = Field(
        default=None,
        description="Стабильный id сессии/чата (если нет thread_id). Должен повторяться между запросами.",
    )
    # Реплей состояния графа (OpenWebUI и др.) — подставляем, если чекпоинт/кэш пусты.
    branch_path: Optional[str] = Field(default=None, description="Подсказка workspace, если клиент передаёт состояние.")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Например {'branch_path': 'test'}.")


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: "ChatCompletionMessage"
    finish_reason: str = "stop"


class ChatCompletionMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: Optional[str] = None


class ChatCompletionUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletion(BaseModel):
    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage
    thread_id: Optional[str] = None  # Передай этот id в следующих запросах, чтобы сохранить контекст
    conversation_id: Optional[str] = None


class ModelInfo(BaseModel):
    id: str
    object: Literal["model"] = "model"
    created: int = 0
    owned_by: str = "workshop"


class ModelsList(BaseModel):
    object: Literal["list"] = "list"
    data: List[ModelInfo]
