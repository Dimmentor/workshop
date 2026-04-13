from functools import lru_cache
from fastapi import Request
from src.api.services.chat_completion_service import ChatCompletionService
from src.api.services.stream_service import ChatStreamService


def get_workflow(request: Request):
    return request.app.state.workflow


def get_mcp_client(request: Request):
    return request.app.state.mcp_client

@lru_cache
def get_chat_completion_service() -> ChatCompletionService:
    return ChatCompletionService()

@lru_cache
def get_chat_stream_service() -> ChatStreamService:
    return ChatStreamService()
