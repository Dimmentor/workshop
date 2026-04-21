import time
import uuid

from opentelemetry import trace
from src.api.schemas import ChatCompletion, ChatCompletionChoice, \
    ChatCompletionMessage, ChatCompletionUsage
from src.api.services.llm_queue import llm_slot
from src.api.services.utils import _build_thread_and_state
from src.config import settings
from src.infrastructure.observability.metrics import monitor_model_performance
from src.domain.openai import last_assistant_content


class ChatCompletionService:

    async def handle(self, body, workflow, *, chat_id_from_header=None) -> ChatCompletion:
        start_time = time.time()

        thread_id, initial_state = _build_thread_and_state(
            body, chat_id_from_header=chat_id_from_header
        )
        model_name = body.model or "graph"
        base_url = getattr(body, "base_url", None)

        span = trace.get_current_span()
        span_ctx = span.get_span_context() if span is not None else None
        if span_ctx and getattr(span_ctx, "is_valid", False):
            span.set_attribute("workshop.thread_id", thread_id)
            span.set_attribute("workshop.model", model_name)
            span.set_attribute("workshop.stream", False)
            span.set_attribute("workshop.messages.in_count", len(body.messages or []))

        async with llm_slot(model=model_name, base_url=base_url):
            result = await workflow.ainvoke(
                initial_state,
                config={
                    "configurable": {"thread_id": thread_id},
                    "recursion_limit": settings.RECURSION_LIMIT,
                },
            )

        monitor_model_performance(
            {**result, "task_type": "chat_completions", "start_time": start_time}
        )

        content = self._extract_content(result)

        if span_ctx and getattr(span_ctx, "is_valid", False):
            span.set_attribute("workshop.response.length", len(content or ""))

        return ChatCompletion(
            id=thread_id,
            created=int(time.time()),
            model=model_name,
            choices=[
                ChatCompletionChoice(
                    message=ChatCompletionMessage(content=content),
                    finish_reason="stop",
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
            ),
            thread_id=thread_id,
            conversation_id=thread_id,
        )

    def _extract_content(self, result: dict) -> str:
        messages = result.get("messages") or []
        final_report = result.get("final_report")
        clarification_needed = result.get("clarification_needed")
        confirmation_needed = result.get("confirmation_needed")

        if final_report:
            return final_report

        if clarification_needed:
            return f"[Уточнение] {clarification_needed}"

        if confirmation_needed:
            return f"[Подтверждение] {confirmation_needed}"

        return last_assistant_content(messages) or ""
