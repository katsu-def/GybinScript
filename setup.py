# setup.py — Build Cython extensions for GybinScript (Termux-friendly)
#
# This script finds Python source files under the Core/ package and builds
# C extensions in-place using Cython. It also installs Core as a Python
# package and includes any .gbn data files found there.
#
# Usage (Termux):
#   pkg install python clang make git
#   python -m pip install --upgrade pip setuptools wheel cython
#   python setup.py build_ext --inplace
#
# Notes:
# - The repo's Python source is expected under the Core/ directory (flat or
#   with subpackages that have __init__.py).
# - If you want to build a single module you can adapt the "extensions"
#   list below.
# - To include extra data files in a PyInstaller build, either pass
#     --add-data "Core/stdutils.gbn:Core"
#   or update the .spec file with datas=[('Core/stdutils.gbn','Core')].

from setuptools import setup, Extension, find_packages
from Cython.Build import cythonize
import os
import glob
import sys

HERE = os.path.abspath(os.path.dirname(__file__))
CORE_DIR = os.path.join(HERE, 'Core')

# Helper: collect python/pyx files under Core (non-private)
pyfiles = []
for root, dirs, files in os.walk(CORE_DIR):
    # treat directories as packages only if they have __init__.py
    if root != CORE_DIR and '__init__.py' not in files:
        # Skip package-like subdirs without __init__.py (not packages)
        continue
    for f in files:
        if f.endswith('.py') or f.endswith('.pyx'):
            if f.startswith('_'):
                # skip private modules by default
                continue
            pyfiles.append(os.path.join(root, f))

extensions = []
for path in pyfiles:
    # module name: Core.sub.path.module
    rel = os.path.relpath(path, HERE)
    mod_path = os.path.splitext(rel)[0].replace(os.path.sep, '.')
    # Example: Core/foo.py -> Core.foo
    extensions.append(Extension(mod_path, [rel]))

# If nothing found, provide an example extension (user can edit manually)
if not extensions:
    # Fallback: user can adapt this to point at the real module
    extensions = [
        Extension('Core.example', ['Core/example.py']),
    ]

# Cythonize extensions with Python3 language level
ext_modules = cythonize(extensions, compiler_directives={'language_level': '3'})

# Include any .gbn files inside Core as package data (e.g. stdutils.gbn)
package_data = {}
# glob for gbn files under Core (non-recursive at package root) and include them
gbn_files = []
if os.path.isdir(CORE_DIR):
    for p in glob.glob(os.path.join(CORE_DIR, '*.gbn')):
        gbn_files.append(os.path.basename(p))
    if gbn_files:
        package_data['Core'] = gbn_files

setup(
    name='GybinScript-Cythonized',
    version='0.1',
    description='GybinScript — Cython build helpers',
    packages=find_packages(where='.'),
    ext_modules=ext_modules,
    package_data=package_data,
    include_package_data=bool(package_data),
    zip_safe=False,
)
