"""Pestaña de ajustes: estado del sistema, PATH, exportar/importar configuración."""

from __future__ import annotations

import getpass
import os
import shutil
import subprocess
from pathlib import Path

from PySide6.QtWidgets import (QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
                               QLabel, QMessageBox, QPushButton, QVBoxLayout,
                               QWidget)

from .. import rutas

BLOQUE_PATH = (
    '\n# >>> gestorcron:path >>>\n'
    'case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac\n'
    '# <<< gestorcron:path <<<\n'
)
BLOQUE_PATH_FISH = (
    '\n# >>> gestorcron:path >>>\n'
    'fish_add_path -g ~/.local/bin\n'
    '# <<< gestorcron:path <<<\n'
)


def _bin_en_path() -> bool:
    return str(rutas.bin_dir()) in os.environ.get("PATH", "").split(":")


def _apagado_autorizado() -> bool:
    """True si sudo permite apagar sin contraseña (regla de la acción Apagar)."""
    systemctl = shutil.which("systemctl")
    if not systemctl:
        return False
    try:
        r = subprocess.run(["sudo", "-n", "-l", systemctl, "poweroff"],
                           capture_output=True, timeout=5)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


class TabAjustes(QWidget):
    def __init__(self, gestor, parent=None):
        super().__init__(parent)
        self.gestor = gestor
        capa = QVBoxLayout(self)

        estado = QGroupBox("Estado del sistema")
        form = QFormLayout(estado)
        disponibles = gestor.backends_disponibles()
        form.addRow("Backend crontab:", QLabel("Disponible" if disponibles["crontab"]
                                               else "No disponible (instala cron/cronie)"))
        form.addRow("Backend systemd:", QLabel("Disponible" if disponibles["systemd"]
                                               else "No disponible"))
        form.addRow("Shells detectadas:", QLabel(", ".join(
            gestor.comandos_backend.shells_detectadas()) or "ninguna"))

        fila_path = QHBoxLayout()
        self.etiqueta_path = QLabel()
        fila_path.addWidget(self.etiqueta_path)
        self.boton_path = QPushButton("Reparar PATH")
        self.boton_path.clicked.connect(self._reparar_path)
        fila_path.addWidget(self.boton_path)
        fila_path.addStretch()
        cont = QWidget()
        cont.setLayout(fila_path)
        form.addRow("~/.local/bin en PATH:", cont)

        fila_apagado = QHBoxLayout()
        self.etiqueta_apagado = QLabel()
        fila_apagado.addWidget(self.etiqueta_apagado)
        self.boton_apagado = QPushButton("Autorizar…")
        self.boton_apagado.setToolTip(
            "Instala una regla de sudo (solo para apagar/rtcwake) para que la "
            "acción «Apagar el equipo» funcione desde tareas programadas.")
        self.boton_apagado.clicked.connect(self._autorizar_apagado)
        fila_apagado.addWidget(self.boton_apagado)
        fila_apagado.addStretch()
        cont_apagado = QWidget()
        cont_apagado.setLayout(fila_apagado)
        form.addRow("Apagado programado:", cont_apagado)
        capa.addWidget(estado)

        copia = QGroupBox("Copia de seguridad")
        fila = QHBoxLayout(copia)
        exportar = QPushButton("Exportar configuración…")
        exportar.clicked.connect(self._exportar)
        importar = QPushButton("Importar configuración…")
        importar.clicked.connect(self._importar)
        fila.addWidget(exportar)
        fila.addWidget(importar)
        fila.addStretch()
        capa.addWidget(copia)

        nota = QLabel("Para desinstalar la aplicación ejecuta el script uninstall.sh "
                      "incluido con el programa.")
        nota.setWordWrap(True)
        nota.setStyleSheet("color: palette(mid);")
        capa.addWidget(nota)
        capa.addStretch()
        self._refrescar_path()
        self._refrescar_apagado()

    def _refrescar_path(self) -> None:
        ok = _bin_en_path()
        self.etiqueta_path.setText("Sí" if ok else "No")
        self.boton_path.setVisible(not ok)

    def _refrescar_apagado(self) -> None:
        ok = _apagado_autorizado()
        self.etiqueta_apagado.setText("Autorizado" if ok else "No autorizado")
        self.boton_apagado.setVisible(not ok)

    def _autorizar_apagado(self) -> None:
        systemctl = shutil.which("systemctl")
        rtcwake = shutil.which("rtcwake")
        if not systemctl:
            QMessageBox.warning(self, "No disponible",
                                "No se encontró systemctl en este sistema.")
            return
        if not shutil.which("pkexec"):
            QMessageBox.information(
                self, "Hace falta hacerlo a mano",
                "No hay pkexec (polkit). Crea el archivo como root:\n\n"
                f"  /etc/sudoers.d/gestorcron-apagado\n\ncon esta línea:\n\n"
                f"  {getpass.getuser()} ALL=(root) NOPASSWD: {systemctl} poweroff"
                + (f", {rtcwake} *" if rtcwake else ""))
            return
        comandos = f"{systemctl} poweroff" + (f", {rtcwake} *" if rtcwake else "")
        regla = f"{getpass.getuser()} ALL=(root) NOPASSWD: {comandos}\n"
        # se valida con visudo antes de activarla para no romper sudo
        script = ('f=/etc/sudoers.d/gestorcron-apagado; '
                  'printf %s "$1" > "$f.tmp" && chmod 440 "$f.tmp" '
                  '&& visudo -cq -f "$f.tmp" && mv "$f.tmp" "$f" '
                  '|| { rm -f "$f.tmp"; exit 1; }')
        try:
            r = subprocess.run(["pkexec", "bash", "-c", script, "_", regla],
                               capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        self._refrescar_apagado()
        if r.returncode == 0:
            QMessageBox.information(
                self, "Apagado autorizado",
                "Regla instalada en /etc/sudoers.d/gestorcron-apagado.\n"
                "La acción «Apagar el equipo» ya funciona desde tareas programadas.")
        elif r.returncode in (126, 127):
            pass  # el usuario canceló el diálogo de autenticación
        else:
            QMessageBox.warning(self, "No se pudo autorizar",
                                (r.stderr or "").strip() or "Error desconocido")

    def _reparar_path(self) -> None:
        arreglados = []
        for shell, rc in (("bash", ".bashrc"), ("zsh", ".zshrc")):
            if shutil.which(shell):
                ruta = Path.home() / rc
                texto = ruta.read_text(encoding="utf-8") if ruta.exists() else ""
                if "gestorcron:path" not in texto:
                    ruta.write_text(texto + BLOQUE_PATH, encoding="utf-8")
                arreglados.append(rc)
        if shutil.which("fish"):
            conf = Path(os.environ.get("XDG_CONFIG_HOME",
                                       Path.home() / ".config")) / "fish" / "config.fish"
            texto = conf.read_text(encoding="utf-8") if conf.exists() else ""
            if "gestorcron:path" not in texto:
                conf.parent.mkdir(parents=True, exist_ok=True)
                conf.write_text(texto + BLOQUE_PATH_FISH, encoding="utf-8")
            arreglados.append("config.fish")
        QMessageBox.information(
            self, "PATH reparado",
            "Añadido ~/.local/bin al PATH en: " + ", ".join(arreglados) +
            ".\nAbre una terminal nueva para que haga efecto.")

    def _exportar(self) -> None:
        destino, _ = QFileDialog.getSaveFileName(self, "Exportar configuración",
                                                 "gestor-cron-comandos.json",
                                                 "JSON (*.json)")
        if destino:
            shutil.copyfile(self.gestor.almacen.ruta, destino)
            QMessageBox.information(self, "Exportado", f"Configuración guardada en {destino}")

    def _importar(self) -> None:
        origen, _ = QFileDialog.getOpenFileName(self, "Importar configuración", "",
                                                "JSON (*.json)")
        if not origen:
            return
        resp = QMessageBox.question(
            self, "Importar configuración",
            "Esto sustituirá la configuración actual y volverá a crear todas las "
            "tareas y comandos del archivo. ¿Continuar?")
        if resp != QMessageBox.Yes:
            return
        try:
            shutil.copyfile(origen, self.gestor.almacen.ruta)
            self.gestor.almacen.cargar()
            for tarea in list(self.gestor.almacen.tareas):
                self.gestor.guardar_tarea(tarea)
            for comando in list(self.gestor.almacen.comandos):
                self.gestor.guardar_comando(comando)
        except Exception as e:
            QMessageBox.warning(self, "Error al importar", str(e))
            return
        ventana = self.window()
        if hasattr(ventana, "refrescar_todo"):
            ventana.refrescar_todo()
        QMessageBox.information(self, "Importado", "Configuración importada y aplicada.")
