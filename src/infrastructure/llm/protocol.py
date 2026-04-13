from typing import Protocol, Optional

from langchain_core.language_models import BaseChatModel


class LLMFactoryProtocol(Protocol):
    """
    Порт для получения чат-модели по роли (assistant/coder/validator).
    Ноды зависят от этого интерфейса, а не от конкретной реализации (Ollama, OpenAI и т.д.).
    """

    def get(
        self,
        role: str,
        *,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> BaseChatModel:
        ...
