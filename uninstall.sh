#!/usr/bin/env bash
# Desinstalador de Gestor Cron & Comandos.
set -euo pipefail

APP_ID="gestor-cron-comandos"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/$APP_ID"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/$APP_ID"
BIN_DIR="$HOME/.local/bin"
DESKTOP="${XDG_DATA_HOME:-$HOME/.local/share}/applications/$APP_ID.desktop"
ICONO="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps/$APP_ID.svg"
SYSTEMD_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
CONFIG_JSON="$CONFIG_DIR/config.json"

echo "== Desinstalador de Gestor Cron & Comandos =="
echo
read -r -p "¿Eliminar también las tareas programadas y los comandos personalizados creados con la app? [s/N] " RESP
BORRAR_DATOS=0
case "$RESP" in [sS]|[sS][iI]) BORRAR_DATOS=1 ;; esac

if [ "$BORRAR_DATOS" -eq 1 ]; then
    echo "-- Eliminando tareas y comandos gestionados..."
    # tareas systemd
    if command -v systemctl >/dev/null 2>&1; then
        for t in "$SYSTEMD_DIR"/gestorcron-*.timer; do
            [ -e "$t" ] || continue
            systemctl --user disable --now "$(basename "$t")" 2>/dev/null || true
            rm -f "$t" "${t%.timer}.service"
        done
        systemctl --user daemon-reload 2>/dev/null || true
    fi
    # tareas crontab (solo las líneas etiquetadas por la app)
    if command -v crontab >/dev/null 2>&1 && crontab -l >/dev/null 2>&1; then
        crontab -l | grep -v '# gestorcron:' | crontab - || true
    fi
    # comandos personalizados: scripts y funciones fish listados en la configuración
    if [ -f "$CONFIG_JSON" ] && command -v python3 >/dev/null 2>&1; then
        python3 - "$CONFIG_JSON" <<'PYEOF'
import json, sys
from pathlib import Path
datos = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
home = Path.home()
for c in datos.get("comandos", []):
    (home / ".local/bin" / c["palabra_clave"]).unlink(missing_ok=True)
    (home / ".config/fish/functions" / (c["palabra_clave"] + ".fish")).unlink(missing_ok=True)
PYEOF
    fi
    # bloques de alias en los rc (todos los gestorcron:<id> menos el del PATH)
    for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
        [ -f "$rc" ] || continue
        python3 - "$rc" <<'PYEOF' 2>/dev/null || true
import re, sys
from pathlib import Path
rc = Path(sys.argv[1])
texto = rc.read_text(encoding="utf-8")
nuevo = re.sub(r"\n?# >>> gestorcron:(?!path)[^ ]* >>>.*?# <<< gestorcron:(?!path)[^ ]* <<<\n?",
               "\n", texto, flags=re.DOTALL)
if nuevo != texto:
    rc.write_text(nuevo, encoding="utf-8")
PYEOF
    done
    rm -rf "$CONFIG_DIR"
    echo "   Hecho."
else
    echo "-- Se conservan tareas, comandos y configuración ($CONFIG_DIR)."
fi

echo "-- Eliminando la aplicación..."
rm -f "$BIN_DIR/$APP_ID" "$DESKTOP" "$ICONO"
rm -rf "$DATA_DIR"
command -v update-desktop-database >/dev/null 2>&1 && \
    update-desktop-database "$(dirname "$DESKTOP")" 2>/dev/null || true

echo
echo "== Desinstalación completada =="
echo "   (Los bloques '# >>> gestorcron:path >>>' de tus rc no se tocan por si otros programas dependen de ~/.local/bin en el PATH.)"
if [ -f /etc/sudoers.d/gestorcron-apagado ] 2>/dev/null || sudo -n -l "$(command -v systemctl)" poweroff >/dev/null 2>&1; then
    echo "   Si autorizaste el apagado programado, la regla de sudo se elimina con:"
    echo "     sudo rm /etc/sudoers.d/gestorcron-apagado"
fi
