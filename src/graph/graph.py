from typing import Optional, Any
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from src.graph.workflow import AgentWorkflow
from src.graph.state import AgentState
from src.graph.nodes.god_node import GodNode
from src.graph.nodes.docs_validator import DocsValidatorNode
from src.application.tooling.tools_resolver import ToolsResolver


def build_agent_graph(checkpointer: Optional[Any] = None):

    # tools_resolver = ToolsResolver()
    # node = GodNode(tools_resolver=tools_resolver)
    node = DocsValidatorNode()
    graph = StateGraph(AgentState)
    graph.add_node("docs_validator", node)
    graph.set_entry_point("docs_validator")
    graph.add_edge("docs_validator", END)

    compiled = graph.compile(checkpointer=checkpointer or MemorySaver())

    # png_data = compiled.get_graph().draw_mermaid_png()
    # with open("graph.png", "wb") as f:
    #     f.write(png_data)

    return AgentWorkflow(compiled)