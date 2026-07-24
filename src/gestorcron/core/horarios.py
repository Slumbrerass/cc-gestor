"""Traducción del horario visual a expresión cron y a OnCalendar de systemd.

El horario se guarda como dict con clave "tipo" y parámetros propios:
  cada_minuto      {}
  cada_n_minutos   {"n": 5}
  cada_hora        {"minuto": 30}
  diaria           {"hora": 8, "minuto": 0}
  semanal          {"dias": [1, 3], "hora": 8, "minuto": 0}   # 1=lunes .. 7=domingo
  mensual          {"dia": 15, "hora": 8, "minuto": 0}
  personalizada    {"cron": "*/5 * * * *", "oncalendar": "*:0/5"}
"""

from __future__ import annotations

import re

# (número interno 1-7, nombre visible, dow de cron, nombre systemd)
DIAS_SEMANA = [
    (1, "Lunes", "1", "Mon"),
    (2, "Martes", "2", "Tue"),
    (3, "Miércoles", "3", "Wed"),
    (4, "Jueves", "4", "Thu"),
    (5, "Viernes", "5", "Fri"),
    (6, "Sábado", "6", "Sat"),
    (7, "Domingo", "0", "Sun"),
]
_POR_NUM = {d[0]: d for d in DIAS_SEMANA}


def construir(h: dict) -> tuple[str, str]:
    """Devuelve (expresión_cron, OnCalendar) para el horario dado."""
    t = h["tipo"]
    if t == "cada_minuto":
        return "* * * * *", "*-*-* *:*:00"
    if t == "cada_n_minutos":
        n = int(h["n"])
        if not 1 <= n <= 59:
            raise ValueError("El intervalo de minutos debe estar entre 1 y 59")
        return f"*/{n} * * * *", f"*-*-* *:0/{n}:00"
    if t == "cada_hora":
        m = int(h["minuto"])
        return f"{m} * * * *", f"*-*-* *:{m:02d}:00"
    if t == "diaria":
        hh, mm = int(h["hora"]), int(h["minuto"])
        return f"{mm} {hh} * * *", f"*-*-* {hh:02d}:{mm:02d}:00"
    if t == "semanal":
        dias = sorted(int(d) for d in h["dias"])
        if not dias:
            raise ValueError("Elige al menos un día de la semana")
        hh, mm = int(h["hora"]), int(h["minuto"])
        cron_dias = ",".join(_POR_NUM[d][2] for d in dias)
        sysd_dias = ",".join(_POR_NUM[d][3] for d in dias)
        return f"{mm} {hh} * * {cron_dias}", f"{sysd_dias} *-*-* {hh:02d}:{mm:02d}:00"
    if t == "mensual":
        dia, hh, mm = int(h["dia"]), int(h["hora"]), int(h["minuto"])
        return f"{mm} {hh} {dia} * *", f"*-*-{dia:02d} {hh:02d}:{mm:02d}:00"
    if t == "personalizada":
        cron = h.get("cron", "").strip()
        validar_cron(cron)
        return cron, h.get("oncalendar", "").strip()
    raise ValueError(f"Tipo de horario desconocido: {t}")


def validar_cron(expr: str) -> None:
    campos = expr.split()
    if len(campos) != 5:
        raise ValueError("La expresión cron debe tener 5 campos (min hora día mes día-semana)")
    if not all(re.fullmatch(r"[\d*,/\-]+", c) for c in campos):
        raise ValueError("La expresión cron contiene caracteres no válidos")


def descripcion(h: dict) -> str:
    """Texto legible del horario para las listas de la GUI."""
    t = h["tipo"]
    if t == "cada_minuto":
        return "Cada minuto"
    if t == "cada_n_minutos":
        return f"Cada {h['n']} minutos"
    if t == "cada_hora":
        return f"Cada hora, al minuto {int(h['minuto']):02d}"
    if t == "diaria":
        return f"Diaria a las {int(h['hora']):02d}:{int(h['minuto']):02d}"
    if t == "semanal":
        nombres = ", ".join(_POR_NUM[int(d)][1] for d in sorted(h["dias"]))
        return f"{nombres} a las {int(h['hora']):02d}:{int(h['minuto']):02d}"
    if t == "mensual":
        return f"Día {h['dia']} de cada mes a las {int(h['hora']):02d}:{int(h['minuto']):02d}"
    if t == "personalizada":
        return f"Cron: {h.get('cron', '')}"
    return t
