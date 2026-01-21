from __future__ import annotations

import datetime
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


# -----------------------------
# Resultado padronizado (debug)
# -----------------------------
@dataclass
class HarmonyRunResult:
    returncode: int
    cmd: List[str]
    stdout: str
    stderr: str
    log_path: Optional[Path] = None


def _timestamp() -> str:
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")


def strip_utf8_bom_inplace(path: Path) -> bool:
    """
    Remove BOM UTF-8 (EF BB BF) se existir.
    Isso evita alguns 'Parse error' quando o interpretador lê o 1º caractere.
    """
    data = path.read_bytes()
    if data.startswith(b"\xef\xbb\xbf"):
        path.write_bytes(data[3:])
        return True
    return False


def run_harmony_batch(
    harmony_exe: Path,
    scene_xstage: Path,
    script_js: Path,
    *,
    env_extra: Optional[Dict[str, str]] = None,
    readonly: bool = False,
    timeout_s: Optional[int] = None,
    cwd: Optional[Path] = None,
    log_dir: Optional[Path] = None,
) -> HarmonyRunResult:
    """
    Executa o Harmony em batch para rodar um script JS (Qt Script).

    Sintaxe (Stand Alone) conforme documentação:
      Harmony<Edition> PathToScene/Scene.xstage -batch -compile PathToScript/Script.js
    """
    if not harmony_exe.exists():
        raise FileNotFoundError(f"Harmony exe não encontrado: {harmony_exe}")
    if not scene_xstage.exists():
        raise FileNotFoundError(f"Scene .xstage não encontrado: {scene_xstage}")
    if not script_js.exists():
        raise FileNotFoundError(f"Script .js não encontrado: {script_js}")

    # Sanidade: remover BOM, se existir
    try:
        strip_utf8_bom_inplace(script_js)
    except Exception:
        pass

    cmd: List[str] = [
        str(harmony_exe),
        str(scene_xstage),
        "-batch",
        "-compile",
        str(script_js),
    ]
    if readonly:
        cmd.append("-readonly")

    env = os.environ.copy()
    if env_extra:
        for k, v in env_extra.items():
            env[str(k)] = str(v)

    completed = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=timeout_s,
    )

    log_path = None
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / f"harmony_batch_{scene_xstage.stem}_{_timestamp()}.log"
        log_path.write_text(
            "CMD:\n"
            + " ".join(cmd)
            + "\n\nSTDOUT:\n"
            + (completed.stdout or "")
            + "\n\nSTDERR:\n"
            + (completed.stderr or ""),
            encoding="utf-8",
            errors="replace",
        )

    return HarmonyRunResult(
        returncode=completed.returncode,
        cmd=cmd,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        log_path=log_path,
    )


def write_animatic_job(
    job_path: Path,
    *,
    animatic_mp4: Path,
    image_folder: Path,
    image_prefix: str = "ANIM_",
    start_frame: int = 1,
    audio_file: Optional[Path] = None,
) -> None:
    payload = {
        "animatic_mp4": str(animatic_mp4),
        "image_folder": str(image_folder),
        "image_prefix": str(image_prefix),
        "start_frame": int(start_frame),
    }
    if audio_file:
        payload["audio_file"] = str(audio_file)

    job_path.parent.mkdir(parents=True, exist_ok=True)
    job_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


# Assumindo a estrutura:
# ToonBoom_Batch_Tools/
#   scene_setup.py
#   harmony_scripts/
#     import_animatic.js
DEFAULT_IMPORT_ANIMATIC_JS = Path(__file__).resolve().parent / "harmony_scripts" / "import_animatic.js"


def import_animatic_to_scene(
    harmony_exe: Path,
    scene_xstage: Path,
    animatic_mp4: Path,
    *,
    script_js: Optional[Path] = None,
    scene_dir: Optional[Path] = None,
    image_subdir: str = "elements/animatic",
    image_prefix: str = "ANIM_",
    start_frame: int = 1,
    audio_file: Optional[Path] = None,
    log_dir: Optional[Path] = None,
) -> HarmonyRunResult:
    """
    Cria um TB_JOB.json e manda o Harmony importar o animatic na cena.
    """
    if script_js is None:
        script_js = DEFAULT_IMPORT_ANIMATIC_JS

    if scene_dir is None:
        scene_dir = scene_xstage.parent

    image_folder = (scene_dir / image_subdir)
    image_folder.mkdir(parents=True, exist_ok=True)

    job_path = scene_dir / "_tb_jobs" / f"job_import_animatic_{scene_xstage.stem}_{_timestamp()}.json"
    write_animatic_job(
        job_path,
        animatic_mp4=animatic_mp4,
        image_folder=image_folder,
        image_prefix=image_prefix,
        start_frame=start_frame,
        audio_file=audio_file,
    )

    # Import precisa salvar a cena no final -> NÃO use readonly
    return run_harmony_batch(
        harmony_exe=harmony_exe,
        scene_xstage=scene_xstage,
        script_js=script_js,
        env_extra={"TB_JOB": str(job_path)},
        readonly=False,
        log_dir=log_dir,
    )
