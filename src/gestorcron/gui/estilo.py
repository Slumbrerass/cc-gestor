"""Hoja de estilo QSS, tema oscuro opcional y tamaño de letra ajustable.

El QSS usa palette() en vez de colores fijos, así que sirve igual para el tema
del sistema y para la paleta oscura propia.
"""

from PySide6.QtGui import QColor, QPalette

TAMANO_MIN, TAMANO_MAX = 7, 24

# estilo, paleta y tamaño con los que arrancó la app (el tema del sistema),
# capturados en aplicar_estilo() para poder volver a ellos
_original: dict = {}

QSS = """
QTabWidget::pane {
    border: 1px solid palette(mid);
    border-radius: 6px;
    top: -1px;
}
QTabBar::tab {
    padding: 8px 18px;
    border: 1px solid transparent;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    border-color: palette(mid);
    background: palette(base);
}
QPushButton {
    padding: 6px 14px;
    border: 1px solid palette(mid);
    border-radius: 6px;
    background: palette(button);
}
QPushButton:hover { background: palette(light); }
QPushButton:pressed { background: palette(midlight); }
QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QTimeEdit {
    padding: 5px 8px;
    border: 1px solid palette(mid);
    border-radius: 6px;
    background: palette(base);
}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QSpinBox:focus, QTimeEdit:focus {
    border-color: palette(highlight);
}
QTableWidget {
    border: 1px solid palette(mid);
    border-radius: 6px;
    gridline-color: palette(midlight);
}
QHeaderView::section {
    padding: 6px;
    border: none;
    border-bottom: 1px solid palette(mid);
    background: palette(button);
}
QGroupBox {
    font-weight: bold;
    border: 1px solid palette(mid);
    border-radius: 6px;
    margin-top: 10px;
    padding-top: 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}
"""


def aplicar_estilo(app) -> None:
    _original.setdefault("estilo", app.style().objectName())
    _original.setdefault("paleta", QPalette(app.palette()))
    puntos = app.font().pointSize()
    _original.setdefault("tamano", puntos if puntos > 0 else 10)
    app.setStyleSheet(QSS)


def tamano_base() -> int:
    return _original.get("tamano", 10)


def _paleta_oscura() -> QPalette:
    # partir del color de botón deja que Qt derive mid/light/midlight,
    # que son los tonos que usa el QSS para bordes y hovers
    p = QPalette(QColor(50, 50, 54))
    texto = QColor(222, 222, 222)
    p.setColor(QPalette.Window, QColor(40, 40, 43))
    p.setColor(QPalette.WindowText, texto)
    p.setColor(QPalette.Base, QColor(30, 30, 33))
    p.setColor(QPalette.AlternateBase, QColor(40, 40, 43))
    p.setColor(QPalette.Text, texto)
    p.setColor(QPalette.ButtonText, texto)
    p.setColor(QPalette.ToolTipBase, QColor(50, 50, 54))
    p.setColor(QPalette.ToolTipText, texto)
    p.setColor(QPalette.PlaceholderText, QColor(140, 140, 140))
    p.setColor(QPalette.BrightText, QColor(255, 105, 97))
    p.setColor(QPalette.Highlight, QColor(42, 130, 218))
    p.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    p.setColor(QPalette.Link, QColor(96, 165, 230))
    for rol in (QPalette.Text, QPalette.WindowText, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, rol, QColor(128, 128, 128))
    return p


def aplicar_tema(app, oscuro: bool) -> None:
    if oscuro:
        # Fusion respeta la paleta al completo; los estilos nativos no siempre
        app.setStyle("Fusion")
        app.setPalette(_paleta_oscura())
    else:
        app.setStyle(_original.get("estilo", "Fusion"))
        app.setPalette(_original.get("paleta", QPalette()))
    app.setStyleSheet(QSS)


def aplicar_tamano(app, puntos: int) -> int:
    puntos = max(TAMANO_MIN, min(TAMANO_MAX, int(puntos)))
    fuente = app.font()
    fuente.setPointSize(puntos)
    app.setFont(fuente)
    app.setStyleSheet(QSS)
    return puntos
