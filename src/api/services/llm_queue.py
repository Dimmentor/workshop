from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Optional, Tuple

from fastapi import HTTPException

from src.config import settings

# Keyed semaphores so different models (or different base_url) can be isolated.
_SEMAPHORES: Dict[Tuple[str, str], asyncio.Semaphore] = {}
_LOCK = asyncio.Lock()


def _queue_key(*, model: Optional[str], base_url: Optional[str]) -> Tuple[str, str]:
    return ((model or settings.LLM_MODEL), (base_url or settings.OLLAMA_BASE_URL))


async def _get_semaphore(key: Tuple[str, str]) -> asyncio.Semaphore:
    async with _LOCK:
        sem = _SEMAPHORES.get(key)
        if sem is None:
            max_conc = int(getattr(settings, "LLM_MAX_CONCURRENT_REQUESTS", 1) or 1)
            if max_conc < 1:
                max_conc = 1
            sem = asyncio.Semaphore(max_conc)
            _SEMAPHORES[key] = sem
        return sem


@asynccontextmanager
async def llm_slot(*, model: Optional[str] = None, base_url: Optional[str] = None) -> AsyncIterator[None]:
    """
    Global backpressure for LLM calls.

    - If model is "busy" (concurrency limit reached), requests WAIT in queue.
    - Optional timeout via settings.LLM_QUEUE_TIMEOUT_SECONDS: after that -> 429.
    """
    key = _queue_key(model=model, base_url=base_url)
    sem = await _get_semaphore(key)

    timeout = getattr(settings, "LLM_QUEUE_TIMEOUT_SECONDS", None)
    try:
        if timeout is None:
            await sem.acquire()
        else:
            t = float(timeout)
            if t <= 0:
                await sem.acquire()
            else:
                await asyncio.wait_for(sem.acquire(), timeout=t)
    except asyncio.TimeoutError as e:
        # "Too Many Requests" is the closest semantics: queued too long.
        raise HTTPException(status_code=429, detail="LLM is busy, request queued too long") from e

    try:
        yield
    finally:
        sem.release()

