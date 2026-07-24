"""Punto de entrada de la aplicación."""

import sys


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from .core.servicio import Gestor
    from .gui.estilo import aplicar_estilo, aplicar_tamano, aplicar_tema
    from .gui.main_window import VentanaPrincipal

    app = QApplication(sys.argv)
    app.setApplicationName("gestor-cron-comandos")
    app.setApplicationDisplayName("Gestor Cron & Comandos")
    aplicar_estilo(app)

    gestor = Gestor()
    prefs = gestor.almacen.preferencias
    if prefs.get("tema_oscuro"):
        aplicar_tema(app, True)
    if prefs.get("tamano_fuente"):
        aplicar_tamano(app, prefs["tamano_fuente"])

    ventana = VentanaPrincipal(gestor)
    ventana.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
