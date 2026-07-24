"""Widget compartido para elegir un tipo de acción y rellenar sus parámetros."""

from __future__ import annotations

from PySide6.QtWidgets import (QComboBox, QFileDialog, QFormLayout, QHBoxLayout,
                               QLineEdit, QPlainTextEdit, QPushButton, QSpinBox,
                               QStackedWidget, QVBoxLayout, QWidget)

from ...core.acciones import REGISTRO, Campo
from ...core.modelo import Accion


class _Formulario(QWidget):
    """Formulario dinámico generado a partir de los Campos de una AccionSpec."""

    FILTROS_AUDIO = "Audio (*.mp3 *.ogg *.wav *.flac *.opus *.m4a);;Todos los archivos (*)"

    def __init__(self, campos: list[Campo], parent=None):
        super().__init__(parent)
        self._editores: dict[str, QWidget] = {}
        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        for campo in campos:
            form.addRow(campo.etiqueta + ":", self._crear_editor(campo))

    def _crear_editor(self, campo: Campo) -> QWidget:
        if campo.tipo == "multilinea":
            editor = QPlainTextEdit()
            editor.setPlaceholderText("Comando o script a ejecutar…")
            editor.setFixedHeight(80)
            self._editores[campo.clave] = editor
            return editor
        if campo.tipo == "interprete":
            editor = QComboBox()
            editor.addItems(campo.opciones)
            self._editores[campo.clave] = editor
            return editor
        if campo.tipo == "segundos":
            editor = QSpinBox()
            editor.setRange(0, 86400)
            editor.setSuffix(" s")
            editor.setSpecialValueText("Sin límite (completo)")
            self._editores[campo.clave] = editor
            return editor
        linea = QLineEdit()
        self._editores[campo.clave] = linea
        if campo.tipo in ("archivo", "audio"):
            cont = QWidget()
            fila = QHBoxLayout(cont)
            fila.setContentsMargins(0, 0, 0, 0)
            boton = QPushButton("Examinar…")
            filtro = self.FILTROS_AUDIO if campo.tipo == "audio" else "Todos los archivos (*)"

            def examinar():
                ruta, _ = QFileDialog.getOpenFileName(self, "Elegir archivo", "", filtro)
                if ruta:
                    linea.setText(ruta)

            boton.clicked.connect(examinar)
            fila.addWidget(linea, 1)
            fila.addWidget(boton)
            return cont
        if campo.tipo == "url":
            linea.setPlaceholderText("https://…")
        return linea

    def valores(self) -> dict:
        out = {}
        for clave, editor in self._editores.items():
            if isinstance(editor, QPlainTextEdit):
                out[clave] = editor.toPlainText().strip()
            elif isinstance(editor, QComboBox):
                out[clave] = editor.currentText()
            elif isinstance(editor, QSpinBox):
                out[clave] = editor.value()
            else:
                out[clave] = editor.text().strip()
        return out

    def cargar(self, params: dict) -> None:
        # recorre todos los editores (no solo params) para que los campos
        # ausentes en configuraciones antiguas queden en su valor por defecto
        for clave, editor in self._editores.items():
            valor = params.get(clave, "")
            if isinstance(editor, QPlainTextEdit):
                editor.setPlainText(str(valor))
            elif isinstance(editor, QComboBox):
                editor.setCurrentText(str(valor))
            elif isinstance(editor, QSpinBox):
                editor.setValue(int(valor or 0))
            else:
                editor.setText(str(valor))


class SelectorAccion(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tipos = list(REGISTRO.keys())
        capa = QVBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        self.combo = QComboBox()
        self.combo.addItems([REGISTRO[t].nombre for t in self._tipos])
        self._pila = QStackedWidget()
        for tipo in self._tipos:
            self._pila.addWidget(_Formulario(REGISTRO[tipo].campos))
        self.combo.currentIndexChanged.connect(self._pila.setCurrentIndex)
        capa.addWidget(self.combo)
        capa.addWidget(self._pila)

    def accion(self) -> Accion:
        tipo = self._tipos[self.combo.currentIndex()]
        params = self._pila.currentWidget().valores()
        opcionales = {c.clave for c in REGISTRO[tipo].campos if c.opcional}
        vacios = [k for k, v in params.items() if not v and k not in opcionales]
        if vacios:
            raise ValueError("Faltan campos por rellenar en la acción")
        return Accion(tipo=tipo, params=params)

    def cargar(self, accion: Accion) -> None:
        if accion.tipo in self._tipos:
            idx = self._tipos.index(accion.tipo)
            self.combo.setCurrentIndex(idx)
            self._pila.widget(idx).cargar(accion.params)
