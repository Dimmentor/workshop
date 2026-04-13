import logging
from typing import Dict, Optional
from src.graph.state import AgentState
from src.application.tooling.tools_resolver import ToolsResolver
from src.infrastructure.observability.tracing import get_tracer, get_openinference_parent_context_from_capture

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


class BaseNode:
    """Базовый класс для узлов с зашитым трейсингом"""

    def __init__(
            self,
            mcp_client=None,
            llm_factory=None,
            tools_resolver: Optional[ToolsResolver] = None,
    ):
        self._mcp_client = mcp_client
        self._llm_factory = llm_factory
        self._tools = tools_resolver or ToolsResolver()

    async def __call__(self, state: AgentState) -> Dict[str, object]:
        """Execute node logic with tracing."""
        with tracer.start_as_current_span(
                f"node.{self.__class__.__name__}",
                context=get_openinference_parent_context_from_capture(),
        ) as span:
            return await self._execute_logic(state, span)

    async def _execute_logic(self, state: AgentState, span) -> Dict[str, object]:
        """Override in subclasses to implement node-specific logic."""
        raise NotImplementedError