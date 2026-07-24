"""Ventana principal con las tres pestañas."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget

from . import estilo
from .tab_ajustes import TabAjustes
from .tab_comandos import TabComandos
from .tab_cron import TabCron

ICONO = Path(__file__).parent.parent / "recursos" / "icono.svg"


class VentanaPrincipal(QMainWindow):
    def __init__(self, gestor):
        super().__init__()
        self.gestor = gestor
        self.setWindowTitle("Gestor Cron & Comandos")
        if ICONO.exists():
            self.setWindowIcon(QIcon(str(ICONO)))
        self.resize(860, 560)
        self._crear_menu()

        self.tab_cron = TabCron(gestor)
        self.tab_comandos = TabComandos(gestor)
        self.tab_ajustes = TabAjustes(gestor)

        pestañas = QTabWidget()
        pestañas.addTab(self.tab_cron, "Tareas programadas")
        pestañas.addTab(self.tab_comandos, "Comandos personalizados")
        pestañas.addTab(self.tab_ajustes, "Ajustes")
        self.setCentralWidget(pestañas)

    def _crear_menu(self) -> None:
        prefs = self.gestor.almacen.preferencias
        # guardar la referencia evita que shiboken libere el QMenu
        self._menu_ver = menu = self.menuBar().addMenu("&Ver")

        oscuro = QAction("Tema &oscuro", self)
        oscuro.setCheckable(True)
        oscuro.setChecked(bool(prefs.get("tema_oscuro", False)))
        oscuro.toggled.connect(self._cambiar_tema)
        menu.addAction(oscuro)
        menu.addSeparator()

        for texto, atajo, delta in (("&Aumentar tamaño", QKeySequence.ZoomIn, +1),
                                    ("&Reducir tamaño", QKeySequence.ZoomOut, -1),
                                    ("Tamaño &normal", "Ctrl+0", 0)):
            accion = QAction(texto, self)
            accion.setShortcut(QKeySequence(atajo))
            accion.triggered.connect(lambda _=False, d=delta: self._cambiar_tamano(d))
            menu.addAction(accion)

    def _cambiar_tema(self, oscuro: bool) -> None:
        estilo.aplicar_tema(QApplication.instance(), oscuro)
        self._guardar_preferencia("tema_oscuro", oscuro)

    def _cambiar_tamano(self, delta: int) -> None:
        app = QApplication.instance()
        actual = app.font().pointSize()
        if actual <= 0:
            actual = estilo.tamano_base()
        deseado = estilo.tamano_base() if delta == 0 else actual + delta
        aplicado = estilo.aplicar_tamano(app, deseado)
        self._guardar_preferencia("tamano_fuente", aplicado)

    def _guardar_preferencia(self, clave: str, valor) -> None:
        self.gestor.almacen.preferencias[clave] = valor
        self.gestor.almacen.guardar()

    def refrescar_todo(self) -> None:
        self.tab_cron.refrescar()
        self.tab_comandos.refrescar()
