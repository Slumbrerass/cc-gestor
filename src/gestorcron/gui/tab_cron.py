"""Pestaña de tareas programadas."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from ..core import horarios
from ..core.acciones import REGISTRO, resumen
from .dialogs.nueva_tarea import DialogoTarea

COLUMNAS = ["Nombre", "Horario", "Backend", "Acción", "Estado"]


class TabCron(QWidget):
    def __init__(self, gestor, parent=None):
        super().__init__(parent)
        self.gestor = gestor
        capa = QVBoxLayout(self)

        self.tabla = QTableWidget(0, len(COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(COLUMNAS)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SingleSelection)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.doubleClicked.connect(lambda _: self._editar())
        capa.addWidget(self.tabla)

        fila = QHBoxLayout()
        for texto, manejador in (
            ("+ Nueva tarea", self._nueva),
            ("Editar", self._editar),
            ("Activar / Desactivar", self._alternar),
            ("Ejecutar ahora", self._ejecutar),
            ("Eliminar", self._eliminar),
        ):
            boton = QPushButton(texto)
            boton.clicked.connect(manejador)
            fila.addWidget(boton)
        fila.addStretch()
        capa.addLayout(fila)
        self.refrescar()

    def refrescar(self) -> None:
        tareas = sorted(self.gestor.almacen.tareas, key=lambda t: t.nombre.lower())
        self.tabla.setRowCount(len(tareas))
        for fila, t in enumerate(tareas):
            celdas = [t.nombre, horarios.descripcion(t.horario), t.backend,
                      resumen(t.accion), "Activa" if t.habilitada else "Pausada"]
            for col, texto in enumerate(celdas):
                item = QTableWidgetItem(texto)
                item.setData(Qt.UserRole, t.id)
                self.tabla.setItem(fila, col, item)

    def _id_seleccionado(self) -> str | None:
        item = self.tabla.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _nueva(self) -> None:
        if DialogoTarea(self.gestor, parent=self).exec():
            self.refrescar()

    def _editar(self) -> None:
        tid = self._id_seleccionado()
        if tid is None:
            return
        tarea = self.gestor.almacen.obtener_tarea(tid)
        if tarea and DialogoTarea(self.gestor, tarea, parent=self).exec():
            self.refrescar()

    def _alternar(self) -> None:
        tid = self._id_seleccionado()
        if tid is None:
            return
        tarea = self.gestor.almacen.obtener_tarea(tid)
        try:
            self.gestor.alternar_tarea(tid, not tarea.habilitada)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))
        self.refrescar()

    def _ejecutar(self) -> None:
        tid = self._id_seleccionado()
        if tid is None:
            return
        tarea = self.gestor.almacen.obtener_tarea(tid)
        spec = REGISTRO.get(tarea.accion.tipo) if tarea else None
        if spec is not None and spec.peligrosa:
            resp = QMessageBox.question(
                self, "Ejecutar ahora",
                f"«{tarea.nombre}» ejecuta la acción «{spec.nombre}» "
                "(puede apagar el equipo ahora mismo). ¿Continuar?")
            if resp != QMessageBox.Yes:
                return
        self.gestor.ejecutar_tarea_ahora(tid)

    def _eliminar(self) -> None:
        tid = self._id_seleccionado()
        if tid is None:
            return
        tarea = self.gestor.almacen.obtener_tarea(tid)
        resp = QMessageBox.question(self, "Eliminar tarea",
                                    f"¿Eliminar la tarea «{tarea.nombre}»?")
        if resp == QMessageBox.Yes:
            try:
                self.gestor.eliminar_tarea(tid)
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))
            self.refrescar()
