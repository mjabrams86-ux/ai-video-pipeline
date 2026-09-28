# LatentSync Engine
# Wrapper para lip-sync de alta calidad con LatentSync 1.6 (ByteDance)
#
# CLI real: `python -m scripts.inference` (no "infer.py").
# Requisitos:
#   - Repositorio clonado con dependencias (requirements.txt)
#   - Checkpoints descargados: huggingface-cli download ByteDance/LatentSync-1.6
#   - GPU NVIDIA (CUDA) — LatentSync NO corre en Mac Apple Silicon.
#     En Mac, usa MuseTalk (fallback a CPU) o Rentpod para LatentSync.

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class LatentSyncEngine:
    """
    Ejecuta LatentSync via subprocess para lip-sync de alta calidad (512x512).
    Requiere GPU NVIDIA (CUDA).
    """

    def __init__(self, repo_root: str, inference_steps: int = 20,
                 guidance_scale: float = 1.5, enable_deepcache: bool = True,
                 unet_config: str = "configs/unet/stage2_512.yaml"):
        self.repo_root = Path(repo_root)
        self.inference_steps = inference_steps
        self.guidance_scale = guidance_scale
        self.enable_deepcache = enable_deepcache
        self.unet_config = unet_config
        self.ckpt_dir = self.repo_root / "checkpoints"
        self.unet_ckpt = self.ckpt_dir / "latentsync_unet.pt"
        logger.info("[LIPSYNC] LatentSync configurado desde %s", repo_root)

    def ensure_checkpoints(self):
        """Descarga latentsync_unet.pt + whisper desde HuggingFace si no existen."""
        if self.unet_ckpt.exists() and (self.ckpt_dir / "whisper").exists():
            logger.info("[LIPSYNC] Checkpoints ya presentes.")
            return
        logger.info("[LIPSYNC] Descargando checkpoints de ByteDance/LatentSync-1.6...")
        cmds = [
            [sys.executable, "-m", "huggingface_hub", "download",
             "ByteDance/LatentSync-1.6", "whisper/tiny.pt", "--local-dir", str(self.ckpt_dir)],
            [sys.executable, "-m", "huggingface_hub", "download",
             "ByteDance/LatentSync-1.6", "latentsync_unet.pt", "--local-dir", str(self.ckpt_dir)],
        ]
        for c in cmds:
            r = subprocess.run(c, capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(f"Descarga de checkpoint falló: {r.stderr[-400:]}")
        logger.info("[LIPSYNC] Checkpoints descargados.")

    def sync(self, video_path: str, audio_path: str, output_path: str) -> Path:
        """
        Aplica lip-sync al video usando el audio.
        Args:
            video_path: Video base.
            audio_path: Audio (.wav) a sincronizar.
            output_path: Ruta de salida del video con lip-sync.
        Returns:
            Path al video resultante.
        """
        self.ensure_checkpoints()
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            sys.executable, "-m", "scripts.inference",
            "--unet_config_path", self.unet_config,
            "--inference_ckpt_path", str(self.unet_ckpt),
            "--inference_steps", str(self.inference_steps),
            "--guidance_scale", str(self.guidance_scale),
            "--video_path", video_path,
            "--audio_path", audio_path,
            "--video_out_path", str(out),
        ]
        if self.enable_deepcache:
            cmd.append("--enable_deepcache")

        logger.info("[LIPSYNC] Ejecutando LatentSync (steps=%d)...", self.inference_steps)
        result = subprocess.run(cmd, capture_output=True, text=True,
                                cwd=str(self.repo_root), timeout=3600)
        if result.returncode != 0:
            logger.error("[LIPSYNC] ERROR: %s", result.stderr[-600:])
            raise RuntimeError(f"LatentSync falló: {result.stderr[-300:]}")

        logger.info("[LIPSYNC] Resultado: %s", out)
        return out
