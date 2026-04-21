import logging
from typing import Any, Dict, Optional, Tuple

from src.api.schemas import ChatCompletionRequest
from src.domain.conversation import build_initial_state, resolve_conversation_ids
from src.domain.openai import openai_messages_to_lc
from src.api.services.streaming import stream_sse_events as _stream_sse_events

__all__ = [
    "_build_thread_and_state",
    "_stream_sse_events",
]


def _build_thread_and_state(
    body: ChatCompletionRequest,
    *,
    chat_id_from_header: Optional[str] = None,
) -> Tuple[str, Dict[str, Any]]:
    chat_from_body = (getattr(body, "chat_id", None) or "").strip()
    chat_merged = chat_from_body or (chat_id_from_header or "").strip() or None

    ids = resolve_conversation_ids(
        thread_id=getattr(body, "thread_id", None),
        conversation_id=getattr(body, "conversation_id", None),
        chat_id=chat_merged,
        session_id=getattr(body, "session_id", None),
    )
    thread_id = ids.thread_id

    logging.getLogger(__name__).debug(
        "Thread id=%s, stream=%s, messages=%d",
        thread_id,
        bool(body.stream),
        len(body.messages or []),
    )

    has_explicit_id = bool(
        (getattr(body, "thread_id", None) or "").strip()
        or (getattr(body, "conversation_id", None) or "").strip()
        or (getattr(body, "chat_id", None) or "").strip()
        or (getattr(body, "session_id", None) or "").strip()
        or (chat_id_from_header or "").strip()
    )
    ctx = getattr(body, "context", None)
    ctx_bp = None
    if isinstance(ctx, dict):
        raw = ctx.get("branch_path")
        if isinstance(raw, str) and raw.strip():
            ctx_bp = raw.strip()
    client_bp = getattr(body, "branch_path", None)
    client_bp = client_bp.strip() if isinstance(client_bp, str) and client_bp.strip() else None

    state = build_initial_state(
        openai_messages=body.messages or [],
        has_explicit_conversation_id=has_explicit_id,
        to_lc_messages=openai_messages_to_lc,
        thread_id=thread_id,
        client_branch_path=client_bp,
        client_context_branch_path=ctx_bp,
    )
    # API-level hint: позволяет узлам выбирать streaming вызовы LLM.
    state["_stream"] = bool(getattr(body, "stream", False))

    # LLM override params (per-request). All fields are optional; None means "use default".
    # We keep them in state so graph nodes/usecases can access them.
    raw_model = getattr(body, "model", None)
    if isinstance(raw_model, str):
        raw_model = raw_model.strip()
    # "graph" is a legacy placeholder used by some clients; treat it as "not specified"
    model_override = None
    if isinstance(raw_model, str) and raw_model and raw_model.lower() != "graph":
        model_override = raw_model

    state["_llm"] = {
        "model": model_override,
        "base_url": getattr(body, "base_url", None),
        "reasoning": getattr(body, "reasoning", None),
        "validate_model_on_init": getattr(body, "validate_model_on_init", None),
        "format": getattr(body, "format", None),
        "keep_alive": getattr(body, "keep_alive", None),
        "client_kwargs": getattr(body, "client_kwargs", None),
        "async_client_kwargs": getattr(body, "async_client_kwargs", None),
        "sync_client_kwargs": getattr(body, "sync_client_kwargs", None),
        "options": getattr(body, "options", None),
        # option-like fields (used to build options if body.options is not set)
        "temperature": getattr(body, "temperature", None),
        "top_p": getattr(body, "top_p", None),
        "top_k": getattr(body, "top_k", None),
        "num_ctx": getattr(body, "num_ctx", None),
        "num_gpu": getattr(body, "num_gpu", None),
        "num_thread": getattr(body, "num_thread", None),
        "num_predict": getattr(body, "num_predict", None),
        "repeat_last_n": getattr(body, "repeat_last_n", None),
        "repeat_penalty": getattr(body, "repeat_penalty", None),
        "seed": getattr(body, "seed", None),
        "stop": getattr(body, "stop", None),
        "tfs_z": getattr(body, "tfs_z", None),
        "mirostat": getattr(body, "mirostat", None),
        "mirostat_eta": getattr(body, "mirostat_eta", None),
        "mirostat_tau": getattr(body, "mirostat_tau", None),
        # OpenAI compatibility
        "max_tokens": getattr(body, "max_tokens", None),
    }
    return thread_id, state
