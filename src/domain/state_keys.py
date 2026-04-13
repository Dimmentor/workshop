from __future__ import annotations
from typing import Tuple

"""
Единая карта ключей состояния LangGraph.
"""

STATE_KEY_MESSAGES = "messages"
STATE_KEY_CONTEXT = "context"
STATE_KEY_SESSION_ID = "session_id"
STATE_KEY_BRANCH_PATH = "branch_path"

STATE_KEY_CLARIFICATION_NEEDED = "clarification_needed"
STATE_KEY_CONFIRMATION_NEEDED = "confirmation_needed"
STATE_KEY_FINAL_REPORT = "final_report"
STATE_KEY_MCP_SERVERS_INFO = "mcp_servers_info"

STATE_KEY_DELEGATE_TO_CODER = "_delegate_to_coder"
STATE_KEY_DELEGATE_TOOL_CALL_ID = "_delegate_tool_call_id"
STATE_KEY_VALIDATE_WORK = "_validate_work"
STATE_KEY_VALIDATE_TOOL_CALL_ID = "_validate_tool_call_id"


# Ключи которые НЕ нужно сбрасывать между сообщениями чата
PRESERVED_STATE_KEYS = (
    STATE_KEY_BRANCH_PATH,
    STATE_KEY_CONTEXT,
    STATE_KEY_MCP_SERVERS_INFO,
)

CONTROL_KEYS_TO_RESET: Tuple[str, ...] = (
    STATE_KEY_CLARIFICATION_NEEDED,
    STATE_KEY_CONFIRMATION_NEEDED,
    STATE_KEY_FINAL_REPORT,
    STATE_KEY_DELEGATE_TO_CODER,
    STATE_KEY_DELEGATE_TOOL_CALL_ID,
    STATE_KEY_VALIDATE_WORK,
    STATE_KEY_VALIDATE_TOOL_CALL_ID,
)

