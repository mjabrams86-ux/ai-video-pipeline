-- Generador de Video IA — app de un solo clic (macOS)
-- Pide la idea, elige el tipo de video, arranca el pipeline y abre el resultado.

set base to (POSIX path of (path to home folder)) & "proyectos/ai-video-pipeline"

-- 1) La idea
set idea to text returned of (display dialog "Generador de Video IA" & return & "¿Qué debe decir tu video?" default answer "Bienvenidos a nuestra empresa: un video corto que explica quiénes somos, qué hacemos y por qué somos diferentes" buttons {"Cancelar", "Continuar"} default button 2 with title "Generador de Video IA")
if (count of idea) < 8 then
    display alert "Idea demasiado corta" message "Escribe la idea del video con más detalle (mínimo 8 caracteres)."
    return
end if

-- 2) Tipo de video
set useAI to true
tell (display dialog "¿Qué tipo de video quieres?" buttons {"Video con IA (escenas reales)", "Cara fija + voz (rápido)"} default button 1 with title "Generador de Video IA")
    set useAI to (button returned is "Video con IA (escenas reales)")
end tell

set qualityFlag to ""
set avatarFlag to ""
if useAI then
    set qualityFlag to " --quality agvideo"
else
    set qualityFlag to " --quality none"
    set chosePhoto to false
    tell (display dialog "¿Qué cara mostrará el video?" buttons {"Usar la cara incluida", "Elegir una foto"} default button 1 with title "Generador de Video IA")
        set chosePhoto to (button returned is "Elegir una foto")
    end tell
    if chosePhoto then
        set avatarPath to POSIX path of (choose file with prompt "Elige una foto de una persona (de frente, bien iluminada)")
        set avatarFlag to " --avatar " & quoted form of avatarPath
    end if
end if

-- 3) Arrancar el pipeline en segundo plano, con marcador de fin
--    (la clave de Agnes está en el .env del proyecto: no hay que hacer nada)
set cmd to "rm -f /tmp/generador-video.status; ( cd " & quoted form of base & " && COQUI_TOS_AGREED=1 venv/bin/python src/pipeline.py --prompt " & quoted form of idea & " --config configs/pipeline.yaml" & qualityFlag & avatarFlag & " >/tmp/generador-video.log 2>&1; if [ $? -eq 0 ]; then echo OK > /tmp/generador-video.status; else echo FAIL > /tmp/generador-video.status; fi ) &"
do shell script cmd

-- 4) Esperar al pipeline (saltos de 5 s; máx. 60 min; el video IA tarda más)
set iters to 0
repeat
    do shell script "sleep 5"
    set iters to iters + 1
    set status to ""
    try
        set status to do shell script "cat /tmp/generador-video.status 2>/dev/null"
    end try
    if status contains "OK" or status contains "FAIL" then
        exit repeat
    end if
    if iters > 720 then
        display alert "Demasiado tiempo" message "Lleva más de 60 minutos. Mira /tmp/generador-video.log para ver qué pasó."
        return
    end if
end repeat

-- 5) Resultado
if status contains "OK" then
    set latestFile to do shell script "ls -t " & quoted form of (base & "/output/video_final_*.mp4") & " | head -1"
    do shell script "open " & quoted form of latestFile
    display alert "¡Video listo!" message "Tu video se acaba de abrir. También está guardado en: " & base & "/output/"
else
    set logTail to do shell script "tail -5 /tmp/generador-video.log 2>/dev/null"
    display alert "Algo ha fallado" message logTail & return & return & "Detalle completo en /tmp/generador-video.log"
end if
