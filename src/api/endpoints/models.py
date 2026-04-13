import time
from fastapi import APIRouter
from src.api.schemas import ModelInfo, ModelsList

router = APIRouter()


@router.get("/models", response_model=ModelsList)
async def list_models():
    """Необходим для определения приложения как OpenAI-совместимую модель"""
    return ModelsList(
        data=[ModelInfo(id="WATA AI Workshop", created=int(time.time()), owned_by="workshop")]
    )