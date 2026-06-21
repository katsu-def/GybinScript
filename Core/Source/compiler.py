from __future__ import annotations

# ALL:
# Este archivo encapsula la generacion de ejecutables.
# `_create_wrapper_executable` crea un wrapper bash cuando PyInstaller no
# esta disponible o falla; el wrapper siempre ejecuta `Core/Gybin.py`.
# `_write_pyinstaller_stub` genera un script temporal que carga el `.gbn`
# embebido y delega la ejecucion al entrypoint principal.
# `compile_to_executable` intenta construir un binario onefile con
# PyInstaller y vuelve al wrapper si algo no se puede completar.
# `stdutils.gbn` NUNCA se embebe en el binario: se copia como archivo de
# texto plano junto al ejecutable final, para que cualquiera pueda leerla
# o editarla (ver get_resource_path en runtime.py).
# El motor solo llama a esta capa; no necesita conocer detalles del build.

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from Core.runtime import find_libs_dir, get_resource_path


def _interpreter_invocation() -> list[str]:
    """Command used to re-invoke this interpreter on a .gbn script.

    - Frozen standalone build: re-run the actual compiled executable itself
      (`sys.executable`) — a real, persistent file on disk. We deliberately do NOT
      use `__file__` here: under PyInstaller it points inside `_MEIPASS`, a private
      temp folder that's wiped as soon as this process exits, so a wrapper script
      written against it would already be broken by the time anyone runs it.
    - Running from source: fall back to `python3 Core/Gybin.py`, same as before.
    """
    if getattr(sys, "frozen", False):
        return [sys.executable]
    parser_path = Path(__file__).resolve().with_name("Gybin.py")
    return ["python3", str(parser_path)]


def _create_wrapper_executable(gbn_path: Path) -> Path:
    executable_path = gbn_path.with_suffix("")
    invocation = " ".join(f'"{part}"' for part in _interpreter_invocation())
    wrapper = f"#!/usr/bin/env bash\nexec {invocation} \"{gbn_path.resolve()}\" \"$@\"\n"
    executable_path.write_text(wrapper, encoding="utf-8")
    executable_path.chmod(executable_path.stat().st_mode | 0o111)
    return executable_path


def _write_pyinstaller_stub(stub_path: Path, payload_name: str) -> None:
    stub_code = f"""#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

PAYLOAD_NAME = {payload_name!r}


def get_base_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def main() -> None:
    base_path = get_base_path()
    payload_path = base_path / PAYLOAD_NAME
    if not payload_path.exists():
        raise FileNotFoundError(f"Embedded script not found: {payload_name}")
    sys.argv = [sys.argv[0], str(payload_path)] + sys.argv[1:]
    import Core.Gybin as parser
    parser.main()


if __name__ == "__main__":
    main()
"""
    stub_path.write_text(stub_code, encoding="utf-8")


def _resolve_lib_path(path_text: str, current_dir: Path) -> Path | None:
    """Mirror engine.resolve_path() to find .gbn imports at compile time.

    Always returns a fully resolved (absolute, canonical) Path or None.
    Search order mirrors engine.resolve_path() exactly:
      1. Relative to current_dir (with or without extension)
      2. libs/ directory found by walking up from the installation (see find_libs_dir())
    """
    SUPPORTED_EXTS = [".gbn", ".py", ".h", ".c", ".cpp", ".asm", ".sh", ".bash"]

    candidate = Path(path_text)
    if not candidate.is_absolute():
        candidate = current_dir / candidate

    # Already has an extension and exists
    if candidate.suffix and candidate.exists():
        return candidate.resolve()

    # Try appending each supported extension
    base = candidate.with_suffix("")
    for ext in SUPPORTED_EXTS:
        c = base.with_suffix(ext)
        if c.exists():
            return c.resolve()

    # Mirror engine: search libs/ by walking up from the installation (never
    # __file__-relative — that breaks once this very process is itself a frozen
    # executable; see find_libs_dir()).
    # Strip leading dots from bare names (e.g. ".sys" -> "sys") before searching
    bare_name = Path(path_text).name.lstrip(".")
    stem_only = Path(bare_name).stem if Path(bare_name).suffix else bare_name
    if "/" not in path_text and stem_only:
        if stem_only.lower() != "stdutils":
            libs_dir = find_libs_dir()
            if libs_dir is not None:
                for ext in SUPPORTED_EXTS:
                    c = libs_dir / (stem_only + ext)
                    if c.exists():
                        return c.resolve()

    return None


def _collect_imported_gbn_libs(gbn_path: Path) -> list[Path]:
    """Recursively scan a .gbn script for @use/@from statements and collect ALL
    transitive .gbn dependencies, following the same search order as engine.resolve_path().

    This handles chains like: main.gbn -> time.gbn -> sys.gbn -> ...
    Each discovered library is itself scanned, so deep dependency trees are fully captured.
    """
    import re as _re

    main_key = str(gbn_path.resolve())

    collected: list[Path] = []       # ordered list of deps to bundle (excludes main script)
    visited: set[str] = set()        # canonical paths already processed
    queue: list[Path] = [gbn_path.resolve()]

    while queue:
        current = queue.pop(0)
        key = str(current)
        if key in visited:
            continue
        visited.add(key)

        # Collect every resolved file except the main payload (it's added separately)
        if key != main_key:
            collected.append(current)

        # Only .gbn files can contain further @use/@from imports worth scanning
        if current.suffix.lower() != ".gbn":
            continue

        # Read the file and scan for import statements
        try:
            text = current.read_text(encoding="utf-8")
        except Exception:
            continue

        for raw_line in text.splitlines():
            stripped = raw_line.strip()

            # Skip comment lines so we don't follow commented-out imports
            if stripped.startswith("--") or stripped.startswith("!*"):
                continue

            # Match @use <path> or @from <path> [@as alias]
            m = _re.match(r'^@(?:use|from)\s+(\S+)', stripped)
            if not m:
                continue

            raw_path = m.group(1).strip("'\"").strip()

            # Resolve using the same logic as engine, with current file's dir as base
            resolved = _resolve_lib_path(raw_path, current.parent)
            if resolved is None:
                # Not found at compile time — skip (engine will error at runtime if missing)
                continue

            # Bundle all supported file types (.gbn, .py, .h, .c, .cpp, .asm, .sh, .bash)
            if str(resolved) not in visited:
                queue.append(resolved)  # .gbn files will also be scanned for their own deps

    return collected


def compile_to_executable(gbn_path: Path) -> Path:
    executable_path = gbn_path.with_suffix("")

    if getattr(sys, "frozen", False):
        # This interpreter is itself a frozen, standalone build: there is no Core/
        # source tree on disk for a fresh PyInstaller invocation to analyze and
        # bundle (only this process's own embedded bytecode), and there is no
        # guarantee a `pyinstaller` toolchain (or even Python) exists on this
        # machine at all — that's the whole point of shipping standalone. Always
        # fall back to the wrapper, which simply re-invokes this same executable.
        print(
            "Note: this is a standalone build, so only a wrapper executable "
            "(re-invoking this same program) will be created.",
            file=sys.stderr,
        )
        return _create_wrapper_executable(gbn_path)

    pyinstaller_exe = shutil.which("pyinstaller")
    if pyinstaller_exe is None:
        print("Warning: PyInstaller not found. Only a bash wrapper executable will be created.", file=sys.stderr)
        return _create_wrapper_executable(gbn_path)

    spec_root = Path(__file__).resolve().parent.parent
    stdutils_path = get_resource_path("stdutils.gbn")

    # Discover all imported libraries recursively (all supported types, including transitive deps)
    imported_libs = _collect_imported_gbn_libs(gbn_path)
    # Also scan stdutils for transitive deps so its dependencies get bundled too
    if stdutils_path.exists():
        stdutils_deps = _collect_imported_gbn_libs(stdutils_path)
        already = {str(p) for p in imported_libs}
        for dep in stdutils_deps:
            if str(dep) not in already and dep != stdutils_path.resolve():
                imported_libs.append(dep)
                already.add(str(dep))
    if imported_libs:
        lib_names = ", ".join(p.name for p in imported_libs)
        print(f"Bundling {len(imported_libs)} imported library/libraries: {lib_names}", file=sys.stderr)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        payload_name = gbn_path.name
        payload_path = temp_dir_path / payload_name
        payload_path.write_text(gbn_path.read_text(encoding="utf-8"), encoding="utf-8")

        stub_path = temp_dir_path / "run_gybin.py"
        _write_pyinstaller_stub(stub_path, payload_name)

        dist_dir = temp_dir_path / "dist"
        build_dir = temp_dir_path / "build"
        spec_dir = temp_dir_path / "spec"

        cmd = [
            pyinstaller_exe,
            "--onefile",
            "--name",
            executable_path.name,
            "--distpath",
            str(dist_dir),
            "--workpath",
            str(build_dir),
            "--specpath",
            str(spec_dir),
            "--add-data",
            f"{payload_path}{os.pathsep}.",
        ]

        # Bundle each imported library (all supported types) into the executable
        for lib_path in imported_libs:
            cmd += ["--add-data", f"{lib_path}{os.pathsep}."]

        cmd += [
            "--paths",
            str(spec_root),
            str(stub_path),
        ]

        try:
            subprocess.run(cmd, cwd=str(temp_dir_path), check=True, capture_output=True)
        except subprocess.CalledProcessError as exc:
            print("PyInstaller failed, falling back to wrapper executable.", file=sys.stderr)
            if exc.stderr:
                print(exc.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
            return _create_wrapper_executable(gbn_path)

        built_exe = dist_dir / executable_path.name
        if not built_exe.exists():
            raise FileNotFoundError("PyInstaller build output not found")

        shutil.copy2(built_exe, executable_path)
        executable_path.chmod(executable_path.stat().st_mode | 0o111)

        # stdutils.gbn is deliberately NOT embedded (see get_resource_path()): copy it
        # next to the compiled executable as a plain, readable, editable text file.
        if stdutils_path.exists():
            stdutils_dest = executable_path.parent / stdutils_path.name
            shutil.copy2(stdutils_path, stdutils_dest)
            print(f"Standard library kept as a separate file: {stdutils_dest}", file=sys.stderr)

        return executable_path
