from typing import Annotated, Optional, Sequence, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict, total=False):
    """Состояние агента"""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    context: dict = {}
    session_id: str
    branch_path: Optional[str] = None