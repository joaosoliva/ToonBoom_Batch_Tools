from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
import subprocess
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from core.tool_base import ToolContext


@dataclass
class SceneSetupTool:
    ctx: ToolContext
    name = "Scene Setup (Animatic)"

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self, parent: tk.Frame) -> None:
        self.parent = parent

        self.scenes_root = tk.StringVar(value="")
        self.anim_root = tk.StringVar(value="")

        self.scene_list = tk.Text(parent, height=10, width=25)

        row = 0

        ttk.Label(parent, text="Scenes root:").grid(
            row=row, column=0, sticky="w", padx=8, pady=4
        )
        ttk.Entry(parent, textvariable=self.scenes_root, width=70).grid(
            row=row, column=1, sticky="we", padx=8
        )
        ttk.Button(
            parent, text="Browse",
            command=lambda: self._pick_dir(self.scenes_root)
        ).grid(row=row, column=2, padx=8)
        row += 1

        ttk.Label(parent, text="Animatics root:").grid(
            row=row, column=0, sticky="w", padx=8, pady=4
        )
        ttk.Entry(parent, textvariable=self.anim_root, width=70).grid(
            row=row, column=1, sticky="we", padx=8
        )
        ttk.Button(
            parent, text="Browse",
            command=lambda: self._pick_dir(self.anim_root)
        ).grid(row=row, column=2, padx=8)
        row += 1

        ttk.Label(
            parent, text="Cenas (uma por linha: C01, C02...)"
        ).grid(row=row, column=0, sticky="nw", padx=8, pady=6)

        self.scene_list.grid(
            row=row, column=1, sticky="we", padx=8, pady=6
        )
        row += 1

        ttk.Button(
            parent,
            text="Importar Animatic (Batch)",
            command=self.run
        ).grid(row=row, column=1, sticky="e", padx=8, pady=10)

        parent.grid_columnconfigure(1, weight=1)

    def _pick_dir(self, var):
        p = filedialog.askdirectory()
        if p:
            var.set(p)

    # --------------------------------------------------
    # Run
    # --------------------------------------------------

    def run(self) -> None:
        try:
            # ---------- Paths base ----------
            harmony_exe = Path(self.ctx.config["harmony_exe"]).resolve()
            if not harmony_exe.exists():
                raise FileNotFoundError(f"Harmony.exe não encontrado:\n{harmony_exe}")

            script_js = (
                Path(__file__).parent.parent
                / "harmony_scripts"
                / "import_animatic.js"
            ).resolve()

            if not script_js.exists():
                raise FileNotFoundError(f"Script JS não encontrado:\n{script_js}")

            scenes_root = Path(self.scenes_root.get()).resolve()
            anim_root = Path(self.anim_root.get()).resolve()

            if not scenes_root.exists():
                raise FileNotFoundError(f"Scenes root inválido:\n{scenes_root}")

            if not anim_root.exists():
                raise FileNotFoundError(f"Animatics root inválido:\n{anim_root}")

            # ---------- Scenes ----------
            scenes = [
                ln.strip()
                for ln in self.scene_list.get("1.0", "end").splitlines()
                if ln.strip()
            ]

            if not scenes:
                raise ValueError("Nenhuma cena listada")

            # ---------- Process ----------
            for scene_code in scenes:
                scene_dir = scenes_root / scene_code
                scene_dir.mkdir(parents=True, exist_ok=True)

                xstage = scene_dir / f"{scene_code}.xstage"
                if not xstage.exists():
                    xstage.touch()

                animatic = anim_root / f"{scene_code}.mp4"
                if not animatic.exists():
                    raise FileNotFoundError(
                        f"Animatic não encontrado:\n{animatic}"
                    )

                # ---------- Job ----------
                job = {
                    "scene_code": scene_code,
                    "scene_dir": str(scene_dir),
                    "animatic_mp4": str(animatic)
                }

                job_path = scene_dir / "_job_animatic.json"
                job_path.write_text(
                    json.dumps(job, indent=2, ensure_ascii=False),
                    encoding="utf-8"
                )

                env = os.environ.copy()
                env["TB_JOB"] = str(job_path)

                cmd = [
                    str(harmony_exe),
                    "-batch",
                    "-scene", str(xstage),
                    "-script", str(script_js)
                ]

                subprocess.run(
                    cmd,
                    check=True,
                    env=env
                )

            messagebox.showinfo(
                "Sucesso",
                "Animatic importado com sucesso em todas as cenas."
            )

        except subprocess.CalledProcessError as e:
            messagebox.showerror(
                "Harmony erro",
                f"Falha ao executar Harmony:\n{e}"
            )
        except Exception as e:
            messagebox.showerror("Erro", str(e))
