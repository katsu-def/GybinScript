#!/usr/bin/env python3

from __future__ import annotations

# ALL:
# Este archivo es el punto de entrada principal por consola.
# Ajusta `sys.path` cuando se ejecuta como `python3 Core/Parser.py`.
# Importa `engine` y reexporta su API para conservar compatibilidad.
# Construye y procesa argumentos como `--sm`, `--trace`, `--c`, `--nc`.
# Valida el archivo `.gbn`, carga `stdutils.gbn` y ejecuta el programa.
# Gestiona errores, resumen de memoria, warnings, compilacion y tiempos.
# La logica del lenguaje se encuentra en `engine.py`; este archivo coordina CLI.

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Core import engine
from Core.engine import *  # Re-export the interpreter API for older imports.


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="Core.Compiler",
        description=f"Reads and processes .{engine.EXTFILE} files with static typing and managed memory",
    )
    parser.add_argument("file", help=f"Path to the .{engine.EXTFILE} file to process")
    parser.add_argument("--sm", action="store_true",
                        help="Show memory state after execution")
    parser.add_argument("--pr", action="store_true",
                        help="Print automatically all values returned by return")
    parser.add_argument("--t", action="store_true",
                        help="Show execution time")
    parser.add_argument("--tr", action="store_true",
                        help="Show executed lines (only with trace) and not normal output")
    parser.add_argument("--c", action="store_true",
                        help="Compile the script into an executable wrapper if there are no errors")
    parser.add_argument("--fc", action="store_true",
                        help="Compile the script even if errors occur")
    parser.add_argument("--w", action="store_true",
                        help="Enable warning messages")
    parser.add_argument("--nc", action="store_true",
                        help="No console: suppress all stdout output (stderr/errors still shown)")
    return parser


def apply_runtime_flags(args: argparse.Namespace) -> None:
    engine.SHOW_MEMORY = args.sm
    engine.SHOW_RETURNS = args.pr
    engine.TRACE = args.tr
    engine.WARNINGS = args.w


def redirect_stdout_for_no_console(no_console: bool) -> Any:
    original_stdout = sys.stdout
    if no_console:
        sys.stdout = open(os.devnull, "w")
    return original_stdout


def restore_stdout_for_no_console(no_console: bool, original_stdout: Any) -> None:
    if no_console:
        sys.stdout.close()
        sys.stdout = original_stdout


def validate_program_path(file_name: str) -> Path:
    path = Path(file_name)
    if not path.exists():
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(2)

    if path.suffix.lstrip(".").lower() != engine.EXTFILE.lower():
        print(f"Error: Invalid extension. Expected .{engine.EXTFILE}", file=sys.stderr)
        sys.exit(3)
    return path


def load_standard_library() -> None:
    stdutils_path = engine.get_resource_path("stdutils.gbn")
    if stdutils_path.exists():
        names_before = set(engine.memory._slots.keys())
        engine.execute_use(stdutils_path, engine.memory)
        # Mark every symbol introduced by the standard library so that
        # emit_post_execution_warnings() can skip them silently.
        engine.STDLIB_SYMBOLS.update(engine.memory._slots.keys() - names_before)


def execute_program_file(path: Path, args: argparse.Namespace) -> tuple[bool, float | None]:
    lines = engine.read_lines(str(path))
    start_time = time.perf_counter() if args.t else None
    had_error = False
    try:
        engine.process_source_lines(lines, engine.memory, path.parent, trace=args.tr, source_path=path)
    except Exception as exc:
        had_error = True
        print(f"Error: {exc}", file=sys.stderr)
        if args.fc:
            if engine.WARNINGS:
                print("Warning: forcing compilation despite errors", file=sys.stderr)
        else:
            raise
    return had_error, start_time


def exit_after_execution_error(args: argparse.Namespace, original_stdout: Any) -> None:
    if engine.SHOW_MEMORY:
        print("Total memory:", engine.memory.summary(), file=sys.stderr)
    engine.memory._slots.clear()
    restore_stdout_for_no_console(args.nc, original_stdout)
    sys.exit(1)


def emit_memory_summary() -> None:
    if engine.SHOW_MEMORY:
        print("Total memory:", engine.memory.summary())


def maybe_compile_program(path: Path, args: argparse.Namespace, had_error: bool) -> None:
    if not (args.c or args.fc):
        return
    if args.c and had_error and not args.fc:
        print("Compilation skipped because errors were detected.", file=sys.stderr)
        return
    exe_path = engine.compile_to_executable(path)
    print(f"Executable generated: {exe_path}")


def maybe_print_execution_time(args: argparse.Namespace, start_time: float | None) -> None:
    if args.t and start_time is not None:
        elapsed = time.perf_counter() - start_time
        print(f"Executed time: {elapsed:.6f}s", file=sys.stderr if args.nc else sys.stdout)


def finish_program(path: Path, args: argparse.Namespace, had_error: bool, start_time: float | None, original_stdout: Any) -> None:
    emit_memory_summary()
    engine.emit_post_execution_warnings(engine.memory, source_path=path)
    engine._gc_release_unused(engine.memory)
    maybe_compile_program(path, args, had_error)
    maybe_print_execution_time(args, start_time)
    engine.memory._slots.clear()
    restore_stdout_for_no_console(args.nc, original_stdout)


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()
    apply_runtime_flags(args)

    path = validate_program_path(args.file)
    load_standard_library()

    original_stdout = redirect_stdout_for_no_console(args.nc)
    try:
        had_error, start_time = execute_program_file(path, args)
    except Exception:
        exit_after_execution_error(args, original_stdout)
        return
    finish_program(path, args, had_error, start_time, original_stdout)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram stopped: KeyInterrupt")
