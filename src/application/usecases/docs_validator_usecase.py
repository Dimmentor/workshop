from __future__ import annotations
import logging
from typing import Any, Dict
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from src.application.usecases.base_usecase import BaseUseCase, BaseUseCaseConfig
from src.domain.documentation_validation import (
    DocumentationValidationReport,
    DocsValidationToolPayload,
    parse_validation_payload,
    skip_comment,
    extract_json_object,
    SyntaxValidationResult,
    CommentValidationResult,
)
from src.prompt import DOCS_VALIDATOR_STEP_PROMPTS, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_DOC_CHARS = 120_000


class DocsValidatorUseCase(BaseUseCase):
    """Пошаговая проверка: только LLM, вход — текст из чата."""

    def __init__(self, llm_factory: Any = None):
        super().__init__(
            llm_factory=llm_factory,
            config=BaseUseCaseConfig(
                model_name="validator",
                system_prompt_template="",
                is_iterative=True,
                max_iterations=6,
                enable_streaming=False,
            ),
        )

    async def _execute_validation(self, payload: DocsValidationToolPayload) -> Dict[str, Any]:
        body = payload.content
        if len(body) > MAX_DOC_CHARS:
            body = body[:MAX_DOC_CHARS] + "\n\n… [обрезано для проверки]"

        label = (payload.label or "inline").strip() or "inline"
        notes = (payload.notes or "").strip()

        llm = self._get_llm()

        # Шаг 1: Проверка синтаксиса
        syntax_result = await self._validate_step(
            llm=llm,
            system_prompt=DOCS_VALIDATOR_STEP_PROMPTS["syntax_system"],
            user_prompt=DOCS_VALIDATOR_STEP_PROMPTS["syntax"].format(
                label=label, notes=notes or "—", body=body
            ),
            result_model=SyntaxValidationResult,
            step_name="syntax"
        )

        if not syntax_result or not syntax_result.syntax_ok:
            # Если синтаксис неверный, возвращаем отчёт с ошибкой
            rep = DocumentationValidationReport(
                syntax=syntax_result.comment if syntax_result else "ошибка проверки",
                description=skip_comment(),
                architecture=skip_comment(),
                technologies=skip_comment(),
                instruction=skip_comment(),
                syntax_ok=syntax_result.syntax_ok if syntax_result else False,
                pipeline_completed=False,
            )
            return {"report": rep, "error": None}

        # Шаг 2: Проверка описания
        description_result = await self._validate_step(
            llm=llm,
            system_prompt=DOCS_VALIDATOR_STEP_PROMPTS["description_system"],
            user_prompt=DOCS_VALIDATOR_STEP_PROMPTS["description"].format(
                label=label, notes=notes or "—", body=body
            ),
            result_model=CommentValidationResult,
            step_name="description"
        )

        # Шаг 3: Проверка архитектуры
        architecture_result = await self._validate_step(
            llm=llm,
            system_prompt=DOCS_VALIDATOR_STEP_PROMPTS["architecture_system"],
            user_prompt=DOCS_VALIDATOR_STEP_PROMPTS["architecture"].format(
                label=label, notes=notes or "—", body=body
            ),
            result_model=CommentValidationResult,
            step_name="architecture"
        )

        # Шаг 4: Проверка технологий
        technologies_result = await self._validate_step(
            llm=llm,
            system_prompt=DOCS_VALIDATOR_STEP_PROMPTS["technologies_system"],
            user_prompt=DOCS_VALIDATOR_STEP_PROMPTS["technologies"].format(
                label=label, notes=notes or "—", body=body
            ),
            result_model=CommentValidationResult,
            step_name="technologies"
        )

        # Шаг 5: Проверка инструкции
        instruction_result = await self._validate_step(
            llm=llm,
            system_prompt=DOCS_VALIDATOR_STEP_PROMPTS["instruction_system"],
            user_prompt=DOCS_VALIDATOR_STEP_PROMPTS["instruction"].format(
                label=label, notes=notes or "—", body=body
            ),
            result_model=CommentValidationResult,
            step_name="instruction"
        )

        # Формируем итоговый отчёт
        report = DocumentationValidationReport(
            syntax=syntax_result.comment,
            description=description_result.comment if description_result else skip_comment(),
            architecture=architecture_result.comment if architecture_result else skip_comment(),
            technologies=technologies_result.comment if technologies_result else skip_comment(),
            instruction=instruction_result.comment if instruction_result else skip_comment(),
            syntax_ok=syntax_result.syntax_ok,
            pipeline_completed=True,
        )
        return {"report": report, "error": None}

    async def _validate_step(
        self,
        llm,
        system_prompt: str,
        user_prompt: str,
        result_model,
        step_name: str
    ) -> Any:
        """Выполняет один шаг валидации с вызовом LLM."""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            resp = await llm.ainvoke(messages)
            print(f"ШАГ: {resp}")
            text = resp.content if isinstance(resp, AIMessage) else str(resp)
            data = extract_json_object(text)
            return result_model.model_validate(data)
        except Exception as e:
            logger.warning("Docs validator step %s error: %s", step_name, e)
            return None

    async def run(self, state: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
        raw = state.get("_validate_work")
        parsed = parse_validation_payload(raw if isinstance(raw, str) else None)
        if parsed is None:
            return {
                "error": "Ожидается JSON в _validate_work с полем content (текст документа).",
                "report": None,
            }
        return await self._execute_validation(parsed)
