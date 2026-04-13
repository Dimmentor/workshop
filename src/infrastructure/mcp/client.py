from typing import Dict, Any, List


class MCPClient:
    """Мок-клиент"""

    async def initialize(self):
        """No-op initialization."""
        pass

    async def aclose(self):
        """No-op close."""
        pass

    async def list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """Return empty list (no MCP servers)."""
        return []

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """No-op (no MCP servers)."""
        raise NotImplementedError("MCP servers not available in single-node version")