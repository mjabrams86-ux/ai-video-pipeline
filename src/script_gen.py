# Script Generator
# Genera guiones estructurados a partir de prompts usando LLM
# Soporta OpenAI (API) y Ollama (local, gratis) con reintentos automáticos.

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """
Eres un director de cine y guionista profesional.
Dado el siguiente prompt, genera un guion cinematográfico estructurado.

REGLAS:
- Máximo {max_scenes} escenas.
- Cada escena debe tener: un número, un diálogo natural (15-40 palabras),
  y una nota visual descriptiva de lo que se ve en pantalla.
- El diálogo debe sonar natural, como si lo dijera una persona real.
- Idioma del diálogo: {language}.

PROMPT: "{prompt}"

Responde SOLO con JSON válido, sin markdown, en este formato exacto:
[
  {{"scene": 1, "dialogue": "texto del diálogo", "visual_note": "descripción visual"}},
  ...
]
"""


def _extract_json(raw: str) -> str:
    """Extrae el bloque JSON de una respuesta que puede contener markdown."""
    raw = raw.strip()
    raw = raw.replace("```json", "").replace("```JSON", "").replace("```", "")
    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end != -1 and end > start:
        return raw[start:end + 1]
    return raw


def _validate(scenes: Any) -> list[dict[str, Any]]:
    """Valida y normaliza la lista de escenas."""
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("La respuesta no es una lista de escenas válida")
    clean = []
    for i, s in enumerate(scenes):
        if not isinstance(s, dict) or "dialogue" not in s:
            raise ValueError(f"Escena {i + 1} inválida: {s!r}")
        clean.append({
            "scene": int(s.get("scene", i + 1)),
            "dialogue": str(s["dialogue"]).strip(),
            "visual_note": str(s.get("visual_note", "")).strip(),
        })
    return clean


class ScriptGenerator:
    """Genera guiones estructurados usando OpenAI o Ollama local."""

    def __init__(self, provider: str = "openai", model: str = "gpt-4o",
                 max_scenes: int = 5, language: str = "es",
                 api_key_env: str = "OPENAI_API_KEY",
                 ollama_url: str = "http://localhost:11434",
                 max_retries: int = 3):
        self.provider = provider
        self.model = model
        self.max_scenes = max_scenes
        self.language = language
        self.api_key_env = api_key_env
        self._ollama_url = ollama_url
        self.max_retries = max_retries

        if provider == "openai":
            api_key = os.environ.get(api_key_env)
            if not api_key:
                raise ValueError(f"Variable de entorno {api_key_env} no configurada")
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
        elif provider != "ollama":
            raise ValueError(f"Provider no soportado: {provider}")

    def generate(self, prompt: str) -> list[dict[str, Any]]:
        """Genera el guion con reintentos ante respuestas vacías o JSON inválido."""
        template = PROMPT_TEMPLATE.format(
            max_scenes=self.max_scenes,
            language=self.language,
            prompt=prompt,
        )

        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                raw = self._call_llm(template)
                scenes = _validate(json.loads(_extract_json(raw)))
                logger.info("[SCRIPT] Generadas %d escenas (intento %d).", len(scenes), attempt)
                for i, s in enumerate(scenes):
                    logger.info("  Escena %d: \"%s...\"", i + 1, s["dialogue"][:50])
                return scenes
            except Exception as e:  # respuesta vacía, JSON inválido, error de red...
                last_err = e
                logger.warning("[SCRIPT] Intento %d falló (%s). Reintentando...", attempt, e)
                time.sleep(2 * attempt)
        raise RuntimeError(f"ScriptGen falló tras {self.max_retries} intentos: {last_err}")

    def _call_llm(self, template: str) -> str:
        """Llama al LLM (OpenAI u Ollama) y devuelve el texto crudo."""
        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": template}],
                temperature=0.7,
                max_tokens=2000,
            )
            return response.choices[0].message.content.strip()
        return self._call_ollama(template)

    def _call_ollama(self, prompt: str) -> str:
        """Llama a Ollama local vía /api/chat (stream=False)."""
        import urllib.request
        data = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.7},
        }).encode()
        req = urllib.request.Request(
            f"{self._ollama_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=600) as resp:
            result = json.loads(resp.read())
        content = result.get("message", {}).get("content", "").strip()
        if not content:
            raise ValueError("Ollama devolvió respuesta vacía")
        return content
