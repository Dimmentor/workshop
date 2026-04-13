import time
import uuid

from fastapi.responses import StreamingResponse
from opentelemetry import trace
from src.api.services.utils import _build_thread_and_state
from src.api.services.streaming import stream_sse_events
from src.config import settings


class ChatStreamService:

    def handle(self, body, workflow, *, chat_id_from_header=None):

        start_time = time.time()
        thread_id, initial_state = _build_thread_and_state(
            body, chat_id_from_header=chat_id_from_header
        )

        uid = f"chatcmpl-{uuid.uuid4().hex}"
        created = int(time.time())
        model_name = body.model or "graph"

        span = trace.get_current_span()
        span_ctx = span.get_span_context() if span is not None else None
        if span_ctx and getattr(span_ctx, "is_valid", False):
            span.set_attribute("workshop.thread_id", thread_id)
            span.set_attribute("workshop.model", model_name)
            span.set_attribute("workshop.stream", True)
            span.set_attribute("workshop.messages.in_count", len(body.messages or []))

        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": settings.RECURSION_LIMIT,
        }

        return StreamingResponse(
            stream_sse_events(
                workflow=workflow,
                initial_state=initial_state,
                config=config,
                uid=uid,
                created=created,
                model_name=model_name,
                thread_id=thread_id,
                start_time=start_time,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )