"""Persistencia de la configuración en JSON (~/.config/gestor-cron-comandos/)."""

from __future__ import annotations

import json
from pathlib import Path

from .. import rutas
from .modelo import Comando, Tarea


class Almacen:
    def __init__(self, ruta: Path | None = None):
        self.ruta = ruta or (rutas.config_dir() / "config.json")
        self.tareas: list[Tarea] = []
        self.comandos: list[Comando] = []
        self.preferencias: dict = {}   # tema_oscuro, tamano_fuente, …
        self.cargar()

    def cargar(self) -> None:
        if not self.ruta.exists():
            return
        datos = json.loads(self.ruta.read_text(encoding="utf-8"))
        self.tareas = [Tarea.de_dict(d) for d in datos.get("tareas", [])]
        self.comandos = [Comando.de_dict(d) for d in datos.get("comandos", [])]
        self.preferencias = dict(datos.get("preferencias", {}))

    def guardar(self) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        datos = {
            "tareas": [t.a_dict() for t in self.tareas],
            "comandos": [c.a_dict() for c in self.comandos],
            "preferencias": dict(self.preferencias),
        }
        tmp = self.ruta.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.ruta)

    # --- tareas ---
    def obtener_tarea(self, tarea_id: str) -> Tarea | None:
        return next((t for t in self.tareas if t.id == tarea_id), None)

    def reemplazar_tarea(self, tarea: Tarea) -> None:
        self.tareas = [t for t in self.tareas if t.id != tarea.id]
        self.tareas.append(tarea)

    def quitar_tarea(self, tarea_id: str) -> None:
        self.tareas = [t for t in self.tareas if t.id != tarea_id]

    # --- comandos ---
    def obtener_comando(self, comando_id: str) -> Comando | None:
        return next((c for c in self.comandos if c.id == comando_id), None)

    def reemplazar_comando(self, comando: Comando) -> None:
        self.comandos = [c for c in self.comandos if c.id != comando.id]
        self.comandos.append(comando)

    def quitar_comando(self, comando_id: str) -> None:
        self.comandos = [c for c in self.comandos if c.id != comando_id]
