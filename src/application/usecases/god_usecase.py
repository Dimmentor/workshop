import logging
from typing import Any, Dict, List
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.tools import BaseTool
from src.prompt import SYSTEM_PROMPT
from src.application.usecases.base_usecase import BaseUseCase, BaseUseCaseConfig
from src.config import settings
from src.infrastructure.llm.factory import get_llm
from src.graph.state import AgentState

logger = logging.getLogger(__name__)


class GodUseCase(BaseUseCase):
    def __init__(self, tools_resolver=None, llm_factory=None):
        config = BaseUseCaseConfig(
            model_name="default",
            system_prompt_template="",
        )
        super().__init__(tools_resolver=tools_resolver, llm_factory=llm_factory, config=config)

    def _get_tools(self, state: AgentState) -> List[BaseTool]:
        """В оркестраторе возвращает список доступных инструментов"""
        return []

    def _build_system_prompt(self, state: AgentState, tools: List[BaseTool]) -> str:
        """Получить системный промпт"""
        return SYSTEM_PROMPT

    async def run(self, state: AgentState, *, stream: bool = False) -> Dict[str, Any]:
        messages = list(state.get("messages") or [])
        if not messages:
            return {}

        llm_overrides = state.get("_llm") if isinstance(state, dict) else None
        # If request didn't specify model explicitly, fall back to env settings.
        model_override = None
        if isinstance(llm_overrides, dict):
            model_override = llm_overrides.get("model")
            # Defensive: treat empty/"graph" as not specified
            if isinstance(model_override, str):
                mo = model_override.strip()
                model_override = mo if mo and mo.lower() != "graph" else None
        llm = get_llm(
            "default",
            model=(model_override or settings.LLM_MODEL),
            overrides=llm_overrides if isinstance(llm_overrides, dict) else None,
        )

        # System prompt selection:
        # - If client provided any SystemMessage in `messages`, we do NOT prepend internal SYSTEM_PROMPT
        #   to avoid "double system" instructions.
        # - Otherwise we prepend internal SYSTEM_PROMPT.
        has_client_system = any(isinstance(m, SystemMessage) and (m.content or "").strip() for m in messages)
        if has_client_system:
            prompt = messages
        else:
            system = self._build_system_prompt(state, [])
            prompt = [SystemMessage(content=system)] + messages

        invoke_kwargs: Dict[str, Any] = {}
        if isinstance(llm_overrides, dict):
            # Prefer raw Ollama options passthrough if provided
            options = llm_overrides.get("options")
            if isinstance(options, dict):
                invoke_kwargs["options"] = options
            else:
                built_options: Dict[str, Any] = {}
                # Map OpenAI-ish max_tokens to Ollama num_predict if user didn't set it directly
                max_tokens = llm_overrides.get("max_tokens")
                if llm_overrides.get("num_predict") is None and isinstance(max_tokens, int):
                    built_options["num_predict"] = max_tokens

                for k in (
                    "temperature",
                    "top_p",
                    "top_k",
                    "num_ctx",
                    "num_gpu",
                    "num_thread",
                    "num_predict",
                    "repeat_last_n",
                    "repeat_penalty",
                    "seed",
                    "stop",
                    "tfs_z",
                    "mirostat",
                    "mirostat_eta",
                    "mirostat_tau",
                ):
                    v = llm_overrides.get(k)
                    if v is not None:
                        built_options[k] = v

                if built_options:
                    invoke_kwargs["options"] = built_options

            # Invocation-level params
            for k in ("reasoning", "format", "keep_alive"):
                v = llm_overrides.get(k)
                if v is not None:
                    invoke_kwargs[k] = v

        # Note: `stream` here is about API response streaming, not Ollama stream mode.
        try:
            logger.info(
                "LLM invoke: model=%s base_url=%s stream=%s",
                getattr(llm, "model", None),
                getattr(llm, "base_url", None),
                stream,
            )
        except Exception:
            pass
        response = await llm.ainvoke(prompt, **invoke_kwargs)

        if not isinstance(response, AIMessage):
            response = AIMessage(content=str(response) if response else "")

        return {
            "messages": [response],
            "response": response,
        }