from typing import Annotated, Optional, Sequence, TypedDict, Dict, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class AgentState(TypedDict, total=False):
    """Состояние агента"""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    context: Dict[str, Any]
    session_id: str
    branch_path: Optional[str] # не используется
    docs_validation_report: Optional[str] # Последний отчёт validate_documentation (JSON), для отладки/клиентов