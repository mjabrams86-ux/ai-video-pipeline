-- Generador de Video IA — app de un solo clic (macOS)
-- Pide la idea, arranca el pipeline en segundo plano y abre el video resultante.

set base to (POSIX path of (path to home folder)) & "proyectos/ai-video-pipeline"

-- 1) La idea
set idea to text returned of (display dialog "Generador de Video IA" & return & "¿Qué debe decir tu video?" default answer "Bienvenidos a nuestra empresa: un video corto que explica quiénes somos, qué hacemos y por qué somos diferentes" buttons {"Cancelar", "Continuar"} default button 2 with title "Generador de Video IA")
if (count of idea) < 8 then
    display alert "Idea demasiado corta" message "Escribe la idea del video con más detalle (mínimo 8 caracteres)."
    return
end if

-- 2) El avatar
set chosePhoto to false
tell (display dialog "¿Qué cara mostrará el video?" buttons {"Usar la cara incluida", "Elegir una foto"} default button 1 with title "Generador de Video IA")
    set chosePhoto to (button returned is "Elegir una foto")
end tell

set avatarFlag to ""
if chosePhoto then
    set avatarPath to POSIX path of (choose file with prompt "Elige una foto de una persona (de frente, bien iluminada)")
    set avatarFlag to " --avatar " & quoted form of avatarPath
end if

-- 3) Ollama (el escritor del guion) debe estar activo
do shell script "curl -s --max-time 2 http://localhost:11434/api/version >/dev/null 2>&1 || (open -a Ollama 2>/dev/null || (nohup ollama serve >/dev/null 2>&1 &))"

-- 4) Arrancar el pipeline en segundo plano, con marcador de fin
set cmd to "rm -f /tmp/generador-video.status; ( cd " & quoted form of base & " && COQUI_TOS_AGREED=1 venv/bin/python src/pipeline.py --prompt " & quoted form of idea & " --quality none --config configs/pipeline.yaml" & avatarFlag & " >/tmp/generador-video.log 2>&1; if [ $? -eq 0 ]; then echo OK > /tmp/generador-video.status; else echo FAIL > /tmp/generador-video.status; fi ) &"
do shell script cmd

-- 5) Esperar al pipeline (ventas de 5 s; máx. 30 min)
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
    if iters > 360 then
        display alert "Demasiado tiempo" message "Lleva más de 30 minutos. Mira /tmp/generador-video.log para ver qué pasó."
        return
    end if
end repeat

-- 6) Resultado
if status contains "OK" then
    set latestFile to do shell script "ls -t " & quoted form of (base & "/output/video_final_*.mp4") & " | head -1"
    do shell script "open " & quoted form of latestFile
    display alert "¡Video listo!" message "Tu video se acaba de abrir. También está guardado en: " & base & "/output/"
else
    set logTail to do shell script "tail -5 /tmp/generador-video.log 2>/dev/null"
    display alert "Algo ha fallado" message logTail & return & return & "Detalle completo en /tmp/generador-video.log"
end if
