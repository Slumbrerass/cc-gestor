"""Pestaña de comandos personalizados."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from ..core.acciones import resumen
from .dialogs.nuevo_comando import DialogoComando

COLUMNAS = ["Palabra clave", "Shells", "Acción", "Alias en rc"]


class TabComandos(QWidget):
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
            ("+ Nuevo comando", self._nuevo),
            ("Editar", self._editar),
            ("Eliminar", self._eliminar),
        ):
            boton = QPushButton(texto)
            boton.clicked.connect(manejador)
            fila.addWidget(boton)
        fila.addStretch()
        capa.addLayout(fila)
        self.refrescar()

    def refrescar(self) -> None:
        comandos = sorted(self.gestor.almacen.comandos,
                          key=lambda c: c.palabra_clave.lower())
        self.tabla.setRowCount(len(comandos))
        for fila, c in enumerate(comandos):
            celdas = [c.palabra_clave, ", ".join(c.shells_destino),
                      resumen(c.accion), "Sí" if c.crear_alias else "No"]
            for col, texto in enumerate(celdas):
                item = QTableWidgetItem(texto)
                item.setData(Qt.UserRole, c.id)
                self.tabla.setItem(fila, col, item)

    def _id_seleccionado(self) -> str | None:
        item = self.tabla.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _nuevo(self) -> None:
        if DialogoComando(self.gestor, parent=self).exec():
            self.refrescar()

    def _editar(self) -> None:
        cid = self._id_seleccionado()
        if cid is None:
            return
        comando = self.gestor.almacen.obtener_comando(cid)
        if comando and DialogoComando(self.gestor, comando, parent=self).exec():
            self.refrescar()

    def _eliminar(self) -> None:
        cid = self._id_seleccionado()
        if cid is None:
            return
        comando = self.gestor.almacen.obtener_comando(cid)
        resp = QMessageBox.question(self, "Eliminar comando",
                                    f"¿Eliminar el comando «{comando.palabra_clave}»?")
        if resp == QMessageBox.Yes:
            try:
                self.gestor.eliminar_comando(cid)
            except Exception as e:
                QMessageBox.warning(self, "Error", str(e))
            self.refrescar()
