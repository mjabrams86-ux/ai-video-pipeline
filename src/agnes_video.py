"""Motor de video por la API de Agnes (OpenAI Videos-compatible).

Genera videos con audio sincronizado DIRECTAMENTE desde texto, en la nube
($0/seg en promo; listado 28/09/2026). Sustituye el paso de lip-sync local
(MuseTalk/Runpod) cuando se usa la calidad "agvideo".

Uso:
    engine = AgnesVideoEngine()
    video = engine.generate("una oficina, cámara lenta", seconds=5) -> Path

Requisitos: variable AGNES_API_KEY en el entorno o en .env del proyecto.
"""
from __future__ import annotations

import os
import time
import urllib.request
from pathlib import Path
from typing import Any

import json
import logging

logger = logging.getLogger("pipeline.agnes_video")

BASE_URL = os.environ.get("AGNES_BASE_URL", "https://apihub.agnes-ai.com/v1")
POLL_TIMEOUT_SEC = int(os.environ.get("AGNES_VIDEO_TIMEOUT", "600"))


class QueueFullError(RuntimeError):
    """La cola de video de Agnes está llena (falla transitoria, reintentar)."""


class AgnesVideoEngine:
    """Video desde texto a través de la API de Agnes.

    El video final incluye audio propio del modelo (voz/ambiente sincronizado),
    así que en modo "agvideo" el compositor usa ese audio en lugar del TTS.
    """

    model = "agnes-video-2.5-flash"

    def __init__(self, size: str = "720P", aspect_ratio: str = "16:9",
                 download_dir: str | Path | None = None):
        self.size = size
        self.aspect_ratio = aspect_ratio
        self.download_dir = Path(download_dir) if download_dir else None

    def _auth(self) -> str:
        key = os.environ.get("AGNES_API_KEY", "")
        if not key:
            raise RuntimeError(
                "Falta AGNES_API_KEY. Ponla en .env del proyecto o en el entorno."
            )
        return key

    def _post_video_task(self, prompt: str, seconds: int) -> dict:
        """Crea la tarea y devuelve el cuerpo (con id para polling)."""
        body = json.dumps({
            "model": self.model,
            "prompt": prompt,
            "seconds": str(seconds),
            "mode": "text",
            "size": self.size,
            "aspect_ratio": self.aspect_ratio,
        }).encode()
        req = urllib.request.Request(
            BASE_URL + "/videos",
            data=body,
            headers={
                "Authorization": f"Bearer {self._auth()}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        # queue_full llega como JSON normal (no HTTP error)
        if data.get("code") == "video_queue_full":
            raise QueueFullError(data.get("message", "video queue is full"))
        payload = data.get("data") or data
        task_id = payload.get("video_id") or payload.get("id")
        if not task_id:
            raise RuntimeError(f"Agnes no devolvió id de tarea: {data}")
        return payload

    def _poll(self, task: dict) -> dict:
        """Polea la tarea hasta completed/failed o timeout."""
        task_id = task.get("video_id") or task.get("id")
        deadline = time.time() + POLL_TIMEOUT_SEC
        last = task
        while time.time() < deadline:
            time.sleep(2)
            last = self._status(task_id)
            status = last.get("status")
            if status == "completed":
                url = last.get("url")
                if not url:
                    raise RuntimeError("Agnes completó la tarea sin url.")
                return last
            if status in ("failed", "cancelled"):
                raise RuntimeError(f"Agnes video falló: {last.get('error') or last}")
            logger.info("[AGNES] video %s → %s (progreso %s)",
                        task_id, status, last.get("progress", "?"))
        raise TimeoutError(f"Agnes video no listo en {POLL_TIMEOUT_SEC}s")

    def _status(self, task_id: str) -> dict:
        url = (
            "https://apihub.agnes-ai.com/agnesapi"
            f"?video_id={task_id}&model_name={self.model}"
        )
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self._auth()}"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        return data.get("data") or data

    def generate(self, prompt: str, seconds: int = 5, out_path: str | None = None) -> Path:
        """Genera un video y lo descarga; devuelve la ruta local.

        seconds: 4–12 (límites de la API). out_path: ruta final deseada
        (por defecto usa download_dir con nombre automático).
        """
        seconds = max(4, min(12, int(seconds)))
        logger.info("[AGNES] creando video (%ds): %s", seconds, prompt[:80])
        task = self._post_video_task(prompt, seconds)
        result = self._poll(task)
        url = result["url"]

        if out_path:
            target = Path(out_path)
            target.parent.mkdir(parents=True, exist_ok=True)
        else:
            if self.download_dir:
                self.download_dir.mkdir(parents=True, exist_ok=True)
                target = self.download_dir / f"agnes_video_{int(time.time())}.mp4"
            else:
                target = Path("video_agnes.mp4")
        logger.info("[AGNES] descargando → %s", target.name)
        urllib.request.urlretrieve(url, target)
        return target
