import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
from opentelemetry import trace

from src.api.endpoints.chat_competitions import router as chat_router
from src.api.endpoints.models import router as models_router
from src.api.endpoints.metrics import router as metrics_router
from src.composition import build_components
from src.domain.exceptions import OrchestratorError
from src.infrastructure.observability.tracing import setup_tracing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_tracing(app)
    components = build_components()
    app.state.workflow = components.workflow
    app.state.mcp_client = components.mcp_client
    yield
    try:
        await app.state.mcp_client.aclose()
    except OrchestratorError:
        pass


app = FastAPI(
    title="Orchestrator service",
    description="Оркестратор ИИ агентов",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def add_trace_headers(request: Request, call_next):
    response: Response = await call_next(request)
    span = trace.get_current_span()
    span_ctx = span.get_span_context() if span is not None else None
    if span_ctx and getattr(span_ctx, "is_valid", False):
        response.headers["X-Trace-Id"] = format(span_ctx.trace_id, "032x")
        response.headers["X-Span-Id"] = format(span_ctx.span_id, "016x")
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/v1")
app.include_router(models_router, prefix="/v1")
app.include_router(metrics_router)
