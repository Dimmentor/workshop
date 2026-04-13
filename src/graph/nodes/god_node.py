import logging
from typing import Dict
from src.graph.state import AgentState
from src.graph.nodes.base_node import BaseNode
from src.application.usecases.god_usecase import GodUseCase

logger = logging.getLogger(__name__)


class GodNode(BaseNode):
    """Single node that processes messages (similar to AssistantNode pattern)."""

    def __init__(self, mcp_client=None, llm_factory=None, tools_resolver=None):
        super().__init__(mcp_client, llm_factory, tools_resolver)
        self._usecase = GodUseCase(tools_resolver=self._tools, llm_factory=self._llm_factory)

    async def _execute_logic(self, state: AgentState, span) -> Dict[str, object]:
        """Execute single-node logic."""
        stream = bool(state.get("_stream", False))
        span.set_attribute("request.stream", stream)

        result = await self._usecase.run(state, stream=stream)

        response = result.get("response")

        # Extend messages for unified handling
        new_messages = []
        if response:
            new_messages.append(response)

        return {
            "messages": new_messages  # Graph will add to existing messages
        }