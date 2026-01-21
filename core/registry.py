from __future__ import annotations
from dataclasses import dataclass
from typing import Type
from core.tool_base import ToolContext, Tool

@dataclass
class ToolEntry:
    cls: Type[Tool]
    name: str

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: list[ToolEntry] = []

    def register(self, tool_cls: Type[Tool]) -> None:
        self._tools.append(ToolEntry(cls=tool_cls, name=getattr(tool_cls, "name", tool_cls.__name__)))

    @property
    def tools(self) -> list[ToolEntry]:
        return list(self._tools)
