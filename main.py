from __future__ import annotations
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox

from core.tool_base import ToolContext
from core.registry import ToolRegistry

from tools.mp4_splitter import MP4SplitterTool
from tools.scene_setup import SceneSetupTool

CONFIG_PATH = Path("config.json")

def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    # defaults
    return {
        "ffmpeg_path": "ffmpeg",  # ou r"C:\ffmpeg\bin\ffmpeg.exe"
        "harmony_exe": r"C:\Program Files\Toon Boom Harmony 24\win64\bin\Harmony.exe",
        "harmony_script": str(Path("harmony_scripts/run_scene_setup.js").resolve()),
        "project_root": "",
        "scenes_root": "",
        "animatics_root": "",
        "bgs_root": "",
        "rigs_root": "",
        "fps": 24
    }

def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

def main():
    root = tk.Tk()
    root.title("Toon Boom Batch Tools (Harmony 24)")

    cfg = load_config()
    ctx = ToolContext(root=root, config=cfg)

    registry = ToolRegistry()
    registry.register(MP4SplitterTool)
    registry.register(SceneSetupTool)

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True)

    tool_instances = []
    for entry in registry.tools:
        frame = ttk.Frame(nb)
        frame.pack(fill="both", expand=True)
        nb.add(frame, text=entry.name)

        tool = entry.cls(ctx)  # type: ignore
        tool.build_ui(frame)
        tool_instances.append(tool)

    def on_close():
        save_config(cfg)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

if __name__ == "__main__":
    main()
