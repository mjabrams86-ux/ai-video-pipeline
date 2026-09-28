# AI Video Pipeline — Texto → Audio → Lip-Sync → Video MP4

Pipeline automatizado de generación de video con sincronización labial perfecta,
a partir de un único prompt de texto.

**Repositorios base integrados:**
- [bytedance/LatentSync](https://github.com/bytedance/LatentSync) — Lip-sync de máxima calidad (512×512)
- [TMElyralab/MuseTalk](https://github.com/TMElyralab/MuseTalk) — Lip-sync en tiempo real (30+ fps)
- [coqui-ai/TTS](https://github.com/coqui-ai/TTS) — TTS offline con XTTS v2 (16 idiomas)
- [facefusion/facefusion](https://github.com/facefusion/facefusion) — Plataforma completa de face manipulation

## Requisitos

### Hardware
- **GPU:** NVIDIA con ≥12 GB VRAM (LatentSync) o ≥8 GB (MuseTalk)
- **macOS Apple Silicon:** Funciona con FaceFusion + Coqui TTS (CPU/MPS)
- **RAM:** 32 GB recomendados
- **Disco:** 50 GB libres

### Software
```bash
# FFmpeg (obligatorio)
brew install ffmpeg          # macOS
sudo apt install ffmpeg      # Ubuntu/Debian

# Python ≥ 3.10
python3 --version
```

## Instalación rápida

```bash
# 1. Clonar este repositorio
git clone https://github.com/mjabrams86-ux/ai-video-pipeline.git
cd ai-video-pipeline

# 2. Clonar repositorios de modelos
mkdir -p ~/proyectos && cd ~/proyectos
git clone --depth 1 https://github.com/bytedance/LatentSync.git
git clone --depth 1 https://github.com/TMElyralab/MuseTalk.git

# 3. Crear entorno virtual e instalar dependencias
cd ~/proyectos/ai-video-pipeline
python3 -m venv venv && source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
nano .env  # Añadir OPENAI_API_KEY

# 5. (Opcional) Descargar avatares de prueba
# Colocar imágenes PNG en assets/avatars/
```

## Uso

```bash
# Activar entorno
source venv/bin/activate

# Ejecutar pipeline básico
python src/pipeline.py \
  --prompt "Un guía explica cómo los romanos construyeron el Coliseo" \
  --quality high

# Con avatar personalizado
python src/pipeline.py \
  --prompt "Bienvenido a nuestro tutorial de cocina italiana" \
  --quality fast \
  --avatar assets/avatars/mi-avatar.png

# Con voz clonada (proporciona un audio de referencia)
python src/pipeline.py \
  --prompt "Explicación de física cuántica para principiantes" \
  --quality high \
  --avatar assets/avatars/host.png
```

## Parámetros

| Parámetro | Descripción | Valores |
|-----------|-------------|---------|
| `--prompt` | Texto de entrada para generar el video | requerido |
| `--quality` | Calidad del lip-sync | `none` (sin lip-sync, video+audio), `fast` (MuseTalk), `balanced` (auto), `high` (LatentSync) |
| `--avatar` | Ruta a imagen PNG de avatar | opcional |
| `--config` | Ruta al archivo de configuración YAML | default: `configs/pipeline.yaml` |

## Flujo del pipeline

```
Prompt de texto
    │
    ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│ Generador   │────▶│ Escenas      │────▶│ Audio .wav      │
│ LLM (GPT)   │     │ (JSON)       │     │ (Coqui XTTS v2) │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                  │
                            ┌─────────────────────┼─────────────────────┐
                            ▼                     ▼                     ▼
                     ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
                     │ Avatar      │      │ Video base  │      │   Referencia│
                     │  (opcional) │      │  (placeholder)│     │   facial    │
                     └──────┬──────┘      └──────┬──────┘      └──────┬──────┘
                            │                   │                     │
                            └───────────┬───────┘                     │
                                        ▼                             │
                              ┌─────────────────┐                     │
                              │  LatentSync /   │◀────────────────────┘
                              │  MuseTalk       │   (o video directo)
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │  FFmpeg         │
                              │  (compositing)  │
                              └────────┬────────┘
                                       │
                                       ▼
                               video_final.mp4
```

## Configuración avanzada

Editar `configs/pipeline.yaml`:

- `llm.provider`: Cambiar a `ollama` para usar LLM local sin API key
- `tts.speaker_wav`: Ruta a audio de referencia para clonar una voz
- `lipsync.engine`: Cambiar entre `latentsync` y `musetalk`
- `compositing.crf`: Menor valor = mayor calidad de video (18-28)

## Notas importantes

1. **LatentSync** requiere GPU NVIDIA (CUDA) — NO corre en Mac Apple Silicon
2. **MuseTalk** funciona con CPU (fallback) — viable en Mac, aunque lento
3. En Mac sin GPU NVIDIA: usa `--quality none` (video+audio sin lip-sync) o `--quality fast` (MuseTalk)
4. **Coqui TTS (XTTS v2)** licencia CPML = **uso no comercial**. Para proyectos comerciales, pide licencia a Coqui o usa un TTS con licencia comercial
5. El guion usa **Ollama local por defecto** (sin API key). Cambia `llm.provider` a `openai` si prefieres GPT
6. El speaker de voz por defecto es **"Alma María"** (español). Cambia en `configs/pipeline.yaml` o usa `speaker_wav` para clonar otra voz

## Licencia

Este proyecto integra múltiples componentes con diferentes licencias:
- LatentSync: Apache 2.0
- MuseTalk: MIT
- Coqui TTS: MPL-2.0
- FaceFusion: OpenRAIL

## Stack tecnológico

| Componente | Tecnología |
|------------|-----------|
| Guion | OpenAI GPT-4o / Ollama local |
| TTS | Coqui TTS (XTTS v2) |
| Lip-Sync | LatentSync 1.6 / MuseTalk 1.5 |
| Compositing | FFmpeg |
| Orquestación | Python 3.10+ |
