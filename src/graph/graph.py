from typing import Optional, Any
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from src.graph.workflow import AgentWorkflow
from src.graph.state import AgentState
from src.graph.nodes.god_node import GodNode
from src.application.tooling.tools_resolver import ToolsResolver


def build_agent_graph(checkpointer: Optional[Any] = None):

    tools_resolver = ToolsResolver()
    node = GodNode(tools_resolver=tools_resolver)

    graph = StateGraph(AgentState)
    graph.add_node("god_node", node)
    graph.set_entry_point("god_node")
    graph.add_edge("god_node", END)

    compiled = graph.compile(checkpointer=checkpointer or MemorySaver())

    # print(compiled.get_graph().draw_mermaid())

    return AgentWorkflow(compiled)