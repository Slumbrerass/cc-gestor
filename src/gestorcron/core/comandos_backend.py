"""Backend de comandos personalizados.

Fuente de verdad: un script ejecutable en ~/.local/bin/<palabra_clave>.
Opcionalmente, un alias en el rc de bash/zsh (dentro de un bloque delimitado
reversible) y/o una función autocargada de fish.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from .. import rutas
from .acciones import generar_script
from .modelo import Comando

RC_POR_SHELL = {"bash": ".bashrc", "zsh": ".zshrc"}
PALABRA_VALIDA = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


def _marca_ini(comando_id: str) -> str:
    return f"# >>> gestorcron:{comando_id} >>>"


def _marca_fin(comando_id: str) -> str:
    return f"# <<< gestorcron:{comando_id} <<<"


class ComandosBackend:
    @staticmethod
    def shells_detectadas() -> list[str]:
        return [s for s in ("bash", "zsh", "fish") if shutil.which(s)]

    @staticmethod
    def validar_palabra(palabra: str) -> None:
        if not PALABRA_VALIDA.match(palabra):
            raise ValueError("La palabra clave solo puede llevar letras, números, '-' y '_', "
                             "y debe empezar por letra")

    def colision(self, palabra: str) -> str | None:
        """Ruta de un binario ya existente con ese nombre (que no sea nuestro), o None."""
        encontrado = shutil.which(palabra)
        if encontrado and Path(encontrado).resolve() != (rutas.bin_dir() / palabra).resolve():
            return encontrado
        return None

    def crear(self, comando: Comando) -> Path:
        self.validar_palabra(comando.palabra_clave)
        destino = rutas.bin_dir() / comando.palabra_clave
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(generar_script(comando.accion), encoding="utf-8")
        destino.chmod(0o755)
        if comando.crear_alias:
            for shell in comando.shells_destino:
                if shell in RC_POR_SHELL:
                    alias = f'alias {comando.palabra_clave}="{destino}"'
                    self._poner_bloque(Path.home() / RC_POR_SHELL[shell], comando.id, alias)
                elif shell == "fish":
                    self._crear_funcion_fish(comando, destino)
        return destino

    def eliminar(self, comando: Comando) -> None:
        (rutas.bin_dir() / comando.palabra_clave).unlink(missing_ok=True)
        for rc in RC_POR_SHELL.values():
            self._quitar_bloque(Path.home() / rc, comando.id)
        (rutas.fish_functions_dir() / f"{comando.palabra_clave}.fish").unlink(missing_ok=True)

    # --- bloques delimitados en rc de bash/zsh ---
    def _poner_bloque(self, rc: Path, comando_id: str, contenido: str) -> None:
        self._quitar_bloque(rc, comando_id)
        bloque = f"\n{_marca_ini(comando_id)}\n{contenido}\n{_marca_fin(comando_id)}\n"
        previo = rc.read_text(encoding="utf-8") if rc.exists() else ""
        rc.write_text(previo + bloque, encoding="utf-8")

    def _quitar_bloque(self, rc: Path, comando_id: str) -> None:
        if not rc.exists():
            return
        texto = rc.read_text(encoding="utf-8")
        patron = re.compile(
            r"\n?" + re.escape(_marca_ini(comando_id)) + r".*?" + re.escape(_marca_fin(comando_id)) + r"\n?",
            re.DOTALL,
        )
        nuevo = patron.sub("\n", texto)
        if nuevo != texto:
            rc.write_text(nuevo, encoding="utf-8")

    def _crear_funcion_fish(self, comando: Comando, destino: Path) -> None:
        d = rutas.fish_functions_dir()
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{comando.palabra_clave}.fish").write_text(
            f"function {comando.palabra_clave} "
            f"--description 'Generado por Gestor Cron & Comandos (gestorcron:{comando.id})'\n"
            f"    {destino} $argv\nend\n",
            encoding="utf-8",
        )
