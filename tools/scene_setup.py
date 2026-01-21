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
    name = "Scene Setup (JSON)"

    # --------------------------------------------------
    # UI
    # --------------------------------------------------

    def build_ui(self, parent: tk.Frame) -> None:
        self.parent = parent

        default_manifest = self.ctx.config.get("scenes_manifest", "")
        self.manifest_path = tk.StringVar(value=default_manifest)

        self.scene_list = tk.Text(parent, height=10, width=25)

        row = 0

        ttk.Label(parent, text="JSON de cenas:").grid(
            row=row, column=0, sticky="w", padx=8, pady=4
        )
        ttk.Entry(parent, textvariable=self.manifest_path, width=70).grid(
            row=row, column=1, sticky="we", padx=8
        )
        ttk.Button(
            parent, text="Browse",
            command=self._pick_manifest
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
            text="Rodar Setup (Batch)",
            command=self.run
        ).grid(row=row, column=1, sticky="e", padx=8, pady=10)

        parent.grid_columnconfigure(1, weight=1)

    def _pick_manifest(self):
        p = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")]
        )
        if p:
            self.manifest_path.set(p)

    # --------------------------------------------------
    # Run
    # --------------------------------------------------

    def _resolve_path(self, raw: str, base: Path | None = None) -> Path:
        candidate = Path(raw)
        if candidate.is_absolute() or (len(raw) > 1 and raw[1] == ":"):
            return candidate
        if base is None:
            return candidate
        return base / candidate

    def _load_manifest(self, path: Path) -> dict:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON principal deve ser um objeto")
        if "scenes" not in payload or not isinstance(payload["scenes"], list):
            raise ValueError("JSON deve conter a lista 'scenes'")
        return payload

    def _scene_dir_from_manifest(self, manifest: dict, scene: dict) -> Path:
        project = manifest.get("project", {})
        project_paths = project.get("paths", {})

        scenes_root_raw = project_paths.get("scenes")
        scenes_root = None
        if scenes_root_raw:
            scenes_root = self._resolve_path(
                scenes_root_raw,
                Path(project.get("root_path", "") or ".")
            )

        scene_dir_raw = scene.get("scene_dir")
        scene_id = scene.get("scene_id") or scene.get("scene_code")
        if scene_dir_raw:
            return self._resolve_path(scene_dir_raw, scenes_root)
        if scenes_root and scene_id:
            return scenes_root / scene_id
        raise ValueError(
            f"Cena {scene_id!r} sem scene_dir e sem project.paths.scenes."
        )

    def run(self) -> None:
        try:
            # ---------- Paths base ----------
            harmony_exe = Path(self.ctx.config["harmony_exe"]).resolve()
            if not harmony_exe.exists():
                raise FileNotFoundError(f"Harmony.exe não encontrado:\n{harmony_exe}")

            script_js = (
                Path(__file__).parent.parent
                / "harmony_scripts"
                / "run_scene_setup.js"
            ).resolve()

            if not script_js.exists():
                raise FileNotFoundError(f"Script JS não encontrado:\n{script_js}")

            manifest_path = Path(self.manifest_path.get()).resolve()
            if not manifest_path.exists():
                raise FileNotFoundError(f"JSON não encontrado:\n{manifest_path}")
            self.ctx.config["scenes_manifest"] = str(manifest_path)

            # ---------- Scenes ----------
            requested_scenes = [
                ln.strip()
                for ln in self.scene_list.get("1.0", "end").splitlines()
                if ln.strip()
            ]

            manifest = self._load_manifest(manifest_path)
            manifest_scenes = manifest["scenes"]

            # ---------- Process ----------
            matched = 0
            for scene in manifest_scenes:
                scene_id = scene.get("scene_id") or scene.get("scene_code")
                if not scene_id:
                    continue
                if requested_scenes and scene_id not in requested_scenes:
                    continue
                matched += 1

                scene_dir = self._scene_dir_from_manifest(manifest, scene)
                scene_dir.mkdir(parents=True, exist_ok=True)

                xstage = scene_dir / f"{scene_id}.xstage"
                if not xstage.exists():
                    xstage.touch()

                # ---------- Job ----------
                job = {
                    "scene_id": scene_id,
                    "config_path": str(manifest_path)
                }

                job_path = scene_dir / "_tb_jobs" / f"job_scene_setup_{scene_id}.json"
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

            if requested_scenes and matched == 0:
                raise ValueError("Nenhuma cena encontrada no JSON com os códigos informados.")

            messagebox.showinfo(
                "Sucesso",
                "Setup executado com sucesso nas cenas selecionadas."
            )

        except subprocess.CalledProcessError as e:
            messagebox.showerror(
                "Harmony erro",
                f"Falha ao executar Harmony:\n{e}"
            )
        except Exception as e:
            messagebox.showerror("Erro", str(e))
