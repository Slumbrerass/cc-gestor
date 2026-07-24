"""Diálogo de creación/edición de un comando personalizado."""

from __future__ import annotations

from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFormLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QVBoxLayout, QWidget)

from ...core.acciones import REGISTRO
from ...core.modelo import Comando, nuevo_id
from ..widgets.selector_accion import SelectorAccion


class DialogoComando(QDialog):
    def __init__(self, gestor, comando: Comando | None = None, parent=None):
        super().__init__(parent)
        self.gestor = gestor
        self._id = comando.id if comando else nuevo_id()
        self.setWindowTitle("Editar comando" if comando else "Nuevo comando personalizado")
        self.setMinimumWidth(460)

        capa = QVBoxLayout(self)
        form = QFormLayout()
        self.palabra = QLineEdit()
        self.palabra.setPlaceholderText("navidad")
        form.addRow("Palabra clave:", self.palabra)

        detectadas = gestor.comandos_backend.shells_detectadas()
        fila = QHBoxLayout()
        self.cajas_shell: dict[str, QCheckBox] = {}
        for shell in ("bash", "zsh", "fish"):
            caja = QCheckBox(shell)
            if shell not in detectadas:
                caja.setEnabled(False)
                caja.setToolTip(f"{shell} no está instalada en este sistema")
            else:
                caja.setChecked(True)
            self.cajas_shell[shell] = caja
            fila.addWidget(caja)
        cont = QWidget()
        cont.setLayout(fila)
        form.addRow("Shells:", cont)

        self.alias = QCheckBox("Crear también alias/función en el rc de cada shell")
        form.addRow("", self.alias)
        capa.addLayout(form)

        nota = QLabel("El comando siempre se instala como script en ~/.local/bin, "
                      "así funciona en cualquier shell del PATH.")
        nota.setWordWrap(True)
        nota.setStyleSheet("color: palette(mid);")
        capa.addWidget(nota)

        caja_accion = QGroupBox("Acción al escribir la palabra")
        v = QVBoxLayout(caja_accion)
        self.selector_accion = SelectorAccion()
        v.addWidget(self.selector_accion)
        capa.addWidget(caja_accion)

        botones = QDialogButtonBox()
        boton_probar = QPushButton("Probar")
        boton_probar.clicked.connect(self._probar)
        botones.addButton(boton_probar, QDialogButtonBox.ActionRole)
        botones.addButton(QDialogButtonBox.Save).setText("Guardar")
        botones.addButton(QDialogButtonBox.Cancel).setText("Cancelar")
        botones.accepted.connect(self._guardar)
        botones.rejected.connect(self.reject)
        capa.addWidget(botones)

        if comando:
            self.palabra.setText(comando.palabra_clave)
            for shell, caja in self.cajas_shell.items():
                if caja.isEnabled():
                    caja.setChecked(shell in comando.shells_destino)
            self.alias.setChecked(comando.crear_alias)
            self.selector_accion.cargar(comando.accion)

    def _probar(self) -> None:
        try:
            accion = self.selector_accion.accion()
            if REGISTRO[accion.tipo].peligrosa:
                resp = QMessageBox.question(
                    self, "Probar acción",
                    f"Probar «{REGISTRO[accion.tipo].nombre}» la ejecuta de verdad "
                    "(puede apagar el equipo ahora mismo). ¿Continuar?")
                if resp != QMessageBox.Yes:
                    return
            self.gestor.probar_accion(accion)
        except Exception as e:
            QMessageBox.warning(self, "No se pudo probar", str(e))

    def _guardar(self) -> None:
        try:
            palabra = self.palabra.text().strip()
            self.gestor.comandos_backend.validar_palabra(palabra)
            shells = [s for s, caja in self.cajas_shell.items() if caja.isChecked()]
            if not shells:
                raise ValueError("Elige al menos una shell")
            accion = self.selector_accion.accion()

            existente = self.gestor.almacen.obtener_comando(self._id)
            if not (existente and existente.palabra_clave == palabra):
                colision = self.gestor.comandos_backend.colision(palabra)
                if colision:
                    resp = QMessageBox.question(
                        self, "Ya existe un comando con ese nombre",
                        f"'{palabra}' ya existe en el sistema ({colision}).\n"
                        "Si continúas, tu comando puede ensombrecerlo. ¿Continuar?")
                    if resp != QMessageBox.Yes:
                        return

            comando = Comando(id=self._id, palabra_clave=palabra,
                              shells_destino=shells, accion=accion,
                              crear_alias=self.alias.isChecked())
            self.gestor.guardar_comando(comando)
        except Exception as e:
            QMessageBox.warning(self, "No se pudo guardar", str(e))
            return
        self.accept()
