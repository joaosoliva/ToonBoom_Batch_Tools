from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from core.tool_base import ToolContext

# ------------------------------------------------------------
# Utils
# ------------------------------------------------------------

TS_RE = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*$")

def ts_to_seconds(ts: str) -> int:
    m = TS_RE.match(ts)
    if not m:
        raise ValueError(f"Timestamp inválido: {ts!r} (use MM:SS)")
    mm = int(m.group(1))
    ss = int(m.group(2))
    return mm * 60 + ss


# ------------------------------------------------------------
# Tool
# ------------------------------------------------------------

@dataclass
class MP4SplitterTool:
    ctx: ToolContext
    name = "MP4 Splitter"

    # ---------------- UI ----------------

    def build_ui(self, parent: tk.Frame) -> None:
        self.parent = parent

        self.master_var = tk.StringVar(value="")
        self.outdir_var = tk.StringVar(value="")
        self.start_idx_var = tk.StringVar(value="1")

        row = 0

        ttk.Label(parent, text="MP4 master:").grid(
            row=row, column=0, sticky="w", padx=8, pady=6
        )
        ttk.Entry(parent, textvariable=self.master_var, width=70).grid(
            row=row, column=1, sticky="we", padx=8
        )
        ttk.Button(parent, text="Browse", command=self._pick_master).grid(
            row=row, column=2, padx=8
        )
        row += 1

        ttk.Label(parent, text="Saída:").grid(
            row=row, column=0, sticky="w", padx=8, pady=6
        )
        ttk.Entry(parent, textvariable=self.outdir_var, width=70).grid(
            row=row, column=1, sticky="we", padx=8
        )
        ttk.Button(parent, text="Browse", command=self._pick_outdir).grid(
            row=row, column=2, padx=8
        )
        row += 1

        ttk.Label(parent, text="Cena inicial (C001 = 1):").grid(
            row=row, column=0, sticky="w", padx=8, pady=6
        )
        ttk.Entry(parent, textvariable=self.start_idx_var, width=10).grid(
            row=row, column=1, sticky="w", padx=8
        )
        row += 1

        ttk.Label(parent, text="Timestamps (MM:SS – um por linha):").grid(
            row=row, column=0, sticky="nw", padx=8, pady=6
        )
        self.ts_text = tk.Text(parent, height=8, width=40)
        self.ts_text.grid(
            row=row, column=1, sticky="we", padx=8, pady=6
        )
        row += 1

        ttk.Button(
            parent, text="Gerar MP4s", command=self.run
        ).grid(row=row, column=1, sticky="e", padx=8, pady=6)
        row += 1

        # -------- Console de debug --------
        ttk.Label(parent, text="Console / Debug:").grid(
            row=row, column=0, sticky="nw", padx=8, pady=6
        )

        self.console = tk.Text(
            parent,
            height=14,
            bg="#111111",
            fg="#00ff00",
            insertbackground="white"
        )
        self.console.grid(
            row=row, column=1, columnspan=2, sticky="nsew", padx=8, pady=6
        )

        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(row, weight=1)

    # ---------------- Helpers ----------------

    def log(self, msg: str):
        self.console.insert("end", msg + "\n")
        self.console.see("end")
        self.console.update_idletasks()

    def _pick_master(self):
        p = filedialog.askopenfilename(filetypes=[("MP4 files", "*.mp4")])
        if p:
            self.master_var.set(p)

    def _pick_outdir(self):
        p = filedialog.askdirectory()
        if p:
            self.outdir_var.set(p)

    # ---------------- Run ----------------

    def run(self) -> None:
        self.console.delete("1.0", "end")

        try:
            master = Path(self.master_var.get()).resolve()
            outdir = Path(self.outdir_var.get()).resolve()
            start_idx = int(self.start_idx_var.get())

            if not master.exists():
                raise FileNotFoundError(f"MP4 não encontrado: {master}")

            outdir.mkdir(parents=True, exist_ok=True)

            self.log("=== MP4 SPLITTER ===")
            self.log(f"Master: {master}")
            self.log(f"Output: {outdir}")
            self.log(f"Cena inicial: C{start_idx:03d}")

            lines = [
                ln.strip()
                for ln in self.ts_text.get("1.0", "end").splitlines()
                if ln.strip()
            ]

            self.log(f"Timestamps: {lines}")

            if len(lines) < 2:
                raise ValueError("Cole pelo menos 2 timestamps.")

            secs = [ts_to_seconds(x) for x in lines]

            if secs != sorted(secs):
                raise ValueError("Timestamps precisam estar em ordem crescente.")

            ffmpeg = self.ctx.config.get("ffmpeg_path", "ffmpeg")
            self.log(f"FFmpeg: {ffmpeg}")

            for i in range(len(secs) - 1):
                a = secs[i]
                b = secs[i + 1]
                idx = start_idx + i
                name = f"C{idx:03d}.mp4"
                out = outdir / name

                duration = b - a

                cmd = [
                    ffmpeg,
                    "-hide_banner",
                    "-y",
                    "-ss", str(a),
                    "-t", str(duration),
                    "-i", str(master),
                    "-c", "copy",
                    str(out)
                ]


                self.log("\n------------------------------")
                self.log(f"Gerando {name}")
                self.log("CMD:")
                self.log(" ".join(cmd))

                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True
                )

                if proc.stdout:
                    self.log("\nSTDOUT:")
                    self.log(proc.stdout)

                if proc.stderr:
                    self.log("\nSTDERR:")
                    self.log(proc.stderr)

                if proc.returncode != 0:
                    raise RuntimeError(f"FFmpeg falhou ao gerar {name}")

            messagebox.showinfo(
                "Sucesso",
                f"{len(secs) - 1} MP4s gerados com sucesso."
            )

        except Exception as e:
            self.log("\n❌ ERRO:")
            self.log(str(e))
