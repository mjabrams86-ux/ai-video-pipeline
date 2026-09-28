# LatentSync Engine
# Wrapper para lip-sync de alta calidad con LatentSync (ByteDance)

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class LatentSyncEngine:
    """
    Ejecuta LatentSync via subprocess para aplicar lip-sync de alta calidad.
    Requiere: repositorio clonado en LANGUAGESYNC_ROOT.
    """

    def __init__(self, repo_root: str,
                 inference_steps: int = 30, resize: int = 512,
                 pad_top: int = 15, pad_bottom: int = 10):
        self.repo_root = Path(repo_root)
        self.inference_steps = inference_steps
        self.resize = resize
        self.pad_top = pad_top
        self.pad_bottom = pad_bottom
        logger.info("[LIPSYNC] LatentSync cargado desde %s", repo_root)

    def sync(self, video_path: str, audio_path: str, output_path: str) -> Path:
        """
        Aplica lip-sync al video usando el audio proporcionado.
        Args:
            video_path: Ruta al video base (sin audio sincronizado).
            audio_path: Ruta al audio generado (.wav).
            output_path: Ruta de salida del video con lip-sync.
        Returns:
            Path al video resultante.
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable,
            str(self.repo_root / "infer.py"),
            "--face_video", video_path,
            "--audio_audio", audio_path,
            "--results_dir", str(out.parent),
            "--output_name", out.stem,
            "--inference_steps", str(self.inference_steps),
            "--resize", str(self.resize),
            "--pad_top", str(self.pad_top),
            "--pad_bottom", str(self.pad_bottom),
        ]

        logger.info("[LIPSYNC] Ejecutando LatentSync...")
        logger.debug("[LIPSYNC] Cmd: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        if result.returncode != 0:
            logger.error("[LIPSYNC] ERROR stderr: %s", result.stderr[-500:])
            raise RuntimeError(f"LatentSync falló: {result.stderr}")

        logger.info("[LIPSYNC] Resultado: %s", out)
        return out
