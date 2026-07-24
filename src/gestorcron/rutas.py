"""Rutas de configuración y datos, calculadas en tiempo de llamada para respetar HOME/XDG."""

import os
from pathlib import Path


def config_dir() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "gestor-cron-comandos"


def data_dir() -> Path:
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "gestor-cron-comandos"


def jobs_dir() -> Path:
    return data_dir() / "jobs"


def bin_dir() -> Path:
    return Path.home() / ".local" / "bin"


def systemd_user_dir() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "systemd" / "user"


def fish_functions_dir() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "fish" / "functions"
