"""Модели проверки документации (README и аналоги) в формате Markdown / AsciiDoc."""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from pydantic import BaseModel, Field


class DocsValidationToolPayload(BaseModel):
    """Вход: текст документа из сообщения пользователя."""

    content: str = Field(..., min_length=1, description="Содержимое файла / вставка в чат")
    notes: str = Field(default="", description="Краткий контекст")
    label: str = Field(default="inline", description="Подпись для промптов (например имя файла)")


class SyntaxValidationResult(BaseModel):
    """Результат проверки синтаксиса/формата."""
    syntax_ok: bool = Field(..., description="Корректен ли формат .md/.adoc")
    comment: str = Field(..., description="Комментарий о формате")


class CommentValidationResult(BaseModel):
    """Результат проверки с одним комментарием (для остальных полей)."""
    comment: str = Field(..., description="Комментарий о проверяемом аспекте")

class DocumentationValidationReport(BaseModel):
    """
    Результат пошаговой проверки. Поля — краткие комментарии по каждому критерию.
    Если синтаксис/формат не подошёл, дальнейшие шаги помечаются как «не проверено».
    """

    syntax: str = Field(..., description="Формат .md / .adoc и корректность разметки")
    description: str = Field(..., description="Общее описание / назначение проекта")
    architecture: str = Field(..., description="Структура проекта / архитектура")
    technologies: str = Field(..., description="Используемые технологии")
    instruction: str = Field(..., description="Инструкция по запуску")
    syntax_ok: bool = Field(default=False, description="Можно ли доверять последующим пунктам")
    pipeline_completed: bool = Field(default=False, description="Все шаги пайплайна выполнены")


def parse_validation_payload(raw: Optional[str]) -> Optional[DocsValidationToolPayload]:
    """
    Разобрать содержимое _validate_work: JSON с doc_path или legacy plain text (только notes).
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        data = json.loads(s)
        if isinstance(data, dict) and data.get("doc_path"):
            return DocsValidationToolPayload.model_validate(data)
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return None


def skip_comment(reason: str = "не проверено: предыдущий шаг не пройден") -> str:
    return reason


_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def extract_json_object(text: str) -> dict[str, Any]:
    """Вытащить JSON-объект из ответа модели (сырой или в fence)."""
    t = (text or "").strip()
    if not t:
        raise ValueError("empty model response")
    m = _JSON_FENCE.search(t)
    if m:
        t = m.group(1).strip()
    try:
        data = json.loads(t)
    except json.JSONDecodeError:
        # последняя попытка: первые { ... }
        i, j = t.find("{"), t.rfind("}")
        if i >= 0 and j > i:
            data = json.loads(t[i : j + 1])
        else:
            raise
    if not isinstance(data, dict):
        raise ValueError("expected JSON object")
    return data
