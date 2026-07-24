"""Backend de tareas sobre el crontab clásico del usuario (vía python-crontab).

Cada entrada gestionada lleva el comentario "gestorcron:<id>", de modo que solo
se tocan las líneas creadas por esta app y nunca el resto del crontab del usuario.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ETIQUETA = "gestorcron:"


class CrontabBackend:
    nombre = "crontab"

    def __init__(self, tabfile: str | None = None):
        # tabfile permite operar sobre un archivo en vez del crontab real (tests)
        self.tabfile = tabfile

    def disponible(self) -> bool:
        return self.tabfile is not None or shutil.which("crontab") is not None

    def _abrir(self):
        from crontab import CronTab
        if self.tabfile is not None:
            return CronTab(tabfile=self.tabfile)
        return CronTab(user=True)

    def crear(self, tarea, ruta_script: Path, cron_expr: str, oncalendar: str = "") -> None:
        tab = self._abrir()
        tab.remove_all(comment=f"{ETIQUETA}{tarea.id}")
        job = tab.new(command=str(ruta_script), comment=f"{ETIQUETA}{tarea.id}")
        job.setall(cron_expr)
        job.enable(tarea.habilitada)
        tab.write()

    def eliminar(self, tarea_id: str) -> None:
        tab = self._abrir()
        tab.remove_all(comment=f"{ETIQUETA}{tarea_id}")
        tab.write()

    def habilitar(self, tarea_id: str, activo: bool) -> None:
        tab = self._abrir()
        for job in tab.find_comment(f"{ETIQUETA}{tarea_id}"):
            job.enable(activo)
        tab.write()

    def listar_ids(self) -> list[str]:
        tab = self._abrir()
        return [j.comment[len(ETIQUETA):] for j in tab
                if j.comment and j.comment.startswith(ETIQUETA)]
