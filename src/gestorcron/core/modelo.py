"""Modelo de datos: Acción, Tarea programada y Comando personalizado."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


def nuevo_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class Accion:
    tipo: str
    params: dict = field(default_factory=dict)

    def a_dict(self) -> dict:
        return {"tipo": self.tipo, "params": dict(self.params)}

    @staticmethod
    def de_dict(d: dict) -> "Accion":
        return Accion(tipo=d["tipo"], params=dict(d.get("params", {})))


@dataclass
class Tarea:
    nombre: str
    backend: str          # "crontab" | "systemd"
    horario: dict         # ver core.horarios
    accion: Accion
    habilitada: bool = True
    id: str = field(default_factory=nuevo_id)

    def a_dict(self) -> dict:
        return {
            "id": self.id,
            "nombre": self.nombre,
            "backend": self.backend,
            "horario": dict(self.horario),
            "accion": self.accion.a_dict(),
            "habilitada": self.habilitada,
        }

    @staticmethod
    def de_dict(d: dict) -> "Tarea":
        return Tarea(
            id=d["id"],
            nombre=d["nombre"],
            backend=d["backend"],
            horario=dict(d["horario"]),
            accion=Accion.de_dict(d["accion"]),
            habilitada=bool(d.get("habilitada", True)),
        )


@dataclass
class Comando:
    palabra_clave: str
    shells_destino: list
    accion: Accion
    crear_alias: bool = False
    id: str = field(default_factory=nuevo_id)

    def a_dict(self) -> dict:
        return {
            "id": self.id,
            "palabra_clave": self.palabra_clave,
            "shells_destino": list(self.shells_destino),
            "accion": self.accion.a_dict(),
            "crear_alias": self.crear_alias,
        }

    @staticmethod
    def de_dict(d: dict) -> "Comando":
        return Comando(
            id=d["id"],
            palabra_clave=d["palabra_clave"],
            shells_destino=list(d.get("shells_destino", [])),
            accion=Accion.de_dict(d["accion"]),
            crear_alias=bool(d.get("crear_alias", False)),
        )
