from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from langchain_core.messages import BaseMessage

from src.domain.state_keys import CONTROL_KEYS_TO_RESET, PRESERVED_STATE_KEYS, STATE_KEY_SESSION_ID

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConversationIds:
    """
    Идентификаторы диалога для LangGraph checkpointing.
    `thread_id` — ключ состояния (чекпоинта). Он должен быть стабильным между запросами одного диалога.
    `conversation_id` — alias для внешнего API (удобнее семантически).
    """

    thread_id: str
    conversation_id: str


def new_conversation_id() -> str:
    return uuid.uuid4().hex


def resolve_conversation_ids(
    *,
    thread_id: Optional[str],
    conversation_id: Optional[str],
    chat_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> ConversationIds:
    """
    — Если клиент предоставляет какой-либо идентификатор (`thread_id`/`conversation_id`/`chat_id`/`session_id`) — используем его (нормализованный).
    — Если идентификатор не предоставлен — начинаем НОВЫЙ диалог с использованием идентификатора.
    """
    cid = (conversation_id or "").strip()
    tid = (thread_id or "").strip()
    chid = (chat_id or "").strip()
    sid = (session_id or "").strip()

    resolved = tid or cid or chid or sid or new_conversation_id()
    logger.debug(
        "RESOLVE: tid='%s', cid='%s', chat_id='%s', session_id='%s' -> resolved='%s'",
        tid,
        cid,
        chid,
        sid,
        resolved,
    )
    return ConversationIds(thread_id=resolved, conversation_id=resolved)


def infer_branch_path_from_openai_messages(messages: Sequence[Any]) -> Optional[str]:
    """
    Если клиент не прислал стабильный thread_id, кэш пуст, но в истории есть результат clone_branch
    или текст с `/sandbox/<workspace>`, восстанавливаем имя workspace.
    """
    import json
    import re

    from src.application.services.branch_path_service import BranchPathService

    if not messages:
        return None

    for m in reversed(messages):
        content = getattr(m, "content", None)
        if content is None:
            continue
        if isinstance(content, (dict, list)):
            text = json.dumps(content, ensure_ascii=False)
        else:
            text = str(content)
        text = text.strip()
        if not text or len(text) > 400_000:
            continue

        try:
            data = json.loads(text)
        except (json.JSONDecodeError, TypeError, ValueError):
            data = None
        if isinstance(data, dict):
            extracted = BranchPathService.extract_from_tool_result(data)
            if extracted:
                return extracted

        mo = re.search(r"/sandbox/([a-zA-Z0-9._-]+)", text)
        if mo:
            return mo.group(1)

    return None


def last_user_message(messages: Sequence[Any]) -> Optional[Any]:
    for m in reversed(messages or []):
        role = getattr(m, "role", None)
        content = getattr(m, "content", None)
        if role == "user" and isinstance(content, str) and content.strip():
            return m
    return None


def build_initial_state(
    *,
    openai_messages: Sequence[Any],
    has_explicit_conversation_id: bool,
    to_lc_messages: callable,
    thread_id: Optional[str] = None,
    client_branch_path: Optional[str] = None,
    client_context_branch_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Build initial state for the graph with branch_path restoration."""
    lc_messages: List[BaseMessage] = []
    if openai_messages:
        # Передаем все сообщения для сохранения ВСЕГО контекста. TO-DO: придумать оптимальную политику вытеснения.
        lc_messages = to_lc_messages(openai_messages)

    state: Dict[str, Any] = {"messages": lc_messages}

    if thread_id:
        state[STATE_KEY_SESSION_ID] = thread_id

    # Меняем branch_path, если нету в checkpointer
    if not state.get("branch_path"):
        # Задать из сообщений пользователя
        hint = (client_branch_path or "").strip() or (client_context_branch_path or "").strip()
        if hint:
            state["branch_path"] = hint
            logger.info("Applied client branch_path hint '%s' for thread_id '%s'", hint, thread_id)
        else:
            inferred = infer_branch_path_from_openai_messages(openai_messages)
            if inferred:
                state["branch_path"] = inferred
                logger.info("Inferred branch_path '%s' from messages for thread_id '%s'", inferred, thread_id)

    # Сбросить временные флаги
    if lc_messages:
        for k in CONTROL_KEYS_TO_RESET:
            state[k] = None
    
    return state

