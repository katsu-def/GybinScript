from __future__ import annotations

# Este archivo concentra la configuracion compartida del lenguaje.
# `keys` lista palabras reservadas que el parser reconoce como sintaxis.
# `EXTFILE` define la extension oficial de los scripts gbn.
# `MAX_MEMORY_SLOTS` fija el limite inicial de simbolos por memoria.
# `Value` describe los valores que pueden circular por el interprete.
# `TYPE_MAP` traduce nombres de tipos Gybin a clases Python.
# `SUPPORTED_IMPORT_EXTS` enumera extensiones aceptadas por @use/@from.
# `get_resource_path` resuelve archivos internos tanto en desarrollo como
# dentro de un binario PyInstaller, usando `_MEIPASS` cuando existe.

import sys
from pathlib import Path
from typing import Any

keys: list[str] = ["func", "class", "var",
                   "const", "enum", "$", "if", "elseif",
                   "else", "while", "for", "in",
                   "is", "or", "not", "and", "NULL",
                   "return", "end", "continue", "break", "loop", "try", "catch", "except",
                   "await", "pass", "@use", "@from", "@as", "run", "--", "!*", "#onready",
                   "free", "expand_memory"]

EXTFILE: str = "gbn"
MAX_MEMORY_SLOTS: int = 1024

Value = int | float | str | bool | None | list[Any] | dict[str, Any] | Any

TYPE_MAP: dict[str, type] = {
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "any": object,
    "array": list,
    "dict": dict,
}

SUPPORTED_IMPORT_EXTS: list[str] = [".gbn", ".py", ".h", ".c", ".cpp", ".asm", ".sh", ".bash"]


def get_resource_path(relative_path: str) -> Path:
    """Return the correct path for bundled resources when running under PyInstaller."""
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent
    return base_path / relative_path
