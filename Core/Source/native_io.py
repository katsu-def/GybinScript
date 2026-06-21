from __future__ import annotations

# ALL:
# Este archivo contiene las funciones de entrada/salida de archivos.
# Las funciones `_builtin_file_*` se exponen al lenguaje como
# built-ins disponibles desde memoria global.
# `BUILTIN_FUNCTIONS` junta built-ins Python seguros y los helpers de I/O.
# `read_file` y `read_lines` son utilidades internas del interprete para
# cargar scripts `.gbn` y modulos importados sin mezclarlo con el parser.

from pathlib import Path
from typing import Any


def _builtin_file_read(path: str) -> str:
    """Read the entire content of a file as a string."""
    return Path(path).read_text(encoding="utf-8")


def _builtin_file_lines(path: str) -> list:
    """Read a file and return its lines as an array (newlines stripped)."""
    return Path(path).read_text(encoding="utf-8").splitlines()


def _builtin_file_write(path: str, content: str) -> None:
    """Write (overwrite) a file with the given string content."""
    Path(path).write_text(content, encoding="utf-8")


def _builtin_file_append(path: str, content: str) -> None:
    """Append string content to a file (creates it if it does not exist)."""
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(content)


def _builtin_file_exists(path: str) -> bool:
    """Return True if the file exists, False otherwise."""
    return Path(path).exists()


BUILTIN_FUNCTIONS: dict[str, Any] = {
    "print": print,
    "_input": input,
    "int": int,
    "float": float,
    "str": str,
    "bool": bool,
    "range": range,
    "len": len,
    "file_read": _builtin_file_read,
    "file_lines": _builtin_file_lines,
    "file_write": _builtin_file_write,
    "file_append": _builtin_file_append,
    "file_exists": _builtin_file_exists,
}


def read_file(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def read_lines(file_path: str) -> list[str]:
    lines: list[str] = []
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            lines.append(line)
    return lines
