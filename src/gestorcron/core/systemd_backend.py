"""Backend de tareas sobre systemd user timers (~/.config/systemd/user)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .. import rutas

PREFIJO = "gestorcron-"


def generar_units(nombre: str, ruta_script: Path, oncalendar: str) -> tuple[str, str]:
    """Devuelve (contenido_service, contenido_timer). Función pura, testeable."""
    service = f"""[Unit]
Description=Gestor Cron & Comandos: {nombre}

[Service]
Type=oneshot
ExecStart={ruta_script}
"""
    timer = f"""[Unit]
Description=Gestor Cron & Comandos (timer): {nombre}

[Timer]
OnCalendar={oncalendar}

[Install]
WantedBy=timers.target
"""
    return service, timer


class SystemdBackend:
    nombre = "systemd"

    def disponible(self) -> bool:
        if shutil.which("systemctl") is None:
            return False
        r = self._systemctl("show-environment", check=False)
        return r.returncode == 0

    def _systemctl(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        r = subprocess.run(["systemctl", "--user", *args],
                           capture_output=True, text=True)
        if check and r.returncode != 0:
            raise RuntimeError(f"systemctl --user {' '.join(args)} falló: {r.stderr.strip()}")
        return r

    def _base(self, tarea_id: str) -> str:
        return f"{PREFIJO}{tarea_id}"

    def crear(self, tarea, ruta_script: Path, cron_expr: str = "", oncalendar: str = "") -> None:
        if not oncalendar:
            raise ValueError("El backend systemd necesita una expresión OnCalendar")
        d = rutas.systemd_user_dir()
        d.mkdir(parents=True, exist_ok=True)
        service, timer = generar_units(tarea.nombre, ruta_script, oncalendar)
        base = self._base(tarea.id)
        (d / f"{base}.service").write_text(service, encoding="utf-8")
        (d / f"{base}.timer").write_text(timer, encoding="utf-8")
        self._systemctl("daemon-reload")
        if tarea.habilitada:
            self._systemctl("enable", "--now", f"{base}.timer")
        else:
            self._systemctl("disable", "--now", f"{base}.timer", check=False)

    def eliminar(self, tarea_id: str) -> None:
        base = self._base(tarea_id)
        self._systemctl("disable", "--now", f"{base}.timer", check=False)
        d = rutas.systemd_user_dir()
        for suf in (".timer", ".service"):
            (d / f"{base}{suf}").unlink(missing_ok=True)
        self._systemctl("daemon-reload", check=False)

    def habilitar(self, tarea_id: str, activo: bool) -> None:
        base = self._base(tarea_id)
        if activo:
            self._systemctl("enable", "--now", f"{base}.timer")
        else:
            self._systemctl("disable", "--now", f"{base}.timer", check=False)

    def ejecutar_ahora(self, tarea_id: str) -> None:
        self._systemctl("start", f"{self._base(tarea_id)}.service")

    def listar_ids(self) -> list[str]:
        d = rutas.systemd_user_dir()
        return [p.stem[len(PREFIJO):] for p in d.glob(f"{PREFIJO}*.timer")]
