from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ControlPayload(BaseModel):
    model_config = {"populate_by_name": True}

    control: Literal[
        "clarification_needed",
        "confirmation_needed",
        "final_report",
        "delegate_to_coder",
        "validate_work",
    ] = Field(..., alias="__control")
    question: Optional[str] = None
    message: Optional[str] = None
    text: Optional[str] = None
    task: Optional[str] = None
    description: Optional[str] = None

    @field_validator("question", "message", "text", "task", "description", mode="before")
    @classmethod
    def _coerce_optional_str(cls, v: Any) -> Any:
        if v is None or isinstance(v, str):
            return v
        try:
            import json as _json

            return _json.dumps(v, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(v)
