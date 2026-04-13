from typing import List
from langchain_core.tools import BaseTool


class ToolsResolver:
    """Мок-версия"""

    def __init__(self):
        pass

    def tools_list(self, mcp_servers_info: dict = None) -> List[BaseTool]:
        return []

    def tools_list_for_assistant(self, mcp_servers_info: dict = None) -> List[BaseTool]:
        return []

    def tools_list_for_coder(self, mcp_servers_info: dict = None) -> List[BaseTool]:
        return []