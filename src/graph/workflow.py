from __future__ import annotations
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict
from src.infrastructure.observability.tracing import get_tracer
from openinference.instrumentation import capture_span_context


tracer = get_tracer(__name__)


@dataclass(frozen=True)
class AgentWorkflow:
    """
    Фасад над скомпилированным LangGraph workflow
    Нужен, чтобы:
    - не держать вложенные классы в factory-функциях
    - централизованно оборачивать выполнение в tracing spans
    - позволить типизировать публичный контракт для API слоя
    """
    _workflow: Any

    async def ainvoke(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Параметр capture_span_context необходим, поскольку OpenInference+LangChain
        отслеживает диапазоны для узлов/цепочек, не всегда прикрепляя их
        к текущему контексту OpenTelemetry для асинхронных коллбэков."""
        with capture_span_context():
            with tracer.start_as_current_span("graph.execution"):
                return await self._workflow.ainvoke(*args, **kwargs)

    async def astream_events(self, *args: Any, **kwargs: Any) -> AsyncGenerator[Dict[str, Any], None]:
        with capture_span_context():
            with tracer.start_as_current_span("graph.stream"):
                async for event in self._workflow.astream_events(*args, **kwargs):
                    yield event

    async def aget_state(self, *args: Any, **kwargs: Any) -> Any:
        return await self._workflow.aget_state(*args, **kwargs)

