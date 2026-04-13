from dataclasses import dataclass
from src.graph.graph import build_agent_graph
from src.infrastructure.mcp.client import MCPClient


@dataclass
class Components:
    workflow: object
    mcp_client: MCPClient


def build_components() -> Components:
    workflow = build_agent_graph()
    mcp_client = MCPClient()

    return Components(workflow=workflow, mcp_client=mcp_client)