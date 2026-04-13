from __future__ import annotations

import asyncio
import html
import json
from typing import Any, AsyncGenerator, Dict, Optional, Tuple

from src.config import settings
from src.infrastructure.observability.metrics import monitor_model_performance

NODE_NAMES = frozenset({"prepare", "assistant", "executor", "coder", "validator", "god_node"})
_TOOL_OUTPUT_MAX_CHARS = 8000


def _emit_progress_enabled() -> bool:
    return bool(
        getattr(settings, "STREAM_PROGRESS_EVENTS", True)
    )


def _progress_html() -> bool:
    return bool(getattr(settings, "STREAM_PROGRESS_HTML", True))


def format_progress_fragment(*, summary: str, body: Optional[str] = None) -> str:
    """
    Сворачиваемый блок в delta.content. Многострочная разметка —
    иначе многие клиенты (markdown) показывают теги как сырой текст.
    Содержимое blockquote экранируется.
    """
    summary_clean = summary.strip()
    summary_esc = html.escape(summary_clean, quote=False)
    if _progress_html():
        block_src = (
            str(body).strip()
            if body is not None and str(body).strip()
            else summary_clean
        )
        block_esc = html.escape(block_src, quote=False)
        return (
            f"\n<details>\n"
            f"<summary>{summary_esc}</summary>\n"
            f"\n{block_esc}\n"
            f"</details>\n"
        )
    line = f"[{summary_clean}]"
    if body is not None and str(body).strip():
        return f"\n{line}\n{body}\n"
    return f"\n{line}\n"


def format_chunk(
    *,
    uid: str,
    created: int,
    model: str,
    content: str,
    role: Optional[str] = None,
    finish_reason: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> str:
    """Сформировать одну SSE-строку с chat.completion.chunk."""
    delta: dict = {}
    if role:
        delta["role"] = role
    if content:
        delta["content"] = content
    chunk = {
        "id": uid,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            }
        ],
    }
    if thread_id:
        chunk["thread_id"] = thread_id
    return "data: " + json.dumps(chunk, ensure_ascii=False) + "\n\n"


def ensure_role_chunk(
    *,
    uid: str,
    created: int,
    model_name: str,
    sent_role: bool,
    thread_id: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """Первый чанк role=assistant в соответствии с OpenAI протоколом."""
    if sent_role:
        return sent_role, None
    return True, format_chunk(
        uid=uid,
        created=created,
        model=model_name,
        content="",
        role="assistant",
        finish_reason=None,
        thread_id=thread_id,
    )


def _node_from_event(event: Dict[str, Any]) -> Optional[str]:
    meta = event.get("metadata")
    if isinstance(meta, dict):
        raw = meta.get("langgraph_node")
        if isinstance(raw, str) and raw:
            base = raw.split(":")[0] if ":" in raw else raw
            if base in NODE_NAMES:
                return base
    tags = event.get("tags")
    if isinstance(tags, (list, tuple)):
        for t in tags:
            if isinstance(t, str) and t in NODE_NAMES:
                return t
    name = event.get("name")
    if isinstance(name, str) and name in NODE_NAMES:
        return name
    return None


def _serialize_tool_output(output: Any) -> str:
    if output is None:
        return ""
    content = getattr(output, "content", None)
    if content is not None:
        text = content if isinstance(content, str) else str(content)
    elif isinstance(output, (dict, list)):
        try:
            text = json.dumps(output, ensure_ascii=False)
        except (TypeError, ValueError):
            text = str(output)
    else:
        text = str(output)
    if len(text) > _TOOL_OUTPUT_MAX_CHARS:
        return text[: _TOOL_OUTPUT_MAX_CHARS] + "\n…(truncated)"
    return text


async def stream_sse_events(
    *,
    workflow: Any,
    initial_state: Dict[str, Any],
    config: Dict[str, Any],
    uid: str,
    created: int,
    model_name: str,
    thread_id: str,
    start_time: float,
) -> AsyncGenerator[str, None]:
    """
    SSE: по мере выполнения графа — прогресс (узлы/инструменты), параллельно токены модели.
    """
    sent_role = False
    emit_progress = _emit_progress_enabled()

    async for event in workflow.astream_events(initial_state, config=config, version="v2"):
        kind = event.get("event") or ""
        data = event.get("data") or {}
        name = event.get("name") or data.get("name") or ""

        # --- Узлы графа (старт) ---
        if emit_progress and kind == "on_chain_start":
            node = _node_from_event(event)
            if node:
                msg = format_progress_fragment(summary=f"Узел · {node}")
                sent_role, role_chunk = ensure_role_chunk(
                    uid=uid,
                    created=created,
                    model_name=model_name,
                    sent_role=sent_role,
                    thread_id=thread_id,
                )
                if role_chunk:
                    yield role_chunk
                    await asyncio.sleep(0)
                yield format_chunk(
                    uid=uid,
                    created=created,
                    model=model_name,
                    content=msg,
                    role=None,
                    finish_reason=None,
                    thread_id=thread_id,
                )
                await asyncio.sleep(0)

        # --- Инструмент: старт ---
        if emit_progress and kind == "on_tool_start":
            tool_name = name or "tool"
            msg = format_progress_fragment(summary=f"Вызван инструмент · {tool_name}", body="Выполняется…")
            sent_role, role_chunk = ensure_role_chunk(
                uid=uid,
                created=created,
                model_name=model_name,
                sent_role=sent_role,
                thread_id=thread_id,
            )
            if role_chunk:
                yield role_chunk
                await asyncio.sleep(0)
            yield format_chunk(
                uid=uid,
                created=created,
                model=model_name,
                content=msg,
                role=None,
                finish_reason=None,
                thread_id=thread_id,
            )
            await asyncio.sleep(0)

        # --- Токены чата (основной ответ) ---
        if kind == "on_chat_model_stream":
            chunk = data.get("chunk")
            token = getattr(chunk, "content", None) if chunk is not None else None
            if token:
                token_text = token if isinstance(token, str) else str(token)
                if token_text:
                    sent_role, role_chunk = ensure_role_chunk(
                        uid=uid,
                        created=created,
                        model_name=model_name,
                        sent_role=sent_role,
                        thread_id=thread_id,
                    )
                    if role_chunk:
                        yield role_chunk
                        await asyncio.sleep(0)
                    yield format_chunk(
                        uid=uid,
                        created=created,
                        model=model_name,
                        content=token_text,
                        role=None,
                        finish_reason=None,
                        thread_id=thread_id,
                    )
                    await asyncio.sleep(0)

        # Некоторые связки Ollama/LC шлют on_llm_stream вместо on_chat_model_stream
        elif kind == "on_llm_stream":
            chunk = data.get("chunk")
            token = getattr(chunk, "text", None) or getattr(chunk, "content", None) if chunk is not None else None
            if token:
                token_text = token if isinstance(token, str) else str(token)
                if token_text:
                    sent_role, role_chunk = ensure_role_chunk(
                        uid=uid,
                        created=created,
                        model_name=model_name,
                        sent_role=sent_role,
                        thread_id=thread_id,
                    )
                    if role_chunk:
                        yield role_chunk
                        await asyncio.sleep(0)
                    yield format_chunk(
                        uid=uid,
                        created=created,
                        model=model_name,
                        content=token_text,
                        role=None,
                        finish_reason=None,
                        thread_id=thread_id,
                    )
                    await asyncio.sleep(0)

        # --- Инструмент: результат (виртуальные delegate_to_coder и MCP) ---
        elif kind == "on_tool_end":
            output = data.get("output")
            tool_name = name or "tool"

            control_output = output if isinstance(output, str) else str(output) if output else ""
            try:
                control_data = json.loads(control_output)
                if isinstance(control_data, dict) and "__control" in control_data:
                    control_type = control_data.get("__control")
                    if control_type == "clarification_needed":
                        question = control_data.get("question", "")
                        yield format_chunk(
                            uid=uid,
                            created=created,
                            model=model_name,
                            content=f"[Уточнение] {question}",
                            role="assistant",
                            finish_reason="stop",
                            thread_id=thread_id,
                        )
                        await asyncio.sleep(0)
                        continue
                    if control_type == "confirmation_needed":
                        message = control_data.get("message", "")
                        yield format_chunk(
                            uid=uid,
                            created=created,
                            model=model_name,
                            content=f"[Подтверждение] {message}",
                            role="assistant",
                            finish_reason="stop",
                            thread_id=thread_id,
                        )
                        await asyncio.sleep(0)
                        continue
                    if control_type == "final_report":
                        report = control_data.get("text", "")
                        yield format_chunk(
                            uid=uid,
                            created=created,
                            model=model_name,
                            content=report,
                            role="assistant",
                            finish_reason="stop",
                            thread_id=thread_id,
                        )
                        await asyncio.sleep(0)
                        continue
            except (json.JSONDecodeError, TypeError):
                pass

            if emit_progress:
                preview = _serialize_tool_output(output)
                body = preview if preview else "(пусто)"
                msg = format_progress_fragment(summary=f"Результат вызова инструмента · {tool_name}", body=body)
                sent_role, role_chunk = ensure_role_chunk(
                    uid=uid,
                    created=created,
                    model_name=model_name,
                    sent_role=sent_role,
                    thread_id=thread_id,
                )
                if role_chunk:
                    yield role_chunk
                    await asyncio.sleep(0)
                yield format_chunk(
                    uid=uid,
                    created=created,
                    model=model_name,
                    content=msg,
                    role=None,
                    finish_reason=None,
                    thread_id=thread_id,
                )
                await asyncio.sleep(0)

    sent_role, role_chunk = ensure_role_chunk(
        uid=uid, created=created, model_name=model_name, sent_role=sent_role, thread_id=thread_id
    )
    if role_chunk:
        yield role_chunk
        await asyncio.sleep(0)

    try:
        state = await workflow.aget_state(config)
        if state and state.values:
            state_values = state.values
            clarification_needed = state_values.get("clarification_needed")
            confirmation_needed = state_values.get("confirmation_needed")
            final_report = state_values.get("final_report")

            if clarification_needed:
                yield format_chunk(
                    uid=uid,
                    created=created,
                    model=model_name,
                    content=f"[Уточнение] {clarification_needed}",
                    role="assistant",
                    finish_reason="stop",
                    thread_id=thread_id,
                )
                await asyncio.sleep(0)
            elif confirmation_needed:
                yield format_chunk(
                    uid=uid,
                    created=created,
                    model=model_name,
                    content=f"[Подтверждение] {confirmation_needed}",
                    role="assistant",
                    finish_reason="stop",
                    thread_id=thread_id,
                )
                await asyncio.sleep(0)
            elif final_report:
                yield format_chunk(
                    uid=uid,
                    created=created,
                    model=model_name,
                    content=final_report,
                    role="assistant",
                    finish_reason="stop",
                    thread_id=thread_id,
                )
                await asyncio.sleep(0)

            monitor_model_performance(
                {**state.values, "task_type": "chat_completions_stream", "start_time": start_time}
            )
    # TO-DO: Добавить кастомную обработку исключений
    except (RuntimeError, ValueError, IOError):
        pass

    yield format_chunk(
        uid=uid, created=created, model=model_name, content="", role=None, finish_reason="stop", thread_id=thread_id
    )
    await asyncio.sleep(0)
    yield "data: [DONE]\n\n"
