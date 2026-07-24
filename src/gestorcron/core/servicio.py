"""Capa de orquestación: une almacén, backends y compilador de acciones.

La GUI solo habla con Gestor; toda la lógica es utilizable también sin Qt
(tests, futura CLI).
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from .. import rutas
from . import horarios
from .acciones import generar_script
from .almacen import Almacen
from .comandos_backend import ComandosBackend
from .cron_backend import CrontabBackend
from .modelo import Accion, Comando, Tarea
from .systemd_backend import SystemdBackend


class Gestor:
    def __init__(self, almacen: Almacen | None = None,
                 backend_crontab: CrontabBackend | None = None,
                 backend_systemd: SystemdBackend | None = None):
        self.almacen = almacen or Almacen()
        self.backends = {
            "crontab": backend_crontab or CrontabBackend(),
            "systemd": backend_systemd or SystemdBackend(),
        }
        self.comandos_backend = ComandosBackend()

    def backends_disponibles(self) -> dict[str, bool]:
        return {n: b.disponible() for n, b in self.backends.items()}

    # ---------- tareas ----------
    def _ruta_job(self, tarea_id: str) -> Path:
        return rutas.jobs_dir() / f"{tarea_id}.sh"

    def guardar_tarea(self, tarea: Tarea) -> None:
        backend = self.backends.get(tarea.backend)
        if backend is None:
            raise ValueError(f"Backend desconocido: {tarea.backend}")
        if not backend.disponible():
            raise RuntimeError(f"El backend '{tarea.backend}' no está disponible en este sistema")
        cron_expr, oncalendar = horarios.construir(tarea.horario)

        # si la tarea existía con otro backend, retirar los artefactos antiguos
        previa = self.almacen.obtener_tarea(tarea.id)
        if previa and previa.backend != tarea.backend:
            self.backends[previa.backend].eliminar(tarea.id)

        ruta = self._ruta_job(tarea.id)
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(generar_script(tarea.accion, con_entorno=True), encoding="utf-8")
        ruta.chmod(0o755)

        backend.crear(tarea, ruta, cron_expr=cron_expr, oncalendar=oncalendar)
        self.almacen.reemplazar_tarea(tarea)
        self.almacen.guardar()

    def eliminar_tarea(self, tarea_id: str) -> None:
        tarea = self.almacen.obtener_tarea(tarea_id)
        if tarea is None:
            return
        self.backends[tarea.backend].eliminar(tarea_id)
        self._ruta_job(tarea_id).unlink(missing_ok=True)
        self.almacen.quitar_tarea(tarea_id)
        self.almacen.guardar()

    def alternar_tarea(self, tarea_id: str, activo: bool) -> None:
        tarea = self.almacen.obtener_tarea(tarea_id)
        if tarea is None:
            return
        self.backends[tarea.backend].habilitar(tarea_id, activo)
        tarea.habilitada = activo
        self.almacen.reemplazar_tarea(tarea)
        self.almacen.guardar()

    def ejecutar_tarea_ahora(self, tarea_id: str) -> None:
        subprocess.Popen(["bash", str(self._ruta_job(tarea_id))],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)

    # ---------- comandos ----------
    def guardar_comando(self, comando: Comando) -> Path:
        previo = self.almacen.obtener_comando(comando.id)
        if previo is not None:
            self.comandos_backend.eliminar(previo)
        ruta = self.comandos_backend.crear(comando)
        self.almacen.reemplazar_comando(comando)
        self.almacen.guardar()
        return ruta

    def eliminar_comando(self, comando_id: str) -> None:
        comando = self.almacen.obtener_comando(comando_id)
        if comando is None:
            return
        self.comandos_backend.eliminar(comando)
        self.almacen.quitar_comando(comando_id)
        self.almacen.guardar()

    # ---------- utilidades ----------
    @staticmethod
    def probar_accion(accion: Accion) -> None:
        """Ejecuta la acción una vez, en segundo plano, sin guardar nada."""
        with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False,
                                         prefix="gestorcron-prueba-") as f:
            f.write(generar_script(accion))
            ruta = f.name
        subprocess.Popen(["bash", ruta],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
