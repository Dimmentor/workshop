from __future__ import annotations
import json
import logging
from typing import Dict, Optional, Any
from langchain_core.messages import ToolMessage, AIMessage, SystemMessage, HumanMessage
from src.application.usecases.docs_validator_usecase import DocsValidatorUseCase
from src.config import settings
from src.domain.documentation_validation import DocumentationValidationReport, DocsValidationToolPayload
from src.graph.nodes.base_node import BaseNode
from src.infrastructure.llm.factory import get_llm
from src.prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class DocsValidatorNode(BaseNode):
    """Проверка README/документации: чтение файла через MCP и пошаговый LLM-пайплайн."""

    def __init__(self, llm_factory: Any = None):
        super().__init__(mcp_client=None, llm_factory=llm_factory, tools_resolver=None)
        self._usecase = DocsValidatorUseCase(llm_factory=llm_factory)

    async def _execute_logic(self, state: Dict[str, Any], span) -> Dict[str, object]:
        # Проверяем, есть ли задача валидации документации
        raw = state.get("_validate_work")
        tool_call_id = state.get("_validate_tool_call_id") or "docs_validator"

        if raw:
            # Если есть _validate_work, выполняем валидацию документации
            result = await self._usecase.run(state)
            err = result.get("error")
            report: Optional[DocumentationValidationReport] = result.get("report")

            if err:
                text = f"Проверка документации: {err}"
                out_report = None
            elif report:
                text = _human_summary(report) + "\n\n--- JSON ---\n" + json.dumps(
                    report.model_dump(), ensure_ascii=False, indent=2
                )
                out_report = json.dumps(report.model_dump(), ensure_ascii=False)
            else:
                text = "Проверка документации: пустой результат."
                out_report = None

            updates: Dict[str, object] = {
                "messages": [AIMessage(content=text)],
                "_validate_work": None,
                "_validate_tool_call_id": None,
            }
            if out_report is not None:
                updates["docs_validation_report"] = out_report
            return updates

        # Если нет _validate_work, проверяем сообщения на наличие документации для валидации
        messages = list(state.get("messages") or [])
        if not messages:
            return {}

        last_message = messages[-1] if messages else None
        if isinstance(last_message, HumanMessage) and last_message.content:
            doc_text = str(last_message.content)

            # Выполняем валидацию документации
            payload = DocsValidationToolPayload(
                content=doc_text,
                notes="Валидация из сообщения чата",
                label="inline"
            )

            result = await self._usecase._execute_validation(payload)
            err = result.get("error")
            report: Optional[DocumentationValidationReport] = result.get("report")

            if err:
                text = f"Проверка документации: {err}"
                out_report = None
            elif report:
                text = _human_summary(report) + "\n\n--- JSON ---\n" + json.dumps(
                    report.model_dump(), ensure_ascii=False, indent=2
                )
                out_report = json.dumps(report.model_dump(), ensure_ascii=False)
            else:
                text = "Проверка документации: пустой результат."
                out_report = None

            updates: Dict[str, object] = {
                "messages": [AIMessage(content=text)],
            }
            if out_report is not None:
                updates["docs_validation_report"] = out_report
            return updates



def _human_summary(r: DocumentationValidationReport) -> str:
    lines = [
        "### Результат проверки документации",
        "",
        f"**Синтаксис / формат:** {r.syntax}",
        f"**Общее описание:** {r.description}",
        f"**Архитектура / структура:** {r.architecture}",
        f"**Технологии:** {r.technologies}",
        f"**Запуск:** {r.instruction}",
        "",
        f"Синтаксис приемлем для дальнейших проверок: **{'да' if r.syntax_ok else 'нет'}**.",
    ]
    return "\n".join(lines)
