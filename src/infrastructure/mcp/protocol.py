"""Протокол MCP-клиента: оркестратор зависит от интерфейса, а не от конкретной реализации."""
from typing import Any, Dict, List, Protocol


class MCPClientProtocol(Protocol):
    """Интерфейс для работы с MCP-серверами: сессии, список инструментов, вызов, инструкции."""

    async def list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """Список инструментов одного сервера (tools/list)."""
        ...

    async def get_all_tools(self) -> Dict[str, Any]:
        """
        Метаданные всех серверов: tools + instructions.
        Возвращает: { server_name: { "url", "tools", "instructions" } }.
        """
        ...

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Вызов инструмента (tools/call)."""
        ...
