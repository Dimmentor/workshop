from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional


@dataclass(frozen=True)
class ToolCall:
    """Нормализованное представление tool_call (в LangChain оно может быть dict/объект)"""
    name: str
    tool_call_id: str
    args: Dict[str, Any]


@dataclass(frozen=True)
class ToolInvocation:
    """Данные для вызова инструмента после резолвинга/нормализации аргументов"""
    name: str
    tool_call_id: str
    server_name: Optional[str]
    args: Dict[str, Any]


@dataclass(frozen=True)
class ControlUpdate:
    """Изменения state, которые влияют на маршрутизацию графа после executor"""
    clarification_needed: Optional[str] = None
    confirmation_needed: Optional[str] = None
    final_report: Optional[str] = None
    delegate_to_coder: Optional[str] = None
    delegate_tool_call_id: Optional[str] = None
    validate_work: Optional[str] = None
    validate_tool_call_id: Optional[str] = None

    def to_state_updates(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        if self.clarification_needed is not None:
            out["clarification_needed"] = self.clarification_needed
        if self.confirmation_needed is not None:
            out["confirmation_needed"] = self.confirmation_needed
        if self.final_report is not None:
            out["final_report"] = self.final_report
        if self.delegate_to_coder is not None:
            out["_delegate_to_coder"] = self.delegate_to_coder
        if self.delegate_tool_call_id is not None:
            out["_delegate_tool_call_id"] = self.delegate_tool_call_id
        if self.validate_work is not None:
            out["_validate_work"] = self.validate_work
        if self.validate_tool_call_id is not None:
            out["_validate_tool_call_id"] = self.validate_tool_call_id
        return out


@dataclass(frozen=True)
class ToolResult:
    name: str
    tool_call_id: str
    content: str
    is_error: bool = False
    control: Optional[Mapping[str, Any]] = None

