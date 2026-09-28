# Script Generator
# Genera guiones estructurados a partir de prompts usando LLM

from __future__ import annotations

import json
import logging
import os
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


class ScriptGenerator:
    """Genera guiones estructurados usando OpenAI o Ollama local."""

    def __init__(self, provider: str = "openai", model: str = "gpt-4o",
                 max_scenes: int = 5, language: str = "es",
                 api_key_env: str = "OPENAI_API_KEY",
                 ollama_url: str = "http://localhost:11434"):
        self.provider = provider
        self.model = model
        self.max_scenes = max_scenes
        self.language = language
        self.api_key_env = api_key_env
        self.ollama_url = ollama_url
        self.client = None

        if provider == "openai":
            api_key = os.environ.get(api_key_env)
            if not api_key:
                raise ValueError(f"Variable de entorno {api_key_env} no configurada")
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
        elif provider == "ollama":
            import urllib.request
            self._ollama_url = ollama_url
        else:
            raise ValueError(f"Provider no soportado: {provider}")

    def generate(self, prompt: str) -> list[dict[str, Any]]:
        """Genera el guion estructurado a partir del prompt."""
        template = PROMPT_TEMPLATE.format(
            max_scenes=self.max_scenes,
            language=self.language,
            prompt=prompt,
        )

        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": template}],
                temperature=0.7,
                max_tokens=2000,
            )
            raw = response.choices[0].message.content.strip()
        elif self.provider == "ollama":
            raw = self._call_ollama(template)
        else:
            raise ValueError(f"Provider no soportado: {self.provider}")

        # Limpiar posibles marcas markdown
        raw = raw.replace("```json", "").replace("```", "").strip()
        scenes = json.loads(raw)
        logger.info("[SCRIPT] Generadas %d escenas.", len(scenes))
        for i, s in enumerate(scenes):
            logger.info("  Escena %d: \"%s...\"", i + 1, s["dialogue"][:50])
        return scenes

    def _call_ollama(self, prompt: str) -> str:
        """Llama a Ollama local para generación de guion."""
        import urllib.request
        import json as _json
        data = _json.dumps({
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }).encode()
        req = urllib.request.Request(
            f"{self._ollama_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = _json.loads(resp.read())
        return result["response"].strip()
