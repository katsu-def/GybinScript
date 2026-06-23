from __future__ import annotations

# ALL:
# Este archivo encapsula la generacion de ejecutables.
# `_create_wrapper_executable` crea un wrapper cuando PyInstaller no esta
# disponible o falla; el wrapper siempre ejecuta `Core/Gybin.py`. En Windows
# genera un `.bat` (ver `_create_windows_wrapper`); en cualquier otro sistema
# genera un script bash (ver `_create_unix_wrapper`).
# `_bundle_dependencies_for_wrapper` copia (plano, por nombre de archivo) todas
# las dependencias `@use`/`@from` transitivas del script junto al wrapper, y
# este exporta GYBIN_BUNDLE_DIR para que el motor las siga encontrando aunque
# el `libs/` original del proyecto no exista en la maquina donde se ejecute
# (ver get_bundled_libs_dir en runtime.py y resolve_path en engine.py).
# `_find_source_tree_root` busca, partiendo de la ubicacion real (persistente)
# del ejecutable, un `Core/engine.py` genuino en disco — presente en una
# instalacion normal (setup-linux copia el proyecto completo, fuente incluida,
# junto al binario `Gybin` compilado dentro de `Core/`), pero ausente cuando lo
# que corre es un script de usuario ya compilado de forma aislada. Esto permite
# que `--c` compile de verdad con PyInstaller incluso desde un `Gybin`
# congelado, en lugar de rendirse siempre al wrapper.
# `_write_pyinstaller_stub` genera un script temporal que carga el `.gbn`
# embebido y delega la ejecucion al entrypoint principal.
# `compile_to_executable` intenta construir un binario onefile con
# PyInstaller y vuelve al wrapper si algo no se puede completar.
# `stdutils.gbn` se embebe en el binario como red de seguridad (para quien
# comparta solo el ejecutable, sin Gybin instalado), y TAMBIEN se copia como
# archivo de texto plano junto al ejecutable final, para que cualquiera pueda
# leerla o editarla — get_resource_path() en runtime.py siempre prioriza esa
# copia externa sobre la embebida cuando ambas existen.
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
    - Running from source: fall back to `<python> Core/Gybin.py`. The python
      command name itself is platform-dependent: Windows installs normally only
      register `python` on PATH (no `python3` alias), while POSIX systems use
      `python3` to avoid ambiguity with a possible Python 2 `python`.
    """
    if getattr(sys, "frozen", False):
        return [sys.executable]
    parser_path = Path(__file__).resolve().with_name("Gybin.py")
    python_cmd = "python" if os.name == "nt" else "python3"
    return [python_cmd, str(parser_path)]


def _create_wrapper_executable(gbn_path: Path) -> Path:
    """Dispatch to the platform-appropriate wrapper.

    Windows has no concept of the POSIX executable bit nor of shebang lines, and
    `cmd.exe`/Explorer only treat `.bat`/`.cmd`/`.exe` as runnable — a file with
    bash syntax and no extension would just sit there unrunnable. So on Windows
    we emit a `.bat`; everywhere else (Linux, macOS) we keep the existing bash
    wrapper, which is directly executable once chmod'ed.
    """
    if os.name == "nt":
        return _create_windows_wrapper(gbn_path)
    return _create_unix_wrapper(gbn_path)


def _create_unix_wrapper(gbn_path: Path) -> Path:
    executable_path = gbn_path.with_suffix("")
    bundle_dir = _bundle_dependencies_for_wrapper(gbn_path)
    invocation = " ".join(f'"{part}"' for part in _interpreter_invocation())
    env_line = f'export GYBIN_BUNDLE_DIR="{bundle_dir}"\n' if bundle_dir is not None else ""
    wrapper = f"#!/usr/bin/env bash\n{env_line}exec {invocation} \"{gbn_path.resolve()}\" \"$@\"\n"
    executable_path.write_text(wrapper, encoding="utf-8")
    executable_path.chmod(executable_path.stat().st_mode | 0o111)
    return executable_path


def _create_windows_wrapper(gbn_path: Path) -> Path:
    # Unlike Unix, Windows needs a recognized extension to actually be runnable
    # (double-click or bare `name` in cmd.exe) — a bare, extension-less file is
    # just inert data to it, so `.bat` here is not cosmetic, it's required.
    executable_path = gbn_path.with_suffix(".bat")
    bundle_dir = _bundle_dependencies_for_wrapper(gbn_path)
    invocation = " ".join(f'"{part}"' for part in _interpreter_invocation())
    env_line = f'set "GYBIN_BUNDLE_DIR={bundle_dir}"\r\n' if bundle_dir is not None else ""
    # `%*` forwards all arguments through, mirroring "$@" in the bash wrapper.
    # CRLF line endings, since plain "\n" in a .bat can confuse some legacy
    # Windows command-line tooling even though modern cmd.exe tolerates it.
    wrapper = f'@echo off\r\n{env_line}{invocation} "{gbn_path.resolve()}" %*\r\n'
    executable_path.write_text(wrapper, encoding="utf-8", newline="")
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


def _bundle_dependencies_for_wrapper(gbn_path: Path) -> Path | None:
    """Copy every transitively-imported .gbn/.py/etc. dependency of `gbn_path`
    flat (by basename) into a dedicated `<script-stem>_libs/` folder next to it
    — the exact same flat-by-basename scheme `compile_to_executable` already
    uses for PyInstaller's `--add-data`/`_MEIPASS` — so the wrapper keeps
    resolving @use/@from targets even when the project's own `libs/` tree isn't
    present on whatever machine ends up running it (see
    runtime.get_bundled_libs_dir() and resolve_path() in engine.py for the
    matching lookup).

    Returns the bundle directory's resolved path, or None (copying nothing)
    when the script has no imports to bundle — so dependency-free scripts get
    no extra folder and behave exactly as before this existed.
    """
    imported_libs = _collect_imported_gbn_libs(gbn_path)
    if not imported_libs:
        return None

    bundle_dir = gbn_path.parent / f"{gbn_path.stem}_libs"
    bundle_dir.mkdir(exist_ok=True)
    for lib_path in imported_libs:
        # Flat by basename, same as the PyInstaller bundle: two deps that
        # share a basename but came from different folders would collide here
        # exactly like they would inside a frozen `_MEIPASS` bundle.
        shutil.copy2(lib_path, bundle_dir / lib_path.name)

    lib_names = ", ".join(p.name for p in imported_libs)
    print(
        f"Bundling {len(imported_libs)} imported library/libraries next to the wrapper: {lib_names}",
        file=sys.stderr,
    )
    return bundle_dir.resolve()


def _find_source_tree_root(start: Path, max_levels: int = 4) -> Path | None:
    """Walk upward from `start` looking for a directory whose `Core/` subfolder
    holds the package's real, importable .py source on disk (engine.py used as
    the marker file) — mirrors find_libs_dir()'s upward walk in runtime.py,
    just looking for the source tree instead of a `libs/` folder. Returns the
    directory that actually CONTAINS that source (which may be `Core/` itself,
    or `Core/Source/` — see below), or None if nothing turns up.

    This is the piece that lets `compile_to_executable` tell apart different
    "frozen" situations:
    - A normally-installed `Gybin` (e.g. `/opt/GybinScript/Core/Gybin`, with
      `setup-linux` having copied the *whole* project — source included —
      alongside it) where the .py files sit directly in `Core/`: found at
      level 0, returns `Core/` itself.
    - The same kind of install, but where the source has been tidied away into
      a `Core/Source/` subfolder (a common local convention: keep `Core/`
      itself down to just the compiled `Gybin` binary + `stdutils.gbn`, and
      only pull the .py files back out into `Core/` directly while actively
      developing): found one level deeper, returns `Core/Source/`.
    - A standalone *script* executable compiled in isolation (no project tree
      travels with it, e.g. living alone in some user's folder): nothing is
      found within `max_levels`, so the caller correctly still falls back to
      the wrapper.
    """
    current = start
    for _ in range(max_levels):
        core_dir = current / "Core"
        if (core_dir / "engine.py").is_file():
            return core_dir
        tucked_away = core_dir / "Source"
        if (tucked_away / "engine.py").is_file():
            return tucked_away
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _prepare_spec_root(temp_dir_path: Path, package_dir: Path) -> Path:
    """Return a directory to hand PyInstaller as `--paths` so `import
    Core.Gybin` resolves inside the stub. When `package_dir` is already
    literally named `Core` (running from source, or a frozen install where the
    source wasn't tucked away), its own parent already works directly — same
    as before this existed. Otherwise `package_dir` is the user's own
    `Core/Source/` tuck-away folder: its *contents* are the real package, but
    its *name* doesn't match what every internal `from Core.x import y`
    expects, so we build a small shim inside our own temp build dir — a `Core`
    symlink pointing at the real files (falling back to a full copy if
    symlinks aren't available, e.g. unprivileged Windows) — and use that shim
    directory as `--paths` instead.
    """
    if package_dir.name == "Core":
        return package_dir.parent

    shim_root = temp_dir_path / "_source_shim"
    shim_root.mkdir(exist_ok=True)
    shim_core = shim_root / "Core"
    try:
        shim_core.symlink_to(package_dir, target_is_directory=True)
    except OSError:
        shutil.copytree(package_dir, shim_core)
    return shim_root


def _resolve_pyinstaller_build_inputs(gbn_path: Path) -> tuple[str, Path] | None:
    """Decide whether a *fresh* PyInstaller build is actually possible right
    now, and if so return (pyinstaller_executable, package_dir) — the
    directory that actually holds the real `Core` package source on disk (see
    `_prepare_spec_root` for how this becomes a usable `--paths`). Returns None
    when it isn't possible, telling the caller to fall back to the wrapper
    instead:

    - No `pyinstaller` on PATH at all (source or frozen, doesn't matter).
    - Running from source: the package dir is simply this file's own directory
      (`Core/`), exactly as before.
    - Running as a frozen, standalone build: `__file__` itself points inside
      the ephemeral `_MEIPASS` (wiped the moment this process exits), useless
      as a base. Instead we look for a real source tree on disk next to the
      actual executable file via `_find_source_tree_root()` — present in a
      normal install, absent for an isolated compiled script.
    """
    pyinstaller_exe = shutil.which("pyinstaller")
    if pyinstaller_exe is None:
        return None

    if not getattr(sys, "frozen", False):
        return pyinstaller_exe, Path(__file__).resolve().parent

    package_dir = _find_source_tree_root(Path(sys.executable).resolve().parent)
    if package_dir is None:
        return None
    return pyinstaller_exe, package_dir


def compile_to_executable(gbn_path: Path) -> Path:
    # PyInstaller's own --onefile output is always "<name>.exe" on Windows and a
    # bare "<name>" everywhere else; `output_stem` is what we hand to PyInstaller
    # via --name (extension-less, since PyInstaller appends ".exe" itself on
    # Windows), while `executable_path` is the final installed path we actually
    # write to — it needs the ".exe" suffix on Windows or it won't be runnable.
    output_stem = gbn_path.with_suffix("")
    executable_path = output_stem.with_suffix(".exe") if os.name == "nt" else output_stem

    build_inputs = _resolve_pyinstaller_build_inputs(gbn_path)
    if build_inputs is None:
        if getattr(sys, "frozen", False):
            print(
                "Note: no `pyinstaller` on PATH and/or no accompanying Core/ "
                "source tree found next to this standalone build, so only a "
                "wrapper executable (re-invoking this same program) will be created.",
                file=sys.stderr,
            )
        else:
            wrapper_kind = ".bat" if os.name == "nt" else "bash"
            print(f"Warning: PyInstaller not found. Only a {wrapper_kind} wrapper executable will be created.", file=sys.stderr)
        return _create_wrapper_executable(gbn_path)

    pyinstaller_exe, package_dir = build_inputs
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
        spec_root = _prepare_spec_root(temp_dir_path, package_dir)
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
            output_stem.name,
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

        # Embed stdutils.gbn too, as a fallback for whoever ends up with just the
        # compiled binary and nothing else — not every machine that receives a
        # shared executable will have Gybin (or even Core/stdutils.gbn) installed.
        # get_resource_path() already prefers an external, editable copy over this
        # embedded one when both exist (see runtime.py), so this purely adds safety
        # net coverage without taking away anyone's ability to edit the standard
        # library externally — it's still copied as a plain file below too.
        if stdutils_path.exists():
            cmd += ["--add-data", f"{stdutils_path}{os.pathsep}."]

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

        # On Windows, PyInstaller names its --onefile output "<name>.exe" even
        # though we passed --name without an extension; executable_path.name
        # already carries that same ".exe" (see top of function), so this stays
        # correct on every platform without a separate Windows branch here.
        built_exe = dist_dir / executable_path.name
        if not built_exe.exists():
            raise FileNotFoundError("PyInstaller build output not found")

        shutil.copy2(built_exe, executable_path)
        if os.name != "nt":
            # POSIX execute bit; meaningless on Windows, where runnability comes
            # from the ".exe" extension instead, so we skip chmod there.
            executable_path.chmod(executable_path.stat().st_mode | 0o111)

        # stdutils.gbn already got embedded above as a safety net; we ALSO copy it
        # next to the compiled executable as a plain, readable, editable text
        # file, since get_resource_path() always prefers that external copy when
        # it's present — this keeps the "anyone can read/edit the standard
        # library" behavior while no longer requiring people to remember to carry
        # it along whenever they share just the binary.
        if stdutils_path.exists():
            stdutils_dest = executable_path.parent / stdutils_path.name
            shutil.copy2(stdutils_path, stdutils_dest)
            print(f"Standard library embedded, and also kept as an editable file: {stdutils_dest}", file=sys.stderr)

        return executable_path
