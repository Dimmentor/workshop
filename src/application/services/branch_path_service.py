import logging
import os
import re
from typing import Any, Dict, Optional

from src.domain.exceptions import BranchPathError

logger = logging.getLogger(__name__)


class BranchPathService:
    """Сервис для управления branch_path в состоянии графа.

    Детальный OTel по каждому чтению отключён: смотрите node.prepare и кэш, иначе шум в трейсах.
    """

    _VALID_DIR_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")
    _MAX_PATH_LENGTH = 260
    _BRANCH_PATH_CHANGING_TOOLS = {"clone_branch", "delete_workspace"}
    _BRANCH_PATH_DELETING_TOOLS = {"delete_workspace"}

    @staticmethod
    def get_branch_path(state: Dict[str, Any]) -> str:
        """
        Get branch_path from AgentState.
        Since branch_path is persisted via LangGraph checkpoints,
        no additional restoration logic is needed.
        """
        branch_path = state.get("branch_path")
        if branch_path:
            return str(branch_path)

        # Fallback to context for backward compatibility
        context = state.get("context") or {}
        context_path = context.get("branch_path")
        if context_path:
            logger.debug("branch_path from context (backward compatibility)")
            return str(context_path)

        return ""

    @staticmethod
    def validate_branch_path(branch_path: str) -> tuple[bool, Optional[str]]:
        """Валидировать путь к workspace"""
        if not branch_path:
            return False, "branch_path cannot be empty"

        if len(branch_path) > BranchPathService._MAX_PATH_LENGTH:
            return False, f"branch_path too long (max {BranchPathService._MAX_PATH_LENGTH} chars)"

        dir_name = os.path.basename(branch_path)
        if not BranchPathService._VALID_DIR_PATTERN.match(dir_name):
            return (
                False,
                f"Invalid directory name: {dir_name}. Only alphanumeric, dot, underscore, hyphen allowed",
            )

        if os.path.isabs(branch_path):
            return False, f"Absolute paths not allowed: {branch_path}"

        if ".." in branch_path or branch_path.startswith("/"):
            return False, f"Path traversal not allowed: {branch_path}"

        return True, None

    @staticmethod
    def extract_from_tool_result(content: Any) -> str:
        """Извлечь branch_path из результата инструмента"""
        data = None
        if isinstance(content, dict):
            data = content
        elif isinstance(content, str) and content.strip():
            try:
                import json

                data = json.loads(content)
            except json.JSONDecodeError:
                return ""

        if isinstance(data, dict):
            if "error" in data:
                return ""

            path = (
                data.get("workspace")
                or data.get("branch_path")
                or data.get("result", {}).get("workspace")
                or data.get("result", {}).get("branch_path")
                or ""
            )
            if path:
                return str(path).strip()

        return ""

    @staticmethod
    def can_tool_change_branch_path(tool_name: str) -> bool:
        return tool_name in BranchPathService._BRANCH_PATH_CHANGING_TOOLS

    @staticmethod
    def can_tool_delete_branch_path(tool_name: str) -> bool:
        return tool_name in BranchPathService._BRANCH_PATH_DELETING_TOOLS

    @staticmethod
    def should_update_branch_path(tool_name: str, tool_result: Any, current_path: str) -> tuple[bool, str]:
        if not BranchPathService.can_tool_change_branch_path(tool_name):
            return False, current_path

        extracted_path = BranchPathService.extract_from_tool_result(tool_result)

        if not extracted_path:
            return False, current_path

        if tool_name not in BranchPathService._BRANCH_PATH_CHANGING_TOOLS:
            return False, current_path

        if BranchPathService.can_tool_delete_branch_path(tool_name):
            return True, ""

        if extracted_path != current_path:
            return True, extracted_path

        return False, current_path

    @staticmethod
    def update_branch_path(
        state: Dict[str, Any],
        new_path: Optional[str],
        source: str = "unknown",
        force: bool = False,
    ) -> Dict[str, Any]:
        """Обновить branch_path в состоянии с валидацией"""
        old_path = state.get("branch_path", "")

        if new_path is None and not force:
            logger.warning("Attempted to clear branch_path without force flag - ignoring")
            return state

        if old_path and new_path and new_path != old_path and not force:
            logger.warning(
                "Attempted to change branch_path from '%s' to '%s' without force - ignoring",
                old_path,
                new_path,
            )
            return state

        if new_path is None:
            logger.info("Clearing branch_path from state (forced)")
            state["branch_path"] = None
            context = state.get("context") or {}
            context.pop("branch_path", None)
            state["context"] = context
            return state

        if new_path:
            is_valid, error = BranchPathService.validate_branch_path(new_path)
            if not is_valid:
                logger.error("Invalid branch_path: %s", error)
                raise BranchPathError(f"Invalid branch_path: {error}")

        state["branch_path"] = new_path
        context = state.get("context") or {}
        if new_path:
            context["branch_path"] = new_path
        else:
            context.pop("branch_path", None)
        state["context"] = context

        logger.info("Updated branch_path: '%s' -> '%s' (source: %s, force: %s)", old_path, new_path, source, force)
        return state

    @staticmethod
    def ensure_branch_path(state: Dict[str, Any], error_message: str = "Workspace not found") -> str:
        branch_path = BranchPathService.get_branch_path(state)

        if not branch_path:
            logger.error(error_message)
            raise BranchPathError(error_message)

        return branch_path

    @staticmethod
    def validate_branch_path_integrity(state: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        state_path = state.get("branch_path")
        context = state.get("context") or {}
        context_path = context.get("branch_path")

        if not state_path and not context_path:
            return True, None

        if state_path != context_path:
            error = f"Branch path mismatch: state='{state_path}' vs context='{context_path}'"
            logger.warning(error)
            return False, error

        return True, None
