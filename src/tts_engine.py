# Coqui TTS Engine
# Wrapper para generación de audio con XTTS v2

from __future__ import annotations

import logging
import os
from pathlib import Path

import soundfile as sf
import torch

logger = logging.getLogger(__name__)


class TTSEngine:
    """Motor de Text-to-Speech usando Coqui TTS (XTTS v2)."""

    def __init__(self, model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2",
                 language: str = "es", speaker_wav: str | None = None,
                 device: str | None = None, tos_agreed: bool = True,
                 default_speaker: str | None = "angelina"):
        self.model_name = model_name
        self.language = language
        self.speaker_wav = speaker_wav
        self.default_speaker = default_speaker
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")

        # XTTS v2 está bajo licencia CPML (no comercial). Si tos_agreed=True,
        # se acepta el ToS de forma no interactiva antes de cargar el modelo.
        if tos_agreed:
            os.environ.setdefault("COQUI_TOS_AGREED", "1")

        logger.info("[TTS] Cargando modelo %s en %s", model_name, self.device)
        from TTS.api import TTS
        self.tts = TTS(model_name).to(self.device)
        logger.info("[TTS] Modelo cargado correctamente.")

    def generate(self, text: str, output_path: str,
                 speaker_wav: str | None = None) -> Path:
        """
        Genera audio a partir de texto.
        Args:
            text: Texto a hablar.
            output_path: Ruta de salida (.wav).
            speaker_wav: Opcional. Audio de referencia para voice cloning.
        Returns:
            Path al archivo de audio generado.
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        spk = speaker_wav or self.speaker_wav
        if spk:
            logger.info("[TTS] Voice cloning desde: %s", spk)
            self.tts.tts_to_file(
                text=text, speaker_wav=spk,
                language=self.language, file_path=str(path),
            )
        else:
            logger.info("[TTS] Generando audio (speaker por defecto: %s): %s",
                        self.default_speaker, text[:60])
            self.tts.tts_to_file(
                text=text,
                speaker=self.default_speaker,
                language=self.language,
                file_path=str(path),
            )

        logger.info("[TTS] Audio guardado: %s", path)
        return path

    def get_duration(self, audio_path: str) -> float:
        """Retorna la duración en segundos del audio."""
        with sf.SoundFile(audio_path, 'r') as f:
            return len(f) / f.samplerate
