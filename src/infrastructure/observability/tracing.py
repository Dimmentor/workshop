from dataclasses import dataclass
from typing import Optional
from opentelemetry.context import Context
from opentelemetry.trace import NonRecordingSpan
from opentelemetry import trace
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from openinference.instrumentation._capture import _current_capture_span_context
from phoenix.otel import register
from src.config import settings

_tracer_initialized = False


@dataclass(frozen=True)
class TracingSettings:
    enabled: bool
    endpoint: Optional[str]
    project_name: str
    auto_instrument: bool

    @staticmethod
    def from_env() -> "TracingSettings":
        endpoint = (settings.PHOENIX_COLLECTOR_ENDPOINT or "").strip() or None
        project_name = (settings.PHOENIX_PROJECT_NAME or "").strip() or "workshop"
        enabled = bool(endpoint)
        auto_instrument = bool(settings.PHOENIX_AUTO_INSTRUMENT)
        return TracingSettings(
            enabled=enabled,
            endpoint=endpoint,
            project_name=project_name,
            auto_instrument=auto_instrument,
        )


def setup_tracing(app=None) -> bool:
    """
    Инициализация OTel экспорта в Phoenix + авто-инструментация поддерживаемых библиотек.
    Возвращает True, если трейсинг включён.
    """
    global _tracer_initialized

    if _tracer_initialized:
        return True

    cfg = TracingSettings.from_env()
    if not cfg.enabled or not cfg.endpoint:
        return False

    """Phoenix создаёт TracerProvider + OTLP exporter. 
    auto_instrument включает OpenInference-инструментацию (LangChain и др.), если она установлена."""

    protocol = (settings.PHOENIX_OTLP_PROTOCOL or "").strip().lower() or None
    if protocol is None and cfg.endpoint.rstrip("/").endswith(":4317"):
        protocol = "grpc"

    register(
        endpoint=cfg.endpoint,
        project_name=cfg.project_name,
        auto_instrument=cfg.auto_instrument,
        protocol=protocol,
    )

    # HTTP client spans для MCP (aiohttp)
    try:
        AioHttpClientInstrumentor().instrument()
    except (ImportError, RuntimeError, ValueError):
        pass

    # Корреляция логов с trace/span id
    try:
        LoggingInstrumentor().instrument(set_logging_format=True)
    except (ImportError, RuntimeError, ValueError):
        pass

    # Root spans для входящих запросов FastAPI (если app передан)
    if app is not None:
        try:
            FastAPIInstrumentor.instrument_app(app)
        except (ImportError, RuntimeError, ValueError):
            pass

    _tracer_initialized = True
    return True


def get_tracer(name: str):
    return trace.get_tracer(name)


def get_openinference_parent_context_from_capture() -> Optional[Context]:
    """
    OpenInference создает span для цепочек/узлов, но (в целях безопасности) не прикрепляет
    к "текущему контексту" OpenTelemetry на время выполнения коллбэков.
    Этот вспомогательный метод позволяет получить последний захваченный SpanContext OpenInference и использовать
    его в качестве явного родительского элемента при запуске собственных span.
    """
    try:
        capture = _current_capture_span_context.get(None)
        if capture is None:
            return None

        span_contexts = list(capture.get_span_contexts())
        if not span_contexts:
            return None

        parent_span_context = span_contexts[-1]
        if hasattr(parent_span_context, "is_valid") and not parent_span_context.is_valid:
            return None

        parent_span = NonRecordingSpan(parent_span_context)
        return trace.set_span_in_context(parent_span)
    except (AttributeError, TypeError, ValueError):
        # Не валить приложение из-за ошибок tracing, в будущем заменить на кастомный обработчик
        return None