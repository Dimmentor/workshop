from __future__ import annotations
from typing import Any, List, Sequence
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage


def openai_messages_to_lc(openai_messages: Sequence[Any]) -> List[BaseMessage]:
    """
    Преобразует OpenAI-совместимые сообщения (role/content) во внутренние LangChain messages.
    Не зависит от конкретных схем (Pydantic), поэтому принимает `Any` с полями `role` и `content`.
    """
    out: List[BaseMessage] = []
    for m in openai_messages:
        if isinstance(m, dict):
            role = m.get("role")
            content = m.get("content")
        else:
            role = getattr(m, "role", None)
            content = getattr(m, "content", None)
        if role == "system":
            out.append(SystemMessage(content=content or ""))
        elif role == "user":
            out.append(HumanMessage(content=content or ""))
        elif role == "assistant":
            out.append(AIMessage(content=content or ""))
    return out


def last_assistant_content(messages: Sequence[BaseMessage]) -> str:
    """Возвращает последнее содержимое assistant сообщения из списка."""
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], AIMessage) and messages[i].content:
            return messages[i].content if isinstance(messages[i].content, str) else str(messages[i].content)
    return ""

