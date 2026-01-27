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

FRAME_RE = re.compile(r"^\s*\d+\s*$")

def parse_frame_count(value: str) -> int:
    if not FRAME_RE.match(value):
        raise ValueError(f"Número de frames inválido: {value!r}")
    frames = int(value)
    if frames <= 0:
        raise ValueError("Número de frames precisa ser maior que zero.")
    return frames

def parse_frame_rate(value: str) -> float:
    if "/" in value:
        num, den = value.split("/", 1)
        return float(num) / float(den)
    return float(value)

def get_video_fps(ffprobe: str, master: Path) -> float:
    cmd = [
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(master)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError("Não foi possível detectar FPS do vídeo.")
    return parse_frame_rate(result.stdout.strip())

def has_audio_stream(ffprobe: str, master: Path) -> bool:
    cmd = [
        ffprobe,
        "-v", "error",
        "-select_streams", "a",
        "-show_entries", "stream=index",
        "-of", "csv=p=0",
        str(master)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return bool(result.stdout.strip())


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

        ttk.Label(parent, text="Frames por cena (um por linha):").grid(
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

            self.log(f"Frames por cena: {lines}")

            if len(lines) < 1:
                raise ValueError("Cole pelo menos 1 valor de frame.")

            frame_counts = [parse_frame_count(x) for x in lines]

            ffmpeg = self.ctx.config.get("ffmpeg_path", "ffmpeg")
            ffprobe = self.ctx.config.get("ffprobe_path", "ffprobe")
            self.log(f"FFmpeg: {ffmpeg}")
            self.log(f"FFprobe: {ffprobe}")

            fps = get_video_fps(ffprobe, master)
            audio_enabled = has_audio_stream(ffprobe, master)
            self.log(f"FPS detectado: {fps:.6f}")
            self.log(f"Áudio detectado: {'sim' if audio_enabled else 'não'}")

            start_frame = 0

            for i, frames in enumerate(frame_counts):
                idx = start_idx + i
                name = f"C{idx:03d}.mp4"
                out = outdir / name

                end_frame = start_frame + frames
                start_time = start_frame / fps
                end_time = end_frame / fps

                if audio_enabled:
                    filter_complex = (
                        f"[0:v]trim=start_frame={start_frame}:end_frame={end_frame},"
                        f"setpts=PTS-STARTPTS[v];"
                        f"[0:a]atrim=start={start_time:.6f}:end={end_time:.6f},"
                        f"asetpts=PTS-STARTPTS[a]"
                    )
                    cmd = [
                        ffmpeg,
                        "-hide_banner",
                        "-y",
                        "-i", str(master),
                        "-filter_complex", filter_complex,
                        "-map", "[v]",
                        "-map", "[a]",
                        "-c:v", "libx264",
                        "-crf", "18",
                        "-preset", "veryfast",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        str(out)
                    ]
                else:
                    vf = (
                        f"trim=start_frame={start_frame}:end_frame={end_frame},"
                        f"setpts=PTS-STARTPTS"
                    )
                    cmd = [
                        ffmpeg,
                        "-hide_banner",
                        "-y",
                        "-i", str(master),
                        "-vf", vf,
                        "-an",
                        "-c:v", "libx264",
                        "-crf", "18",
                        "-preset", "veryfast",
                        str(out)
                    ]


                self.log("\n------------------------------")
                self.log(f"Gerando {name}")
                self.log(f"Frames: {start_frame} -> {end_frame - 1} ({frames})")
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

                start_frame = end_frame

            messagebox.showinfo(
                "Sucesso",
                f"{len(frame_counts)} MP4s gerados com sucesso."
            )

        except Exception as e:
            self.log("\n❌ ERRO:")
            self.log(str(e))
