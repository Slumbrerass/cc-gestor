#!/usr/bin/env bash
# Instalador de Gestor Cron & Comandos para cualquier distro Linux.
# Idempotente: se puede re-ejecutar para actualizar sin duplicar nada.
# No instala paquetes del sistema por su cuenta: si falta algo, lo detecta y
# sugiere el comando exacto para tu distro.
set -euo pipefail

APP_ID="gestor-cron-comandos"
ORIGEN="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/$APP_ID"
VENV="$DATA_DIR/venv"
APP_DIR="$DATA_DIR/app"
BIN_DIR="$HOME/.local/bin"
LANZADOR="$BIN_DIR/$APP_ID"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"

ok()   { printf '  \033[32m✔\033[0m %s\n' "$1"; }
aviso(){ printf '  \033[33m⚠\033[0m %s\n' "$1"; }
fallo(){ printf '  \033[31m✘\033[0m %s\n' "$1"; }

detectar_gestor_paquetes() {
    for g in pacman apt dnf zypper apk; do
        command -v "$g" >/dev/null 2>&1 && { echo "$g"; return; }
    done
    echo ""
}

sugerir_instalacion() {
    local paquete_generico="$1"
    case "$(detectar_gestor_paquetes)" in
        pacman) echo "sudo pacman -S $paquete_generico" ;;
        apt)    echo "sudo apt install $paquete_generico" ;;
        dnf)    echo "sudo dnf install $paquete_generico" ;;
        zypper) echo "sudo zypper install $paquete_generico" ;;
        apk)    echo "sudo apk add $paquete_generico" ;;
        *)      echo "instala '$paquete_generico' con el gestor de paquetes de tu distro" ;;
    esac
}

echo "== Instalador de Gestor Cron & Comandos =="
echo
echo "[1/7] Comprobando Python 3.10+..."
if ! command -v python3 >/dev/null 2>&1; then
    fallo "No se encontró python3."
    echo "     Instálalo con: $(sugerir_instalacion python3)"
    exit 1
fi
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
    fallo "Se necesita Python 3.10 o superior (tienes $(python3 --version))."
    exit 1
fi
ok "$(python3 --version)"

echo "[2/7] Comprobando el módulo venv..."
if ! python3 -m venv --help >/dev/null 2>&1; then
    fallo "python3 -m venv no funciona."
    echo "     En Debian/Ubuntu suele faltar el paquete: $(sugerir_instalacion python3-venv)"
    exit 1
fi
ok "venv disponible"

echo "[3/7] Creando entorno virtual e instalando dependencias (PySide6, python-crontab)..."
mkdir -p "$DATA_DIR"
if [ ! -x "$VENV/bin/python" ]; then
    python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$ORIGEN/requirements.txt"
ok "Dependencias instaladas en $VENV"

echo "[4/7] Copiando la aplicación..."
rm -rf "$APP_DIR"
mkdir -p "$APP_DIR"
cp -r "$ORIGEN/src/gestorcron" "$APP_DIR/"
cp "$ORIGEN/uninstall.sh" "$DATA_DIR/" 2>/dev/null || true
chmod +x "$DATA_DIR/uninstall.sh" 2>/dev/null || true
ok "Código en $APP_DIR"

echo "[5/7] Creando lanzador y entrada de menú..."
mkdir -p "$BIN_DIR"
cat > "$LANZADOR" <<EOF
#!/usr/bin/env bash
export PYTHONPATH="$APP_DIR"
exec "$VENV/bin/python" -m gestorcron.main "\$@"
EOF
chmod +x "$LANZADOR"

mkdir -p "$ICON_DIR" "$DESKTOP_DIR"
cp "$ORIGEN/src/gestorcron/recursos/icono.svg" "$ICON_DIR/$APP_ID.svg"
cat > "$DESKTOP_DIR/$APP_ID.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Gestor Cron & Comandos
Comment=Crea tareas programadas y comandos de shell personalizados
Exec=$LANZADOR
Icon=$APP_ID
Terminal=false
Categories=Utility;System;
Keywords=cron;alias;comandos;tareas;
EOF
command -v update-desktop-database >/dev/null 2>&1 && \
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
ok "Lanzador: $LANZADOR"
ok "Menú de aplicaciones: $DESKTOP_DIR/$APP_ID.desktop"

echo "[6/7] Comprobando que ~/.local/bin está en el PATH..."
case ":$PATH:" in
    *":$BIN_DIR:"*) ok "Ya está en el PATH" ;;
    *)
        BLOQUE_INI="# >>> gestorcron:path >>>"
        BLOQUE_FIN="# <<< gestorcron:path <<<"
        for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
            shell_bin="$(basename "$rc" | sed 's/^\.//; s/rc$//')"
            command -v "$shell_bin" >/dev/null 2>&1 || continue
            grep -qF "$BLOQUE_INI" "$rc" 2>/dev/null && continue
            printf '\n%s\ncase ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac\n%s\n' \
                "$BLOQUE_INI" "$BLOQUE_FIN" >> "$rc"
            ok "PATH añadido a $rc"
        done
        if command -v fish >/dev/null 2>&1; then
            FISH_CONF="${XDG_CONFIG_HOME:-$HOME/.config}/fish/config.fish"
            if ! grep -qF "$BLOQUE_INI" "$FISH_CONF" 2>/dev/null; then
                mkdir -p "$(dirname "$FISH_CONF")"
                printf '\n%s\nfish_add_path -g ~/.local/bin\n%s\n' \
                    "$BLOQUE_INI" "$BLOQUE_FIN" >> "$FISH_CONF"
                ok "PATH añadido a config.fish"
            fi
        fi
        aviso "Abre una terminal nueva para que el PATH haga efecto."
        ;;
esac

echo "[7/7] Comprobando backends de tareas programadas..."
TIENE_BACKEND=0
if command -v crontab >/dev/null 2>&1; then
    ok "crontab disponible"
    TIENE_BACKEND=1
else
    aviso "No hay 'crontab'. Para usar el backend clásico: $(sugerir_instalacion cronie)"
    aviso "(en Debian/Ubuntu el paquete se llama 'cron')"
fi
if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
    ok "systemd user timers disponibles"
    TIENE_BACKEND=1
else
    aviso "systemd de usuario no disponible."
fi
[ "$TIENE_BACKEND" -eq 0 ] && aviso "Sin ningún backend las tareas programadas no funcionarán (los comandos personalizados sí)."
if command -v timeout >/dev/null 2>&1; then
    ok "timeout (coreutils) disponible — el límite de duración de 'Reproducir audio' funcionará"
else
    aviso "No hay 'timeout' (coreutils): el límite de duración de 'Reproducir audio' no tendrá efecto. Instálalo con: $(sugerir_instalacion coreutils)"
fi
if command -v rtcwake >/dev/null 2>&1; then
    ok "rtcwake disponible — la acción 'Apagar el equipo' podrá programar el encendido"
else
    aviso "No hay 'rtcwake' (util-linux): 'Apagar el equipo' apagará pero no podrá programar el encendido."
fi
command -v pkexec >/dev/null 2>&1 || \
    aviso "No hay 'pkexec' (polkit): el botón 'Autorizar…' de Ajustes te dará instrucciones manuales para el apagado programado."

echo
echo "== Instalación completada =="
echo "  Lánzalo con:  $APP_ID"
echo "  o búscalo como 'Gestor Cron & Comandos' en el menú de aplicaciones."
echo "  Para desinstalar:  bash $DATA_DIR/uninstall.sh"
