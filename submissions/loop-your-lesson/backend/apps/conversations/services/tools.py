"""PreplyTool base class and registry.

Adapted from Medallion AI Phone Agent (apps/ai_chat/tools/base.py).
"""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class PreplyTool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def args_schema(self) -> type[BaseModel]: ...

    @property
    def requires_approval(self) -> bool:
        return False

    @property
    def category(self) -> str:
        return "query"

    @property
    def context_prompt(self) -> str | None:
        return None

    async def execute(self, *, conversation=None, **kwargs: Any) -> tuple[str, dict[str, Any]]:
        """Execute tool and return (message_for_llm, widget_data)."""
        raise NotImplementedError


TOOL_REGISTRY: dict[str, type[PreplyTool]] = {}


def register_tool(cls: type[PreplyTool]) -> type[PreplyTool]:
    instance = cls()
    TOOL_REGISTRY[instance.name] = cls
    return cls
