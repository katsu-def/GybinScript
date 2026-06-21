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
                   "#reserved", "free", "expand_memory"]

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


def get_install_root() -> Path:
    """Base directory used to resolve files that live OUTSIDE the bundle/source tree
    and that the end user controls — currently the starting point for `libs/`
    discovery (see find_libs_dir()) and the external (visible) copy of
    `stdutils.gbn` (see get_resource_path()).

    - Frozen PyInstaller build: the directory containing the actual executable on
      disk (`sys.executable`). NEVER `sys._MEIPASS`: that's a private temp folder
      re-extracted (and deleted) on every run of a onefile build, so it can never
      hold a `libs/` directory the end user placed next to their copy of the program.
    - Running from source: the parent of this package's directory (the repository
      root, so `libs/` sits next to `Core/`) — matches get_resource_path()'s
      non-frozen behavior.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def find_libs_dir(start: Path | None = None, max_levels: int = 6) -> Path | None:
    """Walk upward from `start` (default: get_install_root()) looking for a `libs/`
    directory — the same way tools like git discover their repo root by walking up
    from wherever they're invoked. This keeps bare `@use name` imports working
    whether `libs/` sits directly next to the compiled executable, or one (or a few)
    levels higher — e.g. when the binary is placed inside its own subfolder (such as
    a "Core/" distribution folder) while `libs/` stays at the project root, mirroring
    the source-tree layout. Stops after `max_levels` parent directories so a missing
    `libs/` folder fails fast instead of scanning the whole filesystem.
    """
    current = start if start is not None else get_install_root()
    for _ in range(max_levels):
        candidate = current / "libs"
        if candidate.is_dir():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def get_resource_path(relative_path: str) -> Path:
    """Return the path to a resource shipped with the interpreter (currently just
    `stdutils.gbn`).

    - Running from source: same folder as this module (Core/), as before.
    - Frozen build: prefer the copy sitting next to the actual executable on disk
      (see get_install_root()) over anything embedded in the bundle. This keeps
      `stdutils.gbn` a plain, visible, editable text file that ships alongside the
      executable instead of being hidden inside it — anyone can open and read the
      standard library source. Falls back to the bundled `_MEIPASS` copy only if no
      external copy is found (e.g. an older build that still embeds it via
      `--add-data`).
    """
    if getattr(sys, "frozen", False):
        external_path = get_install_root() / relative_path
        if external_path.exists():
            return external_path
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).resolve().parent / relative_path
