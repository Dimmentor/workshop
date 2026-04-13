import logging
import time
from collections import deque
from typing import Any, Dict, List

from src.config import settings

logger = logging.getLogger(__name__)

_METRICS_BUFFER: deque = deque(maxlen=int(getattr(settings, "METRICS_BUFFER_SIZE", 500) or 500))  # Последние N записей для GET /monitoring/metrics


def log_metrics(metrics: Dict[str, Any]) -> None:
    logger.info("Метрики: %s", metrics)


def get_recent_metrics() -> List[Dict[str, Any]]:
    return list(_METRICS_BUFFER)


def monitor_model_performance(state: Dict[str, Any]) -> Dict[str, Any]:
    metrics = {
        "classification_confidence": state.get("classification_confidence", 0),
        "response_time": time.time() - state.get("start_time", time.time()),
        "model_used": state.get("task_type", "unknown"),
        "success": bool(state.get("final_report") or state.get("final_response") or state.get("last_success_step")),
    }
    log_metrics(metrics)
    _METRICS_BUFFER.append(metrics)
    return state
