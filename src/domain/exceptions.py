class OrchestratorError(Exception):
    """Базовое исключение для ошибок в workshop service."""
    pass


class MCPError(OrchestratorError):
    """MCP server related exceptions."""
    pass


class MCPConnectionError(MCPError):
    """Connection issues with MCP servers."""
    pass


class MCPTimeoutError(MCPError):
    """Timeout issues with MCP servers."""
    pass


class MCPProtocolError(MCPError):
    """Protocol violations in MCP communication."""
    pass


class ConfigurationError(OrchestratorError):
    """Configuration related exceptions."""
    pass


class BranchPathError(OrchestratorError):
    """Branch path related exceptions."""
    pass


class WorkflowError(OrchestratorError):
    """Workflow execution exceptions."""
    pass


class ToolExecutionError(OrchestratorError):
    """Tool execution related exceptions."""
    pass


class LLMError(OrchestratorError):
    """LLM related exceptions."""
    pass


class ValidationError(OrchestratorError):
    """Validation related exceptions."""
    pass