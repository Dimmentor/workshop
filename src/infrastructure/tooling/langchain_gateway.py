from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional
from langchain_core.tools import BaseTool
from src.application.tooling.gateway import ToolGatewayProtocol
from src.application.tooling.tools_resolver import ToolsResolver
from src.domain.exceptions import ToolExecutionError
from src.graph.tools import get_tool_to_server_map


@dataclass
class LangChainToolGateway(ToolGatewayProtocol):
    """
    Адаптер: application-layer работает с портом ToolGatewayProtocol,
    а реализация под капотом использует LangChain tools.
    """
    resolver: ToolsResolver

    def tool_to_server(self, mcp_servers_info: Mapping[str, Any]) -> Dict[str, str]:
        return get_tool_to_server_map(dict(mcp_servers_info or {}))

    def _get_tool(self, tool_name: str, mcp_servers_info: Mapping[str, Any]) -> Optional[BaseTool]:
        tools = self.resolver.tools_map(mcp_servers_info)
        return tools.get(tool_name)

    async def ainvoke(
        self,
        *,
        tool_name: str,
        args: Dict[str, Any],
        mcp_servers_info: Mapping[str, Any],
    ) -> str:
        tool = self._get_tool(tool_name, mcp_servers_info)
        if tool is None:
            raise ToolExecutionError(f"Unknown tool: {tool_name}")
        result = await tool.ainvoke(args)
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False)

    def get_tool_description(
        self, *, tool_name: str, mcp_servers_info: Mapping[str, Any]
    ) -> Optional[str]:
        tool = self._get_tool(tool_name, mcp_servers_info)
        return getattr(tool, "description", None) if tool is not None else None

