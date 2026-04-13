from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from langchain_core.tools import BaseTool
from src.application.tooling.tools_resolver import ToolsResolver
from src.infrastructure.llm.factory import get_llm
from src.infrastructure.llm.protocol import LLMFactoryProtocol
from src.graph.state import AgentState
import logging

logger = logging.getLogger(__name__)


@dataclass
class BaseUseCaseConfig:
    """Конфигурация для usecase - задаёт промпты, модель и параметры"""
    model_name: str
    system_prompt_template: str
    is_iterative: bool = False
    max_iterations: int = 10
    enable_streaming: bool = True


class BaseUseCase(ABC):
    """
    Базовый класс для всех usecases.
    Унифицирует интерфейс и общую логику:
    - Инициализация с tools_resolver и llm_factory
    - Получение LLM по имени модели
    - Биндинг инструментов
    - Построение системного промпта
    """
    
    def __init__(
        self,
        tools_resolver: Optional[ToolsResolver] = None,
        llm_factory: Optional[LLMFactoryProtocol] = None,
        config: Optional[BaseUseCaseConfig] = None,
        **kwargs
    ):
        # Allow flexible initialization for backward compatibility
        if tools_resolver is not None:
            self.tools_resolver = tools_resolver
        self.llm_factory = llm_factory  # Keep for compatibility
        self.config = config or BaseUseCaseConfig(
            model_name="default",
            system_prompt_template="You are a helpful assistant."
        )
    
    def _get_llm(self):
        """Получение LLM по имени модели из конфигурации"""
        return get_llm(self.config.model_name)
    
    def _bind_tools(self, llm, tools: List[BaseTool]):
        """Биндинг инструментов к LLM"""
        return llm.bind_tools(tools)
    
    def _build_system_prompt(self, state: AgentState, tools: List[BaseTool]) -> str:
        """
        Построение системного промпта.
        Переопределяется в подклассах для специфической логики.
        """
        tools_desc = "\n".join(f"- {t.name}: {t.description}" for t in tools)
        return f"{self.config.system_prompt_template}\n\nAvailable tools:\n{tools_desc}"
    
    def _get_tools(self, state: AgentState) -> List[BaseTool]:
        """
        Получение списка инструментов.
        По умолчанию использует tools_resolver для всех инструментов.
        Переопределяется в подклассах для специфической фильтрации.
        """
        if not hasattr(self, 'tools_resolver'):
            return []
        mcp_servers_info = {} # вместо get_mcp_servers_info(state)
        return self.tools_resolver.tools_list(mcp_servers_info)
    
    @abstractmethod
    async def run(self, state: AgentState, **kwargs) -> Dict[str, Any]:
        """
        Основной метод выполнения usecase.
        Должен быть реализован в подклассах.
        """
        pass
