#!/bin/bash
# Compila ~/Desktop/generador-video.app (applet de AppleScript + icono propio).
# Uso: bash ~/proyectos/ai-video-pipeline/app/build-app.sh
set -e
BASE="$HOME/proyectos/ai-video-pipeline"
APP="$HOME/Desktop/generador-video.app"
WORK="$(mktemp -d)"

# 1) Compilar el applet (osacompile crea el bundle completo con su cargador)
osacompile -o "$WORK/app.app" "$BASE/app/generador-video.applescript"

# 2) Moverlo al destino final
rm -rf "$APP"
mv "$WORK/app.app" "$APP"

# 3) Icono propio: PNG 1024 (PIL) → sips (todas las tallas) → iconutil
ICONPNG="$WORK/icon.png"
ICONPY=""
for PY in "$BASE/venv/bin/python" /opt/homebrew/bin/python3.12 /usr/bin/python3; do
    if "$PY" -c "import PIL" 2>/dev/null; then
        ICONPY="$PY"
        break
    fi
done
if [ -z "$ICONPY" ]; then
    echo "No encuentro ningún python con PIL para el icono" >&2
    exit 1
fi
"$ICONPY" "$BASE/app/make-icon.py" "$ICONPNG"

ICONSET="$WORK/app.iconset"
mkdir -p "$ICONSET"
gen() { sips -z "$1" "$1" "$ICONPNG" --out "$ICONSET/$2" >/dev/null; }
gen 16 icon_16x16.png
gen 32 "icon_16x16@2x.png"
gen 32 icon_32x32.png
gen 64 "icon_32x32@2x.png"
gen 128 icon_128x128.png
gen 256 "icon_128x128@2x.png"
gen 256 icon_256x256.png
gen 512 "icon_256x256@2x.png"
gen 512 icon_512x512.png
gen 1024 "icon_512x512@2x.png"
iconutil -c icns "$ICONSET" -o "$APP/Contents/Resources/icon.icns"

# 4) Nombre visible
plutil -replace CFBundleName -string "Generador de Video" "$APP/Contents/Info.plist"
plutil -replace CFBundleDisplayName -string "Generador de Video" "$APP/Contents/Info.plist"
plutil -replace CFBundleShortVersionString -string 1.1 "$APP/Contents/Info.plist"

rm -rf "$WORK"
echo "App lista: $APP"
