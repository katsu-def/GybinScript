
# (C) 2025 - 2026 Kātsu D. <jensaki152@gmail.com>

# ALL:
# Este archivo contiene las funciones de entrada/salida de archivos.
# Las funciones `_builtin_file_*` se exponen al lenguaje como
# built-ins disponibles desde memoria global.
# `BUILTIN_FUNCTIONS` junta built-ins Python seguros y los helpers de I/O.
# `read_file` y `read_lines` son utilidades internas del interprete para
# cargar scripts `.gbn` y modulos importados sin mezclarlo con el parser.

from __future__ import annotations

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


def _builtin_reprint(*args: Any, sep: str = " ", end: str = "", flush: bool = True, **kwargs: Any) -> None:
    """Alternative to $print for status/progress output: overwrites the current
    terminal line in place instead of starting a new one on every call, without
    the caller having to spell out `\\r` (and an ANSI clear) by hand every time
    the way a plain `$print` would need.

    Defaults to no trailing newline (`end=""`) so the NEXT call keeps overwriting
    the same line, and flushes immediately since there's no newline left to
    trigger the usual auto-flush. Pass `end="\\n"` to finish the live line and
    return to normal line-by-line output afterwards — with that override this
    behaves exactly like a regular `$print`, so nothing is lost by using it
    everywhere `$print` would otherwise go.
    """
    text = sep.join(str(arg) for arg in args)
    # "\x1b[K" clears anything left over from a longer previous call on this same
    # line (e.g. going from "99%" down to "5%" without a stray "9%" tail).
    print(f"\r{text}\x1b[K", end=end, flush=flush, **kwargs)


BUILTIN_FUNCTIONS: dict[str, Any] = {
    "print": print,
    "reprint": _builtin_reprint,
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


def _net_bracket_depth(line: str) -> int:
    """Net change in (), [], {} nesting depth contributed by one physical line's real
    code. Ignores bracket characters inside string literals and anything after a `--`
    line comment — same string/comment-aware character scan as Core.source_tools's
    strip_comments(), just counting brackets instead of building a stripped string
    (duplicated here rather than imported, since it's small and this keeps
    native_io.py's only dependency being stdlib)."""
    depth = 0
    in_string: str | None = None
    i = 0
    while i < len(line):
        char = line[i]
        if in_string is not None:
            if char == in_string and (i == 0 or line[i - 1] != "\\"):
                in_string = None
            i += 1
            continue
        if char in ('"', "'"):
            in_string = char
            i += 1
            continue
        if line.startswith("--", i):
            break
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        i += 1
    return depth


def _join_continuation_lines(lines: list[str]) -> list[str]:
    """A statement whose (), [], {} aren't balanced yet by the end of its physical
    line — a dict/array literal or a call's argument list spread across several
    lines for readability — gets joined with however many following physical lines
    it takes to balance out, so the rest of the interpreter (which parses and
    dispatches one physical line at a time) sees one complete logical line, exactly
    as if it had been written on one line to begin with.

    The returned list has the SAME LENGTH as `lines`, with each entry still at its
    original index: a physical line consumed into an earlier one becomes blank in
    its own slot rather than being removed. Every error message, `--tr` trace line,
    and `defined_line` elsewhere keeps pointing at the real file line as a result —
    this only changes what CONTENT dispatch sees at the line where a joined
    statement begins, never the line numbering itself.
    """
    result = list(lines)
    total = len(result)
    i = 0
    while i < total:
        text = result[i]
        stripped = text.strip()
        if not stripped or stripped.startswith("--") or stripped.startswith("!*"):
            i += 1
            continue
        depth = _net_bracket_depth(text)
        if depth <= 0:
            i += 1
            continue
        had_newline = text.endswith("\n")
        pieces = [text.rstrip("\n")]
        j = i
        while depth > 0 and j + 1 < total:
            j += 1
            next_line = result[j]
            pieces.append(next_line.strip())
            depth += _net_bracket_depth(next_line)
            result[j] = "\n" if next_line.endswith("\n") else ""
        result[i] = " ".join(pieces) + ("\n" if had_newline else "")
        i += 1
    return result


def read_lines(file_path: str) -> list[str]:
    lines: list[str] = []
    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            lines.append(line)
    return _join_continuation_lines(lines)
