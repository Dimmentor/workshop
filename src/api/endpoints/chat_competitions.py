from fastapi import APIRouter, Depends, Request
from src.api.depends import get_workflow, get_chat_completion_service, get_chat_stream_service
from src.api.services.request_context import get_stable_chat_id_from_request
from src.api.schemas import ChatCompletion, ChatCompletionRequest
from src.api.services.chat_completion_service import ChatCompletionService
from src.api.services.stream_service import ChatStreamService

router = APIRouter()


@router.post("/chat/completions", response_model=ChatCompletion)
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest,
    workflow=Depends(get_workflow),
    chat_service: ChatCompletionService = Depends(get_chat_completion_service),
    stream_service: ChatStreamService = Depends(get_chat_stream_service),
):
    chat_hdr = await get_stable_chat_id_from_request(request)
    if body.stream:
        return stream_service.handle(body, workflow, chat_id_from_header=chat_hdr)

    return await chat_service.handle(body, workflow, chat_id_from_header=chat_hdr)