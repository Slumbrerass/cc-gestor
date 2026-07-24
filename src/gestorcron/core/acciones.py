"""Catálogo de tipos de acción (estilo plugin) y su compilación a shell.

Cada AccionSpec declara los campos que necesita su formulario en la GUI y una
función que compila los parámetros a un fragmento de bash. Ese fragmento es la
única fuente de verdad: se usa igual para el script de un comando personalizado,
para el job de crontab y para el ExecStart de systemd.
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import Callable

from .modelo import Accion

INTERPRETES = ["bash", "sh", "zsh", "fish", "python3"]


@dataclass
class Campo:
    clave: str
    etiqueta: str
    tipo: str = "texto"   # texto | multilinea | archivo | audio | url | interprete | segundos
    opciones: list = field(default_factory=list)
    opcional: bool = False


@dataclass
class AccionSpec:
    tipo: str
    nombre: str
    campos: list
    compilar: Callable[[dict], str]
    entorno_grafico: bool = False   # necesita DISPLAY/DBus al correr desde cron
    peligrosa: bool = False         # pedir confirmación antes de probar/ejecutar a mano


REGISTRO: dict[str, AccionSpec] = {}


def registrar(spec: AccionSpec) -> None:
    REGISTRO[spec.tipo] = spec


def _q(v) -> str:
    return shlex.quote(str(v))


# Al ejecutarse desde cron no hay entorno gráfico ni bus de sesión; este
# preámbulo reconstruye lo mínimo para que audio, xdg-open y notify-send
# funcionen igual que en una terminal de la sesión.
PREAMBULO_ENTORNO = """\
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
if [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ] && [ -S "$XDG_RUNTIME_DIR/bus" ]; then
    export DBUS_SESSION_BUS_ADDRESS="unix:path=$XDG_RUNTIME_DIR/bus"
fi
if [ -z "${WAYLAND_DISPLAY:-}" ] && [ -z "${DISPLAY:-}" ]; then
    for _s in "$XDG_RUNTIME_DIR"/wayland-*; do
        case "$_s" in *.lock) ;; *) [ -e "$_s" ] && export WAYLAND_DISPLAY="$(basename "$_s")" && break ;; esac
    done
    [ -z "${WAYLAND_DISPLAY:-}" ] && export DISPLAY="${DISPLAY:-:0}"
fi"""


def _c_mostrar_texto(p: dict) -> str:
    return f"printf '%s\\n' {_q(p['texto'])}"


def _c_reproducir_audio(p: dict) -> str:
    # duración máxima en segundos; 0 o vacío = reproducir completo
    dur = p.get("duracion") or 0
    try:
        dur = int(dur)
    except (TypeError, ValueError):
        raise ValueError(f"Duración de audio inválida: {p['duracion']!r}")
    if dur < 0:
        raise ValueError("La duración del audio no puede ser negativa")
    pre = f"timeout {dur} " if dur else ""
    return f"""_f={_q(p['archivo'])}
if command -v ffplay >/dev/null 2>&1; then
    {pre}ffplay -nodisp -autoexit -loglevel quiet -- "$_f"
elif command -v mpg123 >/dev/null 2>&1 && case "$_f" in *.mp3|*.MP3) true ;; *) false ;; esac; then
    {pre}mpg123 -q -- "$_f"
elif command -v paplay >/dev/null 2>&1; then
    {pre}paplay -- "$_f"
elif command -v aplay >/dev/null 2>&1; then
    {pre}aplay -q -- "$_f"
else
    echo 'gestorcron: no se encontró ningún reproductor de audio (ffplay/mpg123/paplay/aplay)' >&2
    exit 1
fi"""


def _c_abrir_archivo(p: dict) -> str:
    return f"nohup xdg-open {_q(p['ruta'])} >/dev/null 2>&1 &"


def _c_abrir_url(p: dict) -> str:
    return f"nohup xdg-open {_q(p['url'])} >/dev/null 2>&1 &"


def _c_ejecutar_comando(p: dict) -> str:
    interprete = p.get("interprete", "bash")
    if interprete not in INTERPRETES:
        raise ValueError(f"Intérprete no soportado: {interprete}")
    return f"{interprete} -c {_q(p['comando'])}"


def _c_ejecutar_script(p: dict) -> str:
    return _q(p["ruta"])


def _c_apagar_pc(p: dict) -> str:
    """Apaga el equipo; con hora de encendido usa rtcwake para que la placa
    lo despierte sola. Requiere la regla sudoers que instala la pestaña
    Ajustes ("Autorizar apagado programado")."""
    aviso = """echo 'gestorcron: apagado no autorizado. Autorízalo en Ajustes de Gestor Cron & Comandos.' >&2
    command -v notify-send >/dev/null 2>&1 && \\
        notify-send -u critical -- 'Gestor Cron & Comandos' \\
            'No se pudo apagar el equipo: falta autorización (pestaña Ajustes)'
    exit 1"""
    hora = str(p.get("hora_encendido", "") or "").strip()
    if not hora:
        return f"""if ! sudo -n systemctl poweroff; then
    {aviso}
fi"""
    if not re.fullmatch(r"([01]?\d|2[0-3]):[0-5]\d", hora):
        raise ValueError(f"Hora de encendido inválida (usa HH:MM): {hora}")
    # rtcwake falla si la hora ya pasó hoy; en ese caso se programa para mañana
    return f"""_t=$(date -d {_q(hora)} +%s)
[ "$_t" -le "$(date +%s)" ] && _t=$((_t + 86400))
if ! sudo -n rtcwake -m off -t "$_t"; then
    {aviso}
fi"""


def _c_notificacion(p: dict) -> str:
    t, c = _q(p["titulo"]), _q(p.get("cuerpo", ""))
    return f"""if command -v notify-send >/dev/null 2>&1; then
    notify-send -- {t} {c}
else
    printf '%s: %s\\n' {t} {c}
fi"""


registrar(AccionSpec("mostrar_texto", "Mostrar texto",
                     [Campo("texto", "Texto a mostrar")], _c_mostrar_texto))
registrar(AccionSpec("reproducir_audio", "Reproducir audio",
                     [Campo("archivo", "Archivo de audio", "audio"),
                      Campo("duracion", "Duración máxima", "segundos", opcional=True)],
                     _c_reproducir_audio, entorno_grafico=True))
registrar(AccionSpec("abrir_archivo_o_imagen", "Abrir archivo o imagen",
                     [Campo("ruta", "Archivo a abrir", "archivo")], _c_abrir_archivo, entorno_grafico=True))
registrar(AccionSpec("abrir_url", "Abrir URL",
                     [Campo("url", "URL", "url")], _c_abrir_url, entorno_grafico=True))
registrar(AccionSpec("ejecutar_comando", "Ejecutar comando",
                     [Campo("comando", "Comando", "multilinea"),
                      Campo("interprete", "Intérprete", "interprete", INTERPRETES)], _c_ejecutar_comando))
registrar(AccionSpec("ejecutar_script", "Ejecutar script existente",
                     [Campo("ruta", "Ruta del script", "archivo")], _c_ejecutar_script))
registrar(AccionSpec("apagar_pc", "Apagar el equipo",
                     [Campo("hora_encendido", "Encender a las (HH:MM, opcional)", opcional=True)],
                     _c_apagar_pc, entorno_grafico=True, peligrosa=True))
registrar(AccionSpec("notificacion_escritorio", "Notificación de escritorio",
                     [Campo("titulo", "Título"), Campo("cuerpo", "Mensaje", opcional=True)],
                     _c_notificacion, entorno_grafico=True))


def generar_script(accion: Accion, con_entorno: bool = False) -> str:
    """Compila una acción a un script bash completo y autocontenido."""
    spec = REGISTRO[accion.tipo]
    lineas = ["#!/usr/bin/env bash", "# Generado por Gestor Cron & Comandos", "set -u", ""]
    if con_entorno or spec.entorno_grafico:
        lineas += [PREAMBULO_ENTORNO, ""]
    lineas.append(spec.compilar(accion.params))
    return "\n".join(lineas) + "\n"


def resumen(accion: Accion) -> str:
    """Descripción corta de una acción para las listas de la GUI."""
    spec = REGISTRO.get(accion.tipo)
    if spec is None:
        return accion.tipo
    detalle = next(iter(accion.params.values()), "")
    detalle = str(detalle).replace("\n", " ")
    if len(detalle) > 48:
        detalle = detalle[:45] + "..."
    return f"{spec.nombre}: {detalle}" if detalle else spec.nombre
