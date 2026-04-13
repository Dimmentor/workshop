from fastapi import APIRouter
from src.infrastructure.observability.metrics import get_recent_metrics

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/metrics")
def metrics():
    return {"metrics": get_recent_metrics()}
