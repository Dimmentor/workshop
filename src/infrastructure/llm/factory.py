import json
import os
from functools import lru_cache
from typing import Optional, Any
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama
from src.config import settings
from src.infrastructure.observability.tracing import get_tracer

_tracer = get_tracer(__name__)


def _serialize_for_trace(obj: Any, max_length: int = 4000) -> str:
    """
    Unified serialization function for tracing.
    Handles messages, responses, and general objects.
    """
    try:
        if hasattr(obj, "content"):
            result = str(obj.content)
        elif isinstance(obj, list) and obj:
            serialized = []
            for m in obj:
                serialized.append({
                    "type": m.__class__.__name__,
                    "content": getattr(m, "content", ""),
                })
            result = json.dumps(serialized, ensure_ascii=False)
        else:
            result = str(obj)
        return result[:max_length] if max_length else result
    except (TypeError, ValueError):
        return "unserializable"


class TracedChatOllama(ChatOllama):
    """Явные спаны LLM, если авто-инструментация LangChain/Ollama не видна в UI."""

    async def ainvoke(self, *args, **kwargs):
        messages = args[0] if args else kwargs.get("input", [])

        with _tracer.start_as_current_span("ollama.chat.invoke") as span:
            span.set_attribute("llm.vendor", "ollama")
            span.set_attribute("llm.model", self.model)
            span.set_attribute("llm.base_url", self.base_url)
            span.set_attribute("llm.input.messages", _serialize_for_trace(messages))

            response = await super().ainvoke(*args, **kwargs)

            span.set_attribute("llm.output", _serialize_for_trace(response))

            return response

    async def astream(self, *args, **kwargs):
        messages = args[0] if args else kwargs.get("input", [])

        with _tracer.start_as_current_span("ollama.chat.stream") as span:
            span.set_attribute("llm.vendor", "ollama")
            span.set_attribute("llm.model", self.model)
            span.set_attribute("llm.input.messages", _serialize_for_trace(messages))

            full_response = ""

            async for chunk in super().astream(*args, **kwargs):
                try:
                    if hasattr(chunk, "content") and chunk.content:
                        full_response += chunk.content
                except (AttributeError, TypeError):
                    pass

                yield chunk

            span.set_attribute("llm.output", _serialize_for_trace(full_response))


def _manual_llm_spans_enabled() -> bool:
    """
    Глобально включить TracedChatOllama для всех ролей (дубли с авто-инструментацией возможны).
    По умолчанию выключено; для кодера см. settings.OLLAMA_TRACE_CODER.
    """
    v = (os.getenv("ORCHESTRATOR_MANUAL_LLM_SPANS") or "false").strip().lower()
    return v in ("1", "true", "yes", "y", "on")


def _use_traced_ollama(role: str) -> bool:
    if _manual_llm_spans_enabled():
        return True
    return bool(role == "coder" and settings.OLLAMA_TRACE_CODER)


@lru_cache(maxsize=32)
def _create_llm_instance(
    model: str,
    base_url: str,
    stream: bool,
    temperature: float,
    num_ctx: int,
    top_p: float,
    top_k: int,
    think: bool,
    num_predict: int,
    use_traced: bool
) -> BaseChatModel:
    """Create LLM instance with caching - actual LLM creation logic."""
    llm_cls = TracedChatOllama if use_traced else ChatOllama
    return llm_cls(
        model=model,
        base_url=base_url,
        stream=stream,
        temperature=temperature,
        num_ctx=num_ctx,
        top_p=top_p,
        top_k=top_k,
        options={"num_predict": num_predict, "think": think} if think else {"num_predict": num_predict},
    )


def get_llm(
    role: str,
    *,
    base_url: Optional[str] = None,
    model: Optional[str] = None
) -> BaseChatModel:

    base_url = base_url or settings.OLLAMA_BASE_URL
    model = model or settings.LLM_MODEL

    temperature = settings.LLM_TEMPERATURE
    num_ctx = settings.LLM_NUM_CTX
    stream = settings.LLM_STREAM
    top_p = settings.LLM_TOP_P
    top_k = settings.LLM_TOP_K
    think = settings.LLM_THINK
    num_predict = settings.LLM_TOP_P
    use_traced = _use_traced_ollama(role)

    return _create_llm_instance(model, base_url, stream, temperature, num_ctx, top_p, top_k, think, num_predict, use_traced)