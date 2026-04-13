from __future__ import annotations

from typing import Any, Dict, Mapping, Protocol, Optional


class ToolGatewayProtocol(Protocol):
    """Порт для доступа к инструментам (MCP + виртуальные) и информации о принадлежности tool -> server."""
    def tool_to_server(self, mcp_servers_info: Mapping[str, Any]) -> Dict[str, str]:
        ...

    async def ainvoke(
        self,
        *,
        tool_name: str,
        args: Dict[str, Any],
        mcp_servers_info: Mapping[str, Any],
    ) -> str:
        """
        Вызвать инструмент и вернуть строковый результат (как отправляем в ToolMessage).
        Исключения не глотаем — обработка ошибок в application service.
        """
        ...

    def get_tool_description(
        self, *, tool_name: str, mcp_servers_info: Mapping[str, Any]
    ) -> Optional[str]:
        ...

