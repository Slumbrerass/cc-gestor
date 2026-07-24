"""Diálogo de creación/edición de una tarea programada."""

from __future__ import annotations

from PySide6.QtCore import QTime
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
                               QFormLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QSpinBox, QStackedWidget,
                               QTimeEdit, QVBoxLayout, QWidget)

from ...core import horarios
from ...core.modelo import Tarea, nuevo_id
from ..widgets.selector_accion import SelectorAccion

PRESETS = [
    ("cada_minuto", "Cada minuto"),
    ("cada_n_minutos", "Cada N minutos"),
    ("cada_hora", "Cada hora"),
    ("diaria", "Diaria"),
    ("semanal", "Semanal"),
    ("mensual", "Mensual"),
    ("personalizada", "Personalizada (avanzado)"),
]


class _SelectorHorario(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        capa = QVBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        self.combo = QComboBox()
        self.combo.addItems([nombre for _, nombre in PRESETS])
        self._pila = QStackedWidget()
        self._paginas: dict[str, QWidget] = {}
        for tipo, _ in PRESETS:
            pagina = self._crear_pagina(tipo)
            self._paginas[tipo] = pagina
            self._pila.addWidget(pagina)
        self.combo.currentIndexChanged.connect(self._pila.setCurrentIndex)
        capa.addWidget(self.combo)
        capa.addWidget(self._pila)

    def _crear_pagina(self, tipo: str) -> QWidget:
        pagina = QWidget()
        form = QFormLayout(pagina)
        form.setContentsMargins(0, 4, 0, 0)
        if tipo == "cada_n_minutos":
            pagina.spin_n = QSpinBox(minimum=1, maximum=59, value=5)
            form.addRow("Cada cuántos minutos:", pagina.spin_n)
        elif tipo == "cada_hora":
            pagina.spin_minuto = QSpinBox(minimum=0, maximum=59)
            form.addRow("Al minuto:", pagina.spin_minuto)
        elif tipo in ("diaria", "semanal", "mensual"):
            pagina.hora = QTimeEdit(QTime(8, 0))
            pagina.hora.setDisplayFormat("HH:mm")
            form.addRow("Hora:", pagina.hora)
            if tipo == "semanal":
                fila = QHBoxLayout()
                pagina.dias = {}
                for num, nombre, _, _ in horarios.DIAS_SEMANA:
                    caja = QCheckBox(nombre[:2])
                    caja.setToolTip(nombre)
                    pagina.dias[num] = caja
                    fila.addWidget(caja)
                cont = QWidget()
                cont.setLayout(fila)
                form.addRow("Días:", cont)
            if tipo == "mensual":
                pagina.spin_dia = QSpinBox(minimum=1, maximum=31, value=1)
                form.addRow("Día del mes:", pagina.spin_dia)
        elif tipo == "personalizada":
            pagina.cron = QLineEdit()
            pagina.cron.setPlaceholderText("*/5 * * * *")
            pagina.oncalendar = QLineEdit()
            pagina.oncalendar.setPlaceholderText("*-*-* *:0/5:00  (solo para backend systemd)")
            form.addRow("Expresión cron:", pagina.cron)
            form.addRow("OnCalendar:", pagina.oncalendar)
        else:
            form.addRow(QLabel("La tarea se ejecutará cada minuto."))
        return pagina

    def horario(self) -> dict:
        tipo = PRESETS[self.combo.currentIndex()][0]
        pagina = self._paginas[tipo]
        if tipo == "cada_minuto":
            return {"tipo": tipo}
        if tipo == "cada_n_minutos":
            return {"tipo": tipo, "n": pagina.spin_n.value()}
        if tipo == "cada_hora":
            return {"tipo": tipo, "minuto": pagina.spin_minuto.value()}
        t = pagina.hora.time()
        if tipo == "diaria":
            return {"tipo": tipo, "hora": t.hour(), "minuto": t.minute()}
        if tipo == "semanal":
            dias = [n for n, caja in pagina.dias.items() if caja.isChecked()]
            return {"tipo": tipo, "dias": dias, "hora": t.hour(), "minuto": t.minute()}
        if tipo == "mensual":
            return {"tipo": tipo, "dia": pagina.spin_dia.value(),
                    "hora": t.hour(), "minuto": t.minute()}
        return {"tipo": "personalizada",
                "cron": pagina.cron.text().strip(),
                "oncalendar": pagina.oncalendar.text().strip()}

    def cargar(self, h: dict) -> None:
        tipo = h.get("tipo", "cada_minuto")
        idx = next((i for i, (t, _) in enumerate(PRESETS) if t == tipo), 0)
        self.combo.setCurrentIndex(idx)
        pagina = self._paginas[tipo]
        if tipo == "cada_n_minutos":
            pagina.spin_n.setValue(int(h["n"]))
        elif tipo == "cada_hora":
            pagina.spin_minuto.setValue(int(h["minuto"]))
        elif tipo in ("diaria", "semanal", "mensual"):
            pagina.hora.setTime(QTime(int(h["hora"]), int(h["minuto"])))
            if tipo == "semanal":
                for n, caja in pagina.dias.items():
                    caja.setChecked(n in [int(d) for d in h.get("dias", [])])
            if tipo == "mensual":
                pagina.spin_dia.setValue(int(h["dia"]))
        elif tipo == "personalizada":
            pagina.cron.setText(h.get("cron", ""))
            pagina.oncalendar.setText(h.get("oncalendar", ""))


class DialogoTarea(QDialog):
    def __init__(self, gestor, tarea: Tarea | None = None, parent=None):
        super().__init__(parent)
        self.gestor = gestor
        self._id = tarea.id if tarea else nuevo_id()
        self._habilitada = tarea.habilitada if tarea else True
        self.setWindowTitle("Editar tarea" if tarea else "Nueva tarea programada")
        self.setMinimumWidth(480)

        capa = QVBoxLayout(self)
        form = QFormLayout()
        self.nombre = QLineEdit()
        form.addRow("Nombre:", self.nombre)

        self.backend = QComboBox()
        disponibles = gestor.backends_disponibles()
        for clave, etiqueta in (("crontab", "Crontab clásico"), ("systemd", "systemd user timer")):
            self.backend.addItem(etiqueta, clave)
            if not disponibles.get(clave):
                idx = self.backend.count() - 1
                self.backend.setItemData(idx, 0, 32)  # Qt.UserRole - 1: deshabilitar item
                self.backend.model().item(idx).setEnabled(False)
                self.backend.setItemText(idx, etiqueta + " (no disponible)")
        # preseleccionar el primero disponible
        for i in range(self.backend.count()):
            if disponibles.get(self.backend.itemData(i)):
                self.backend.setCurrentIndex(i)
                break
        form.addRow("Backend:", self.backend)
        capa.addLayout(form)

        caja_horario = QGroupBox("Horario")
        v1 = QVBoxLayout(caja_horario)
        self.selector_horario = _SelectorHorario()
        v1.addWidget(self.selector_horario)
        capa.addWidget(caja_horario)

        caja_accion = QGroupBox("Acción")
        v2 = QVBoxLayout(caja_accion)
        self.selector_accion = SelectorAccion()
        v2.addWidget(self.selector_accion)
        capa.addWidget(caja_accion)

        botones = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        botones.button(QDialogButtonBox.Save).setText("Guardar")
        botones.button(QDialogButtonBox.Cancel).setText("Cancelar")
        botones.accepted.connect(self._guardar)
        botones.rejected.connect(self.reject)
        capa.addWidget(botones)

        if tarea:
            self.nombre.setText(tarea.nombre)
            i = self.backend.findData(tarea.backend)
            if i >= 0:
                self.backend.setCurrentIndex(i)
            self.selector_horario.cargar(tarea.horario)
            self.selector_accion.cargar(tarea.accion)

    def _guardar(self) -> None:
        try:
            nombre = self.nombre.text().strip()
            if not nombre:
                raise ValueError("Ponle un nombre a la tarea")
            backend = self.backend.currentData()
            horario = self.selector_horario.horario()
            horarios.construir(horario)  # valida antes de tocar nada
            accion = self.selector_accion.accion()
            tarea = Tarea(id=self._id, nombre=nombre, backend=backend,
                          horario=horario, accion=accion, habilitada=self._habilitada)
            self.gestor.guardar_tarea(tarea)
        except Exception as e:
            QMessageBox.warning(self, "No se pudo guardar", str(e))
            return
        self.accept()
