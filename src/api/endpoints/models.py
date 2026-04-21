import time
from fastapi import APIRouter
from src.api.schemas import ModelInfo, ModelsList
from src.config import settings

router = APIRouter()


@router.get("/models", response_model=ModelsList)
async def list_models():
    """Список моделей для OpenAI/OpenWebUI совместимости.

    Важно: OpenWebUI берёт `id` из этого списка и затем отправляет его как `model`
    в `/v1/chat/completions`. Поэтому `id` должен быть реальным именем модели Ollama.
    """
    return ModelsList(
        data=[
            ModelInfo(id=settings.LLM_MODEL, created=int(time.time()), owned_by="workshop"),
        ]
    )