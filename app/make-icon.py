#!/usr/bin/env python3
"""Genera el PNG (1024x1024) del icono: gradiente + botón de play + ondas de audio."""
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def _resample():
    try:
        return Image.Resampling.BILINEAR
    except AttributeError:
        return Image.BILINEAR


def draw_icon(size: int = 1024) -> Image.Image:
    # Fondo: gradiente vertical púrpura → azul
    top = (88, 66, 255)
    bottom = (0, 178, 235)
    col = Image.new("RGB", (1, size))
    for y in range(size):
        t = y / max(size - 1, 1)
        col.putpixel((0, y), tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    grad = col.resize((size, size), _resample()).convert("RGBA")

    # Esquinas redondeadas (estilo icono macOS)
    radius = int(size * 0.225)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(grad, (0, 0), mask)
    out.putalpha(mask)

    d = ImageDraw.Draw(out)
    # Círculo blanco (botón de play)
    cx, cy = size // 2, int(size * 0.44)
    cr = int(size * 0.24)
    d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(255, 255, 255, 235))
    # Triángulo de play
    tw, th = int(size * 0.15), int(size * 0.20)
    d.polygon([
        (cx - tw // 2 + int(size * 0.02), cy - th // 2),
        (cx - tw // 2 + int(size * 0.02), cy + th // 2),
        (cx + tw, cy),
    ], fill=(30, 40, 90, 255))
    # Ondas de audio (3 barras blancas)
    bw = int(size * 0.05)
    gap = int(size * 0.11)
    by = int(size * 0.80)
    total = 3 * bw + 2 * gap
    x_start = (size - total) // 2
    for i, h in enumerate([0.14, 0.22, 0.10]):
        x0 = x_start + i * (bw + gap)
        bh = int(size * h)
        y0 = by - bh // 2
        d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=bw // 2,
                            fill=(255, 255, 255, 220))
    return out


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("icon.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    draw_icon(1024).save(out)
    print(f"PNG del icono creado: {out}")


if __name__ == "__main__":
    main()
