# MuseTalk Engine
# Wrapper para lip-sync de Tencent MuseTalk.
#
# Interfaz real de MuseTalk: scripts/inference.py lee un YAML de tareas
# (task_N: {video_path, audio_path, result_name}) y escribe el video
# resultante en result_dir/version/<nombre>_concat.mp4.
#
# Compatible con CPU (fallback) — viable en Mac Apple Silicon, aunque lento.

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class MuseTalkEngine:
    """
    Ejecuta MuseTalk via subprocess para aplicar lip-sync.
    Requiere: repositorio clonado + pesos descargados en ./models/.
    """

    def __init__(self, repo_root: str, version: str = "v1.5",
                 use_float16: bool = False, bbox_shift: int = 0):
        self.repo_root = Path(repo_root)
        self.version = "v15" if version == "v1.5" else "v1"

        # Rutas de pesos según versión
        if self.version == "v15":
            self.unet_model = self.repo_root / "models/musetalkV15/unet.pth"
            self.unet_cfg = self.repo_root / "models/musetalkV15/musetalk.json"
        else:
            self.unet_model = self.repo_root / "models/musetalk/pytorch_model.bin"
            self.unet_cfg = self.repo_root / "models/musetalk/musetalk.json"
        self.use_float16 = use_float16
        self.bbox_shift = bbox_shift
        logger.info("[MUSE-TALK] MuseTalk %s configurado (repo: %s)", version, repo_root)

    def ensure_weights(self):
        """Descarga pesos de HuggingFace si no existen."""
        if self.unet_model.exists():
            logger.info("[MUSE-TALK] Pesos ya presentes.")
            return
        logger.info("[MUSE-TALK] Descargando pesos desde HuggingFace...")
        from huggingface_hub import snapshot_download
        snapshot_download(
            "TMElyralab/MuseTalk",
            local_dir=str(self.repo_root / "models"),
            allow_patterns=[
                "musetalk/*", "musetalkV15/*", "syncnet/*",
                "dwpose/*", "face-parse-bisent/*", "sd-vae/*", "whisper/*",
            ],
        )
        logger.info("[MUSE-TALK] Pesos descargados.")

    def sync(self, video_path: str, audio_path: str, output_path: str) -> Path:
        """
        Aplica lip-sync: escribe un YAML de tarea, ejecuta scripts.inference
        y mueve el video resultante a output_path.
        """
        self.ensure_weights()
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        result_dir = out.parent / "_musetalk_result"
        result_dir.mkdir(parents=True, exist_ok=True)
        result_name = out.stem

        # YAML de tarea con rutas relativas al repo
        task_yaml = result_dir / "task_config.yaml"
        task = {
            "task_0": {
                "video_path": _rel(video_path, self.repo_root),
                "audio_path": _rel(audio_path, self.repo_root),
                "result_name": result_name,
            }
        }
        if self.bbox_shift != 0:
            task["task_0"]["bbox_shift"] = self.bbox_shift
        with open(task_yaml, "w") as f:
            yaml.safe_dump(task, f)

        cmd = [
            sys.executable, "-m", "scripts.inference",
            "--inference_config", str(task_yaml),
            "--result_dir", str(result_dir),
            "--unet_model_path", str(self.unet_model),
            "--unet_config", str(self.unet_cfg),
            "--version", self.version,
        ]
        if self.use_float16:
            cmd.append("--use_float16")

        logger.info("[MUSE-TALK] Ejecutando scripts.inference (version=%s)...", self.version)
        result = subprocess.run(cmd, capture_output=True, text=True,
                                cwd=str(self.repo_root), timeout=3600)
        if result.returncode != 0:
            logger.error("[MUSE-TALK] ERROR: %s", result.stderr[-500:])
            raise RuntimeError(f"MuseTalk falló: {result.stderr[-300:]}")

        # Buscar el video generado: result_dir/version/<result_name>*.mp4
        candidates = list((result_dir / self.version).glob(f"{result_name}*.mp4"))
        if not candidates:
            raise RuntimeError(
                f"MuseTalk no produjo salida en {result_dir / self.version}. "
                f"stderr: {result.stderr[-300:]}"
            )
        generated = max(candidates, key=lambda p: p.stat().st_size)
        generated.replace(out)
        logger.info("[MUSE-TALK] Resultado: %s", out)
        return out


def _rel(p: str, root: Path) -> str:
    """Devuelve la ruta relativa al repo si es posible, sino la absoluta."""
    p = str(Path(p).resolve())
    try:
        return os.path.relpath(p, root)
    except ValueError:
        return p
