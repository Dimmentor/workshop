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
    return thread_id, state
