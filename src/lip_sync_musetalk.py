# MuseTalk Engine
# Wrapper para lip-sync en tiempo real (Tencent)

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


class MuseTalkEngine:
    """
    Ejecuta MuseTalk via subprocess para lip-sync rápido (30+ fps).
    Requiere: repositorio clonado y weights descargados.
    """

    def __init__(self, repo_root: str,
                 face_template: str = "hubert_face",
                 use_exp_detection: bool = True):
        self.repo_root = Path(repo_root)
        self.face_template = face_template
        self.use_exp_detection = use_exp_detection
        logger.info("[MUSE-TALK] MuseTalk cargado desde %s", repo_root)

    def sync(self, video_path: str, audio_path: str, output_path: str) -> Path:
        """
        Aplica lip-sync al video usando MuseTalk.
        Args:
            video_path: Ruta al video base.
            audio_path: Ruta al audio generado (.wav).
            output_path: Ruta de salida del video con lip-sync.
        Returns:
            Path al video resultante.
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        # Buscar el script de inferencia
        demo_script = self.repo_root / "app.py"
        if not demo_script.exists():
            demo_script = self.repo_root / "inference.py"
        if not demo_script.exists():
            # Intentar encontrar cualquier script de inferencia
            for name in ["demo.py", "run.py", "inference.sh"]:
                candidate = self.repo_root / name
                if candidate.exists():
                    demo_script = candidate
                    break

        if not demo_script.exists():
            raise FileNotFoundError(
                "No se encontró script de inferencia en MuseTalk. "
                "Verifica la instalación."
            )

        cmd = [
            sys.executable, str(demo_script),
            "--face_video", video_path,
            "--audio_audio", audio_path,
            "--face_template", self.face_template,
            "--output_dir", str(out.parent),
            "--output_name", out.stem,
        ]
        if self.use_exp_detection:
            cmd.append("--use_exp_detection")

        logger.info("[MUSE-TALK] Ejecutando: %s", demo_script.name)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            logger.error("[MUSE-TALK] ERROR: %s", result.stderr[-500:])
            raise RuntimeError(f"MuseTalk falló: {result.stderr}")

        logger.info("[MUSE-TALK] Resultado: %s", out)
        return out
