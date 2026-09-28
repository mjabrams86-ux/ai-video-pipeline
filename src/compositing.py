# Compositor
# Orquesta el ensamblaje final: escenas + audio + transiciones → MP4

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class Compositor:
    """Une escenas con transiciones, añade audio y exporta video final."""

    def __init__(self, output_resolution: str = "1920x1080", fps: int = 30,
                 codec: str = "libx264", crf: int = 18,
                 audio_codec: str = "aac", transition_duration: float = 0.5):
        self.resolution = output_resolution
        self.fps = fps
        self.codec = codec
        self.crf = crf
        self.audio_codec = audio_codec
        self.transition_sec = transition_duration
        logger.info("[COMP] Compositor configurado: %sx%s @ %dfps",
                     output_resolution, self.fps)

    def build_final_video(self, scenes: list[dict], assets_dir: str,
                          output_path: str) -> Path:
        """
        Construye el video final uniendo todas las escenas.

        Cada scene debe tener:
          - lip_synced_video: ruta al video con lip-sync
          - audio: ruta al audio de la escena
        """
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        assets = Path(assets_dir)

        # 1. Mezclar video lip-synced + audio por escena
        mixed_clips = []
        for i, scene in enumerate(scenes):
            lip_vid = assets / scene.get("lip_synced_video", "")
            audio = assets / scene.get("audio", "")

            if not lip_vid.exists():
                logger.warning("[COMP] AVISO: video no encontrado para escena %d: %s", i, lip_vid)
                continue
            if not audio.exists():
                logger.warning("[COMP] AVISO: audio no encontrado para escena %d: %s", i, audio)
                continue

            mixed = assets / f"mixed_scene_{i:02d}.mp4"
            self._mix_scene(lip_vid, audio, mixed)
            mixed_clips.append(mixed)
            logger.info("[COMP] Escena %d mezclada: %s", i + 1, mixed.name)

        if len(mixed_clips) < 1:
            raise RuntimeError("No hay clips válidos para compilar.")

        # 2. Concatenar clips con fade transitions
        self._concat_with_transitions(mixed_clips, out)

        # 3. Limpieza
        for clip in mixed_clips:
            clip.unlink(missing_ok=True)

        logger.info("[COMP] Video final guardado: %s", out)
        return out

    def _mix_scene(self, video: Path, audio: Path, output: Path):
        """Mezcla video lip-synced con su audio."""
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video),
            "-i", str(audio),
            "-c:v", "copy",
            "-c:a", self.audio_codec,
            "-shortest",
            str(output),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("[COMP] Error mix escena: %s", result.stderr[-200:])
            raise RuntimeError(f"FFmpeg mix falló: {result.stderr}")

    def _concat_with_transitions(self, clips: list[Path], output: Path):
        """Une clips usando concat de FFmpeg."""
        n = len(clips)
        if n == 1:
            cmd = [
                "ffmpeg", "-y", "-i", str(clips[0]),
                "-c:v", self.codec, "-crf", str(self.crf),
                "-c:a", self.audio_codec,
                str(output),
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return

        # Crear lista de archivos para concat
        list_file = output.parent / "_concat_list.txt"
        with open(list_file, "w") as f:
            for clip in clips:
                f.write(f"file '{clip.resolve()}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-c:v", self.codec, "-crf", str(self.crf),
            "-c:a", self.audio_codec,
            str(output),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        list_file.unlink(missing_ok=True)

        if result.returncode != 0:
            logger.error("[COMP] Error concat: %s", result.stderr[-300:])
            raise RuntimeError(f"FFmpeg concat falló: {result.stderr}")
