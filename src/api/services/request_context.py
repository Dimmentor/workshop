from __future__ import annotations
import logging
import json
from typing import Mapping, Optional
from starlette.requests import Request


logger = logging.getLogger(__name__)

_STABLE_CHAT_ID_HEADERS: tuple[str, ...] = (
    "x-openwebui-chat-id",
    "x-chat-id",
)


def stable_chat_id_from_headers(headers: Mapping) -> Optional[str]:
    """Извлечь стабильный chat id из заголовков (регистронезависимо для обычных dict)."""
    try:
        lowered = {str(k).lower(): v for k, v in headers.items()}
    except Exception:
        return None
    for name in _STABLE_CHAT_ID_HEADERS:
        raw = lowered.get(name.lower())
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    return None


async def get_stable_chat_id_from_request(request: Request) -> Optional[str]:
    """Стабильный идентификатор чата из входящего запроса, если есть."""
    # Сначала проверяем заголовки (для последующих сообщений)
    chat_id = stable_chat_id_from_headers(request.headers)
    if chat_id:
        return chat_id

    # Для первого сообщения проверяем тело запроса
    try:
        body = None
        if hasattr(request, 'json'):
            logger.debug(f"request.json exists: {type(request.json)}")
            if callable(request.json):
                body = await request.json()
                logger.debug(f"Called request.json(): {body}")
            else:
                body = request.json
                logger.debug(f"Used request.json directly: {body}")
        elif hasattr(request, 'body'):
            body_text = request.body
            logger.debug(f"Raw body: {body_text}")
            if isinstance(body_text, (str, bytes)):
                body = json.loads(body_text if isinstance(body_text, str) else body_text.decode())
                logger.debug(f"Parsed body from text: {body}")

        if isinstance(body, dict):
            chat_id = body.get('chat_id') or body.get('thread_id') or body.get('conversation_id')
            logger.debug(f"Extracted chat_id: {chat_id}")
            return chat_id
    # Заменить на кастомное исключение
    except Exception as e:
        logger.error(f"Failed to parse chat_id from request body: {e}")
        pass

    return None
