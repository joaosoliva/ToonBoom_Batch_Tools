from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
import tkinter as tk

class Tool(Protocol):
    name: str
    def build_ui(self, parent: tk.Frame) -> None: ...
    def run(self) -> None: ...

@dataclass
class ToolContext:
    root: tk.Tk
    config: dict
