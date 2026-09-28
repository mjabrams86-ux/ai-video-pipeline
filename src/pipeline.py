# Pipeline Maestro: Texto → Guion → Audio → Video Base → Lip-Sync → Video Final

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

# Añadir raíz del proyecto al path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.script_gen import ScriptGenerator
from src.tts_engine import TTSEngine
from src.lip_sync_latentsync import LatentSyncEngine
from src.lip_sync_musetalk import MuseTalkEngine
from src.compositing import Compositor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pipeline")


def load_config(config_path: str) -> dict:
    """Carga configuración desde YAML."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def generate_base_video(video_path: Path, duration_sec: float, resolution: str, fps: int):
    """
    Genera un video base desde una imagen de avatar usando FFmpeg.
    En producción, reemplazar con SadTalker o MuseV.
    """
    video_path.parent.mkdir(parents=True, exist_ok=True)

    # Si hay avatar, usarlo como fondo; si no, pantalla negra
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(video_path.with_suffix(".png")),  # avatar.png
        "-t", str(duration_sec),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps),
        "-vf", f"scale={resolution}",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Fallback: video negro si no hay avatar
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi", "-i",
            f"color=c=black:s={resolution}:d={duration_sec}:r={fps}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            str(video_path),
        ]
        subprocess.run(cmd, check=False)
    logger.info("[AVATAR] Video base generado: %s (%.1fs)", video_path.name, duration_sec)


def run_pipeline(prompt: str, config: dict, quality: str = "balanced"):
    """Ejecuta el pipeline completo."""

    print("=" * 60)
    print("  PIPELINE: TEXTO → VIDEO CON LIP-SYNC")
    print("=" * 60)
    print(f"  Prompt: {prompt}")
    print(f"  Calidad: {quality}")
    print("=" * 60)

    llm_cfg = config["llm"]
    tts_cfg = config["tts"]
    ls_cfg = config["lipsync"]
    comp_cfg = config["compositing"]
    paths = config["paths"]

    # Determinar motor de lip-sync
    if quality == "high":
        ls_engine = "latentsync"
    elif quality == "fast":
        ls_engine = "musetalk"
    else:
        ls_engine = ls_cfg.get("engine", "latentsync")

    # ── Inicializar componentes ──
    logger.info("[INIT] Generador de guiones (%s/%s)", llm_cfg["provider"], llm_cfg["model"])
    script_gen = ScriptGenerator(**llm_cfg)

    logger.info("[INIT] Motor TTS (%s)", tts_cfg.get("model", "xtts_v2"))
    tts = TTSEngine(
        model_name=tts_cfg.get("model", "tts_models/multilingual/multi-dataset/xtts_v2"),
        language=tts_cfg.get("language", "es"),
        speaker_wav=tts_cfg.get("speaker_wav"),
    )

    comp = Compositor(**comp_cfg)

    # Lip-sync engine
    models_dir = paths["models_dir"].replace("~", str(Path.home()))
    if ls_engine == "latentsync":
        logger.info("[INIT] Motor lip-sync: LatentSync (%s)", models_dir)
        lipsync = LatentSyncEngine(
            repo_root=models_dir,
            inference_steps=ls_cfg.get("inference_steps", 30),
            resize=ls_cfg.get("resize", 512),
            pad_top=ls_cfg.get("pad_top", 15),
            pad_bottom=ls_cfg.get("pad_bottom", 10),
        )
    else:
        muse_root = str(Path("~/proyectos/MuseTalk").expanduser())
        logger.info("[INIT] Motor lip-sync: MuseTalk (%s)", muse_root)
        lipsync = MuseTalkEngine(
            repo_root=muse_root,
            face_template=ls_cfg.get("face_template", "hubert_face"),
            use_exp_detection=ls_cfg.get("use_exp_detection", True),
        )

    # ── Directorios ──
    assets_dir = Path(paths["assets_dir"]).expanduser()
    output_dir = Path(paths["output_dir"]).expanduser()
    assets_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── FASE 1: Generar guion ──
    logger.info("=" * 40)
    logger.info("FASE 1/5: Generando guion con LLM...")
    scenes = script_gen.generate(prompt)

    # ── FASE 2: Generar audio ──
    logger.info("=" * 40)
    logger.info("FASE 2/5: Generando audio con Coqui TTS...")
    audios_dir = assets_dir / "audios"
    audios_dir.mkdir(parents=True, exist_ok=True)

    for i, scene in enumerate(scenes):
        audio_path = audios_dir / f"scene_{i:02d}.wav"
        tts.generate(scene["dialogue"], str(audio_path))
        duration = tts.get_duration(str(audio_path))
        scene["audio"] = str(audio_path)
        scene["duration"] = duration
        logger.info("  Escena %d: %.1fs — %s", i + 1, duration, scene["dialogue"][:50])

    # ── FASE 3: Video base ──
    logger.info("=" * 40)
    logger.info("FASE 3/5: Preparando video base...")
    base_dir = assets_dir / "videos_base"
    base_dir.mkdir(parents=True, exist_ok=True)

    avatar_path = paths.get("default_avatar")
    if avatar_path:
        avatar_path = Path(avatar_path).expanduser()
    else:
        avatar_path = None

    resolution = comp_cfg.get("output_resolution", "1920x1080")
    fps = comp_cfg.get("fps", 30)

    for i, scene in enumerate(scenes):
        dur = scene["duration"]
        base_vid = base_dir / f"scene_{i:02d}.mp4"
        if avatar_path and avatar_path.exists():
            generate_base_video(base_vid, dur, resolution, fps)
        else:
            # Video negro como placeholder
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi", "-i",
                f"color=c=black:s={resolution}:d={dur}:r={fps}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                str(base_vid),
            ], capture_output=True)
        scene["video_base"] = str(base_vid)
        logger.info("  Escena %d: video base (%.1fs)", i + 1, dur)

    # ── FASE 4: Lip-Sync ──
    logger.info("=" * 40)
    logger.info("FASE 4/5: Aplicando lip-sync (%s)...", ls_engine)
    synced_dir = assets_dir / "videos_synced"
    synced_dir.mkdir(parents=True, exist_ok=True)

    for i, scene in enumerate(scenes):
        base_vid = scene["video_base"]
        audio = scene["audio"]
        synced_vid = synced_dir / f"scene_{i:02d}.mp4"

        try:
            lipsync.sync(base_vid, audio, str(synced_vid))
        except Exception as e:
            logger.error("  Escena %d falló lip-sync: %s. Usando video base.", i + 1, e)
            # Fallback: copiar video base si falla lip-sync
            subprocess.run(["cp", base_vid, str(synced_vid)], check=False)

        scene["lip_synced_video"] = str(synced_vid)
        logger.info("  Escena %d: lip-sync completado.", i + 1)

    # ── FASE 5: Compositing ──
    logger.info("=" * 40)
    logger.info("FASE 5/5: Compilando video final...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_path = output_dir / f"video_final_{timestamp}.mp4"

    final_video = comp.build_final_video(scenes, str(assets_dir), str(final_path))

    # ── Resumen ──
    print("\n" + "=" * 60)
    print("  ✅ PIPELINE COMPLETADO")
    print(f"  📹 Video final: {final_video}")
    print(f"  🎬 Escenas procesadas: {len(scenes)}")
    print(f"  🎵 Motor TTS: Coqui XTTS v2")
    print(f"  👄 Motor Lip-Sync: {ls_engine}")
    print("=" * 60)
    return final_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline Texto → Video con Lip-Sync")
    parser.add_argument("--prompt", required=True, help="Prompt de texto para generar el video")
    parser.add_argument("--config", default="configs/pipeline.yaml", help="Ruta al config YAML")
    parser.add_argument("--quality", choices=["fast", "balanced", "high"], default="balanced",
                        help="fast=MuseTalk, balanced=auto, high=LatentSync")
    parser.add_argument("--avatar", default=None, help="Ruta a imagen de avatar PNG (opcional)")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.avatar:
        config["paths"]["default_avatar"] = args.avatar
    run_pipeline(args.prompt, config, quality=args.quality)
