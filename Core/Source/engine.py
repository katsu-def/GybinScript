#!/usr/bin/env python3

from __future__ import annotations
# ALL:
# Este es el motor del lenguaje.
# He aquí la memoria, errores, valores de usuario, evaluacion AST,
# ejecucion de bloques y carga de modulos.
# La configuracion compartida viene de `runtime.py`.
# Las funciones nativas de archivos vienen de `native_io.py`.
# Las utilidades puras de sintaxis vienen de `source_tools.py`.
# `Parser.py` es el entrypoint de consola y llama a este motor.
# La compilacion a ejecutable queda aislada en `compiler.py`.

import ast
import re
import sys
import time
import importlib.util
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from Core.compiler import compile_to_executable
from Core.native_io import BUILTIN_FUNCTIONS, read_file, read_lines
from Core.runtime import (
    EXTFILE,
    MAX_MEMORY_SLOTS,
    SUPPORTED_IMPORT_EXTS,
    TYPE_MAP,
    Value,
    find_libs_dir,
    get_resource_path,
    keys,
)
from Core.source_tools import (
    is_blank,
    is_comment,
    parse_annotation,
    parse_annotation_legacy,
    parse_class_header,
    parse_constant_declaration,
    parse_for_header,
    parse_function_header,
    parse_variable_declaration,
    remove_comments,
    replace_pointer_syntax,
    split_call_arguments,
    strip_comments,
)


@dataclass
class MemorySlot:
    name: str
    type_name: str
    value: Value
    immutable: bool = False
    max_size: int | None = None
    element_type: str | None = None
    is_ready: bool = False
    previous_value: Value = None
    allowed_types: list[str] | None = None  # Multi-type support: list of allowed types
    used_types: set[str] | None = None  # Track which types are actually used
    accessed: bool = False           # True once the symbol is read (not just written)
    defined_line: int | None = None  # Source line where this slot was first declared
    assign_count: int = 0            # Number of times the value has been re-assigned
    is_reserved: bool = False        # True if declared with #reserved (private to the class)


class MemoryError(Exception):
    pass


class ReturnSignal(Exception):
    def __init__(self, value: Value) -> None:
        self.value = value


class BreakSignal(Exception):
    pass


class ContinueSignal(Exception):
    pass


class LoopSignal(Exception):
    """Raised by 'loop' keyword to restart the current while/for iteration from the top."""
    pass

class Interrupt(Exception):
    pass

class ParserError(Exception):
    def __init__(self, message: str, file_path: Path | None = None, line: int | None = None, column: int | None = None, original: Exception | None = None) -> None:
        self.file_path = file_path
        self.line = line
        self.column = column
        self.original = original
        super().__init__(message)

    def __str__(self) -> str:
        location = ""
        if self.file_path is not None:
            location = str(self.file_path)
        if self.line is not None:
            location += f":{self.line}"
        if self.column is not None:
            location += f":{self.column}"
        if location:
            return f"{location}: {self.args[0]}"
        return self.args[0]


def _guess_error_column(line: str) -> int:
    stripped = line.lstrip(" \t")
    if not stripped:
        return 1
    return line.index(stripped) + 1


def print_warning(message: str, file_path: Path | None = None, line: int | None = None) -> None:
    """Print a warning message following parser format."""
    if not WARNINGS:
        return
    location = ""
    if file_path is not None:
        location = str(file_path)
    if line is not None:
        location += f":{line}"
    if location:
        print(f"Warning: {location}: {message}", file=sys.stderr)
    else:
        print(f"Warning: {message}", file=sys.stderr)


def _wrap_parser_error(exc: Exception, file_path: Path | None = None, line: int | None = None, column: int | None = None) -> ParserError:
    if isinstance(exc, ParserError):
        return exc
    message = str(exc) or type(exc).__name__
    if isinstance(exc, SyntaxError) and getattr(exc, "offset", None) is not None:
        column = column or exc.offset
    if column is None:
        column = 1
    return ParserError(message, file_path=file_path, line=line, column=column, original=exc)


class MemoryManager:
    def __init__(self, parent: MemoryManager | None = None, max_slots: int = MAX_MEMORY_SLOTS) -> None:
        self.parent = parent
        self.max_slots = max_slots
        self._slots: dict[str, MemorySlot] = {}

    def allocate(self, name: str, type_name: str, value: Value, immutable: bool = False, max_size: int | None = None, element_type: str | None = None, is_ready: bool = False, defined_line: int | None = None, is_reserved: bool = False) -> None:
        if len(self._slots) >= self.max_slots and name not in self._slots:
            raise MemoryError("Memory limit reached")

        if name in self._slots and not is_ready:
            raise NameError(f"Variable already declared: {name}")

        normalized_type = self._validate_type_name(type_name)

        # Track multi-type info for later warning analysis
        allowed_types = None
        if "," in normalized_type:
            allowed_types = [t.strip() for t in normalized_type.split(",")]

        if max_size is not None:
            self._validate_size(normalized_type, value, max_size)

        # Intentar coerción automática entre int y float cuando el tipo objetivo lo permite
        if "," not in normalized_type:
            if normalized_type == "int" and isinstance(value, float):
                if value.is_integer():
                    value = int(value)
                else:
                    raise TypeError(f"Cannot assign float with fractional part to {name}: {normalized_type}")
            if normalized_type == "float" and isinstance(value, int):
                value = float(value)

        if not self._type_matches(normalized_type, value) and normalized_type != "any":
            raise TypeError(f"Cannot assign {type(value).__name__} a {name}: {normalized_type}")

        if element_type is not None:
            self._validate_element_type_spec(element_type)
            self._validate_element_types(normalized_type, value, element_type)

        # Track the type that is actually used (defer infer_type call to avoid circular dependency)
        used_types = set()
        if value is not None and hasattr(value, '__class__') and value.__class__.__name__ not in ('builtin_function_or_method', 'method'):
            try:
                # Only infer type if infer_type is available (it's defined later in the module)
                if 'infer_type' in globals():
                    used_types = {infer_type(value)}
            except:
                used_types = set()

        self._slots[name] = MemorySlot(name=name,type_name=normalized_type, value=value, immutable=immutable, max_size=max_size, element_type=element_type, is_ready=is_ready, previous_value=value, allowed_types=allowed_types, used_types=used_types, defined_line=defined_line, is_reserved=is_reserved)

        # Suspicious conversion warning
        if globals().get("WARNINGS") and "," not in normalized_type and value is not None:
            declared = normalized_type
            actual = infer_type(value) if 'infer_type' in globals() else None
            # Only compare against primitive declared types: class-name/enum-name
            # annotations are validated precisely via _type_matches/_validate_class_annotation,
            # and their runtime representation (dict/int) never matches the declared name itself.
            if actual and declared in TYPE_MAP and declared != "any" and actual != declared:
                # int->float coercion is intentional and silent; report others
                if not (declared == "float" and actual == "int"):
                    print_warning(
                        f"'{name}' declared as '{declared}' but initial value is '{actual}'",
                        line=defined_line,
                    )

    def assign(self, name: str, value: Value, type_name: str | None = None) -> None:
        if name in self._slots:
            slot = self._slots[name]
            if slot.immutable:
                raise TypeError(f"Immutable constant: {name}")
            target_type = type_name or slot.type_name
            normalized_type = self._validate_type_name(target_type)

            # Track the type being used for this variable
            if slot.used_types is None:
                slot.used_types = set()
            actual_type = infer_type(value)
            slot.used_types.add(actual_type)

            # Suspicious conversion warning
            if globals().get("WARNINGS") and "," not in normalized_type and value is not None:
                declared = slot.type_name
                if declared in TYPE_MAP and declared != "any" and actual_type != declared:
                    if not (declared == "float" and actual_type == "int"):
                        print_warning(
                            f"Suspicious assignment to '{name}': declared '{declared}', assigning '{actual_type}'",
                            line=slot.defined_line,
                        )

            # Too-many-types warning (multi-type vars)
            if globals().get("WARNINGS") and slot.allowed_types and len(slot.used_types) > 3:
                print_warning(
                    f"'{name}' has been assigned {len(slot.used_types)} different types "
                    f"({', '.join(sorted(slot.used_types))}); consider splitting into separate variables",
                    line=slot.defined_line,
                )

            # Intentar coerción automática entre int y float para asignaciones
            if "," not in normalized_type:
                if normalized_type == "int" and isinstance(value, float):
                    if value.is_integer():
                        value = int(value)
                    else:
                        raise TypeError(f"Cannot assign float with fractional part to {name}: {slot.type_name}")
                if normalized_type == "float" and isinstance(value, int):
                    value = float(value)
            if not self._type_matches(normalized_type, value):
                raise TypeError(
                    f"Cannot assign {type(value).__name__} a {name}: {slot.type_name}"
                )

            if slot.max_size is not None:
                self._validate_size(normalized_type, value, slot.max_size)

            if slot.element_type is not None:
                self._validate_element_type_spec(slot.element_type)
                self._validate_element_types(normalized_type, value, slot.element_type)

            # Optimización: No reasignar si el valor es idéntico
            if slot.previous_value != value:
                slot.value = value
                slot.previous_value = value
                slot.assign_count += 1

            return

        if self.parent is not None and self.parent.has(name):
            self.parent.assign(name, value, type_name)
            return

        raise NameError(f"Variable not declared: {name}")

    def get(self, name: str) -> Value:
        if name in self._slots:
            self._slots[name].accessed = True
            return self._slots[name].value
        if self.parent is not None:
            return self.parent.get(name)
        raise NameError(f"Variable not declared: {name}")

    def has(self, name: str) -> bool:
        if name in self._slots:
            return True
        if self.parent is not None:
            return self.parent.has(name)
        return False

    def has_local(self, name: str) -> bool:
        return name in self._slots

    def release(self, name: str) -> None:
        if name in self._slots:
            del self._slots[name]

    def release_block_variables(self, block_var_names: set[str]) -> None:
        """Release a set of local block variables on block exit."""
        for var_name in block_var_names:
            self.release(var_name)

    def _validate_type_name(self, type_name: str) -> str:
        # Preserve case for class-name annotations (class names are case-sensitive identifiers);
        # everything else is normalized to lowercase as before.
        raw = type_name.strip()
        normalized_type = raw.lower()
        # Allow empty/unspecified type (treat as 'any' until a value or explicit type is set)
        if normalized_type == "":
            return "any"
        # Support multi-type: "int,str,float"
        if "," in normalized_type:
            types_list = [t.strip() for t in normalized_type.split(",")]
            for t in types_list:
                if t not in TYPE_MAP:
                    raise TypeError(f"Unsupported type in multi-type: {t}")
            return normalized_type
        if normalized_type in TYPE_MAP:
            return normalized_type
        # Not a primitive: treat as a class-name or enum-name annotation if a matching
        # definition is visible from this scope. Both keep their original casing.
        if self._lookup_class_definition(raw) is not None:
            return raw
        if self._lookup_enum_definition(raw) is not None:
            return raw
        raise TypeError(f"Unsupported type: {type_name}")

    def _lookup_class_definition(self, name: str) -> "ClassDefinition | None":
        mgr: MemoryManager | None = self
        while mgr is not None:
            if name in mgr._slots:
                candidate = mgr._slots[name].value
                if isinstance(candidate, ClassDefinition):
                    return candidate
                return None
            mgr = mgr.parent
        return None

    def _lookup_enum_definition(self, name: str) -> "EnumDefinition | None":
        mgr: MemoryManager | None = self
        while mgr is not None:
            if name in mgr._slots:
                candidate = mgr._slots[name].value
                if isinstance(candidate, EnumDefinition):
                    return candidate
                return None
            mgr = mgr.parent
        return None

    def _enum_value_matches(self, enum_name: str, value: Value) -> bool:
        """Enums are always represented as plain ints internally (see EnumDefinition).
        A value matches an enum-typed annotation when it is one of that enum's own
        declared members — not just any int — so mixing values between unrelated
        enums (or plain ints) is still caught."""
        enum_def = self._lookup_enum_definition(enum_name)
        if enum_def is None:
            return False
        if isinstance(value, bool):  # bool is technically an int subclass in Python
            return False
        if not isinstance(value, int):
            return False
        return value in enum_def.values.values()

    def _validate_element_type_spec(self, element_type: str) -> None:
        """Ensure every non-primitive name in an array/dict element-type annotation
        actually refers to a declared class or enum. Primitives and 'any' are already
        guaranteed valid by parse_annotation; this catches typos/undeclared names
        even when the container is empty (and so never reaches per-item validation)."""
        if element_type == "any":
            return
        for spec in (t.strip() for t in element_type.split(",")):
            if spec == "any" or spec in TYPE_MAP:
                continue
            if self._lookup_class_definition(spec) is None and self._lookup_enum_definition(spec) is None:
                raise TypeError(f"Unknown type '{spec}' used in array/dict element-type annotation")

    def _element_matches_spec(self, spec: str, item: Value) -> bool:
        """Resolve a single array/dict element-type spec — primitive, class name, or
        declared enum name — and check whether `item` satisfies it."""
        if spec == "any":
            return True
        if spec in TYPE_MAP:
            return isinstance(item, TYPE_MAP[spec])
        if self._lookup_enum_definition(spec) is not None:
            return self._enum_value_matches(spec, item)
        return self._instance_matches_class(item, spec)

    def _instance_matches_class(self, value: Value, class_name: str) -> bool:
        """Check value['__class__'] against class_name, walking up __parent__ for inheritance."""
        if not isinstance(value, dict) or "__class__" not in value:
            return False
        seen: set[str] = set()
        current = value.get("__class__")
        while current and current not in seen:
            if current == class_name:
                return True
            seen.add(current)
            parent_def = self._lookup_class_definition(current)
            current = parent_def.parent_class if parent_def else None
        return False

    def _type_matches(self, type_name: str, value: Value) -> bool:
        if type_name == "any":
            return True
        if value is None:
            return True
        # Support multi-type checking
        if "," in type_name:
            types_list = [t.strip() for t in type_name.split(",")]
            for t in types_list:
                if t == "any":
                    return True
                if t in TYPE_MAP:
                    if isinstance(value, TYPE_MAP[t]):
                        return True
                elif self._lookup_enum_definition(t) is not None:
                    if self._enum_value_matches(t, value):
                        return True
                elif self._instance_matches_class(value, t):
                    return True
            return False
        if type_name in TYPE_MAP:
            return isinstance(value, TYPE_MAP[type_name])
        if self._lookup_enum_definition(type_name) is not None:
            return self._enum_value_matches(type_name, value)
        # Class-name annotation: value must be an instance of that class (or a subclass)
        return self._instance_matches_class(value, type_name)

    def _validate_size(self, type_name: str, value: Value, max_size: int) -> None:
        # Validate size based on the runtime value, not only on the declared type.
        if isinstance(value, str):
            if len(value) > max_size:
                raise ValueError(
                    f"String has {len(value)} characters but the declared limit is {max_size}. "
                    f"Use str[{len(value)}] or larger to fit this value."
                )
        elif isinstance(value, list):
            if len(value) > max_size:
                raise ValueError(
                    f"Array has {len(value)} elements but the declared limit is {max_size}. "
                    f"Use array[...][{len(value)}] or larger to fit this value."
                )
        elif isinstance(value, dict):
            if len(value) > max_size:
                raise ValueError(
                    f"Dict has {len(value)} entries but the declared limit is {max_size}. "
                    f"Use dict[...][{len(value)}] or larger to fit this value."
                )

    def _validate_element_types(self, type_name: str, value: Value, element_type: str) -> None:
        """Valida los tipos de elementos dentro de arrays y diccionarios."""
        if value is None:
            return
        # Validate element types based on the runtime value structure.
        if isinstance(value, list):
            if element_type == "any":
                return
            allowed_specs = [t.strip() for t in element_type.split(",")]
            for index, item in enumerate(value):
                if not any(self._element_matches_spec(spec, item) for spec in allowed_specs):
                    if len(allowed_specs) > 1:
                        raise TypeError(
                            f"Array element at index {index} must be one of {element_type}, got {type(item).__name__}"
                        )
                    raise TypeError(
                        f"Array element at index {index} must be {element_type}, got {type(item).__name__}"
                    )
        elif isinstance(value, dict):
            if element_type == "any":
                return
            # Dict element_type always describes ALLOWED VALUE TYPES (keys are always str).
            # "int" -> values must be int
            # "int,str,float" -> values must be one of int, str, float
            allowed_specs = [t.strip() for t in element_type.split(",")]
            for key, item in value.items():
                if item is None:
                    continue
                if not any(self._element_matches_spec(spec, item) for spec in allowed_specs):
                    raise TypeError(
                        f"Dict value for key {key!r} must be one of ({element_type}), got {type(item).__name__}"
                    )
        else:
            # If value is not a list/dict we cannot validate element types now; defer until an appropriate value is assigned.
            return

    def validate_single_element(self, container_name: str, value: Value) -> None:
        """Validate that a single value is allowed by the element_type annotation of a container slot.

        Called when a single element is assigned via index (array[i] = v) or key (dict["k"] = v),
        where the full container isn't re-validated by _validate_element_types.
        Does nothing if the slot has no element_type annotation or element_type is 'any'.
        """
        slot = None
        # Search up the scope chain
        mgr: MemoryManager | None = self
        while mgr is not None:
            if container_name in mgr._slots:
                slot = mgr._slots[container_name]
                break
            mgr = mgr.parent

        if slot is None or slot.element_type is None or slot.element_type == "any":
            return
        if value is None:
            return

        element_type = slot.element_type
        allowed_specs = [t.strip() for t in element_type.split(",")]
        if not any(self._element_matches_spec(spec, value) for spec in allowed_specs):
            raise TypeError(
                f"Element assigned to '{container_name}' must be one of ({element_type}), "
                f"got {type(value).__name__}"
            )

    def summary(self) -> str:
        entries = [f"{slot.name}:{slot.type_name}={slot.value!r}" for slot in self._slots.values()]
        return " | ".join(entries)


def _is_class_instance(value: Any) -> bool:
    """Duck-types a class-instance dict as built by ClassDefinition.instantiate(),
    without mistaking it for an ordinary dict literal written in the script."""
    return isinstance(value, dict) and "__class__" in value and "__fields__" in value


def _display_repr(value: Value, _seen: frozenset = frozenset()) -> str:
    """Builds the string print() actually shows. Class instances render as
    'ClassName(field=value, ...)' — only their public data fields, methods excluded —
    instead of leaking the internal bookkeeping dict (__body__, __memory__, __dir__,
    __defining_memory__, __reserved__, etc). Plain lists/dicts/values keep the same
    shape Python's own print() would have produced, including nested instances."""
    if _is_class_instance(value):
        class_name = value.get("__class__", "object")
        instance_id = id(value)
        if instance_id in _seen:
            return f"{class_name}(...)"  # guard against self-referencing structures
        _seen = _seen | {instance_id}
        fields = value.get("__fields__", {})
        parts = [
            f"{field_name}={_display_repr(field_value, _seen)}"
            for field_name, field_value in fields.items()
            if not isinstance(field_value, FunctionDefinition)  # skip methods
        ]
        return f"{class_name}({', '.join(parts)})"
    if isinstance(value, list):
        return "[" + ", ".join(_display_repr(item, _seen) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{key!r}: {_display_repr(item, _seen)}" for key, item in value.items()) + "}"
    if isinstance(value, str):
        return repr(value)
    return str(value)


def _builtin_print(*args: Any, **kwargs: Any) -> None:
    """Wraps Python's print() so class instances — bare, or nested inside an array/dict —
    show their data fields instead of the raw internal instance dict."""
    formatted = [_display_repr(arg) if isinstance(arg, (dict, list)) else arg for arg in args]
    print(*formatted, **kwargs)


memory = MemoryManager()
for name, function in BUILTIN_FUNCTIONS.items():
    memory.allocate(name, "any", function)
# Override the raw Python print registered above with the instance-aware version.
memory._slots["print"].value = _builtin_print

SHOW_MEMORY: bool = False
SHOW_RETURNS: bool = False
TRACE: bool = False
WARNINGS: bool = False
LOADED_MODULES: set[str] = set()
EXPRESSION_AST_CACHE: dict[str, ast.expr] = {}
_CURRENT_LINE: int | None = None  # Updated by process_source_lines for warning attribution

# Tracking for warnings
USAGE_TRACKING: dict[str, bool] = {}  # Track if variables/functions/classes are used
UNUSED_TYPES_WARNING: dict[str, set[str]] = {}  # Track unused types in multi-type variables
DEFINED_SYMBOLS: dict[str, tuple[str, int]] = {}  # symbol_name -> (type, line_number)

# Names loaded from the standard library (stdutils.gbn) or native builtins.
# Populated by load_standard_library() in Parser.py before user code runs.
# emit_post_execution_warnings() skips these to avoid spurious "never used" noise.
STDLIB_SYMBOLS: set[str] = set()

# Public API re-exported by Parser.py via `from Core.engine import *`.
# Only symbols that external callers legitimately need are listed here.
__all__ = [
    # Runtime configuration globals (mutated by Parser.py CLI flags)
    "SHOW_MEMORY",
    "SHOW_RETURNS",
    "TRACE",
    "WARNINGS",
    "EXTFILE",
    # Core objects
    "memory",
    "MemoryManager",
    "MemorySlot",
    # Signals / errors
    "MemoryError",
    "ReturnSignal",
    "BreakSignal",
    "ContinueSignal",
    "LoopSignal",
    "Interrupt",
    "ParserError",
    # Interpreter entry-points
    "process_source_lines",
    "execute_use",
    "compile_to_executable",
    "emit_post_execution_warnings",
    "_gc_release_unused",
    # Helpers used by Parser.py
    "get_resource_path",
    "read_lines",
    "run_program",
    # Standard-library symbol registry (populated by Parser.py)
    "STDLIB_SYMBOLS",
]


def _memory_descends_from(caller_memory: "MemoryManager", target_memory: "MemoryManager") -> bool:
    """True if caller_memory IS target_memory or a descendant of it via the parent chain."""
    mgr: MemoryManager | None = caller_memory
    while mgr is not None:
        if mgr is target_memory:
            return True
        mgr = mgr.parent
    return False


def _bind_self_scope(instance: dict, memory_manager: MemoryManager) -> "MemoryManager":
    """Create a child scope of `memory_manager` with `self` bound to `instance`.

    Used when calling a bound method from outside the class body,
    so the method body can reference `$self` purely through scope lookup — exactly like `init`
    does via `class_memory` — without `self` ever occupying a positional argument slot.
    This keeps declared parameters mapped 1:1 to the values the caller actually passes.
    """
    scope = MemoryManager(parent=memory_manager)
    scope.allocate("self", "any", instance)
    return scope


def _resolve_annotation_for_value(annotation_raw: str, memory_manager: MemoryManager) -> tuple[str, int | None, str | None]:
    """Resolve a parameter/return annotation string into (base_type, max_size, element_type).

    Tries parse_annotation first (primitives, array[T][N], str[N], dict[V][N], multi-type).
    If that fails and the annotation is a bare identifier matching a known ClassDefinition,
    treats it as a class-name annotation with no size/element constraints.
    """
    text = annotation_raw.strip()
    if text == "" or text.lower() == "any":
        return "any", None, None
    try:
        return parse_annotation(text)
    except TypeError:
        if is_valid_identifier(text) and (
            memory_manager._lookup_class_definition(text) is not None
            or memory_manager._lookup_enum_definition(text) is not None
        ):
            return text, None, None
        # Unknown annotation: surface the original error context to the caller via TypeError
        raise


def _validate_class_annotation(base_type: str, value: Value, memory_manager: MemoryManager, context: str) -> None:
    """If base_type is a class-name or enum-name annotation (not a primitive/multi-type),
    ensure value matches it. No-op for primitives, 'any', and multi-type strings,
    since those are validated elsewhere (MemoryManager.allocate / _type_matches)."""
    if base_type in TYPE_MAP or base_type in ("any", "NULL") or "," in base_type:
        return
    if value is None:
        return
    if memory_manager._lookup_enum_definition(base_type) is not None:
        if not memory_manager._enum_value_matches(base_type, value):
            raise TypeError(
                f"{context}: expected a value of enum '{base_type}', got {type(value).__name__}"
            )
        return
    if not memory_manager._instance_matches_class(value, base_type):
        actual = value.get("__class__") if isinstance(value, dict) and "__class__" in value else type(value).__name__
        raise TypeError(f"{context}: expected instance of class '{base_type}', got '{actual}'")


_NO_SELF = object()  # Sentinel distinguishing "no bound_self provided" from "bound_self is None"


@dataclass
class FunctionDefinition:
    name: str
    params: list[str]
    body: list[str]
    return_type: str = "any"
    return_max_size: int | None = None
    return_element_type: str | None = None
    return_type_raw: str = "any"
    source_path: Path | None = None
    defined_line: int | None = None
    defining_memory: "MemoryManager | None" = None  # Scope where this function was defined.
    # Used so a function captured into a namespace dict (via `@from x.gbn @as alias`) keeps
    # access to symbols from its OWN file (e.g. another `@from` it did internally) even when
    # called later from a completely different file's scope.

    def call(self, args: list[Value], parent_memory: MemoryManager, current_dir: Path, source_path: Path | None = None, bound_self: Value = _NO_SELF) -> Value:
        source_path = source_path or self.source_path

        # Resolve the effective parent scope. Normally this is just `parent_memory` (the
        # caller's scope), which is what lets implicit-self methods (no `self` param) reach
        # `self` via _bind_self_scope, and what lets module-level functions see globals defined
        # after them in the same file. But when this function is invoked through a namespace
        # dict captured by `@from x.gbn @as alias` — i.e. `parent_memory` is some UNRELATED
        # file's scope, not a descendant of where this function was defined — symbols this
        # function relies on from its OWN file (e.g. something it imported via its own
        # `@from`) would otherwise be invisible. In that specific case, fall back to the scope
        # this function was defined in, chained off the caller's scope so dynamic bindings
        # like `bound_self` (passed positionally, not via scope) are unaffected.
        first_param_name = self.params[0].split(":", 1)[0].strip() if self.params else None
        uses_implicit_self = first_param_name != "self" and bound_self is not _NO_SELF
        effective_parent = parent_memory
        if (
            self.defining_memory is not None
            and not uses_implicit_self
            and not _memory_descends_from(parent_memory, self.defining_memory)
        ):
            effective_parent = MemoryManager(parent=self.defining_memory)

        local_memory = MemoryManager(parent=effective_parent)

        # Support both class-method conventions:
        #   func init(self, x: int)   -> "self" is declared explicitly as the first parameter;
        #                                 the instance is injected positionally into it, like Python.
        #   func init(x: int)         -> no "self" parameter; the instance is reachable purely
        #                                 via scope (parent_memory already has "self" bound by
        #                                 _bind_self_scope / class_memory), so declared params
        #                                 map 1:1 to the values the caller passes.
        effective_args = args
        if bound_self is not _NO_SELF:
            if first_param_name == "self":
                effective_args = [bound_self] + list(args)
            # else: instance stays reachable only via parent_memory's "self" scope binding.

        for index, param in enumerate(self.params):
            # Extraer solo el nombre del parámetro (antes de ":")
            if ":" in param:
                param_name, _ptype_raw = param.split(":", 1)
                param_name = param_name.strip()
                param_annotation_raw = _ptype_raw.strip()
            else:
                param_name = param.strip()
                param_annotation_raw = "any"

            # Resolve the declared annotation into (base_type, max_size, element_type),
            # falling back to a class-name annotation if it's not a primitive/array/dict.
            p_base, p_max_size, p_element_type = _resolve_annotation_for_value(
                param_annotation_raw, local_memory
            )

            if index < len(effective_args):
                value = effective_args[index]
                # target_type: declared annotation when meaningful (primitive, multi-type, or
                # class name), otherwise infer from the runtime value (annotation was "any").
                if p_base == "any":
                    target_type = infer_type(value)
                else:
                    target_type = p_base
                local_memory.allocate(param_name, target_type, value, max_size=p_max_size, element_type=p_element_type)
            else:
                # No argument passed: preserve the DECLARED type (not "any") so that
                # `$param is NULL` and later assignments still respect the annotation.
                local_memory.allocate(param_name, p_base, None, max_size=p_max_size, element_type=p_element_type)

        had_return_signal = False
        ret_val: Value = None
        try:
            process_source_lines(self.body, local_memory, current_dir, trace=False, source_path=source_path,
                                  line_offset=self.defined_line or 0)
        except ReturnSignal as return_signal:
            had_return_signal = True
            ret_val = return_signal.value

        # Validate the return value (explicit `return X` or implicit None when the function
        # falls through without a return) against the declared return_type. Supports
        # array[T][N], str[N], dict[V][N], class names, multi-type, and "any"/"NULL".
        if self.return_type_raw not in ("any", "NULL"):
            if ret_val is None:
                if not had_return_signal:
                    raise TypeError(
                        f"Function '{self.name}': declared return type '{self.return_type_raw}', "
                        f"but the function ended without a 'return' statement"
                    )
                # Explicit `return` with no value (or `return NULL`) is allowed even when a
                # type is declared, mirroring how other None-valued assignments are treated.
            else:
                if self.return_type in TYPE_MAP or "," in self.return_type:
                    expected_types = [TYPE_MAP[t.strip()] for t in self.return_type.split(",") if t.strip() in TYPE_MAP]
                    if expected_types and not any(isinstance(ret_val, t) for t in expected_types):
                        raise TypeError(
                            f"Function '{self.name}': return type declared as '{self.return_type_raw}', "
                            f"but got {type(ret_val).__name__}"
                        )
                    if self.return_max_size is not None:
                        local_memory._validate_size(self.return_type, ret_val, self.return_max_size)
                    if self.return_element_type is not None:
                        local_memory._validate_element_type_spec(self.return_element_type)
                        local_memory._validate_element_types(self.return_type, ret_val, self.return_element_type)
                else:
                    # Class-name or enum-name (or otherwise non-primitive) return annotation:
                    # the class/enum must actually exist, and ret_val must satisfy it.
                    if (
                        local_memory._lookup_class_definition(self.return_type) is None
                        and local_memory._lookup_enum_definition(self.return_type) is None
                    ):
                        raise TypeError(
                            f"Function '{self.name}': return type '{self.return_type_raw}' is not a "
                            f"known type, class, or enum"
                        )
                    _validate_class_annotation(
                        self.return_type, ret_val, local_memory,
                        context=f"Function '{self.name}': return value"
                    )
        return ret_val

        # Unused local variable warnings
        if WARNINGS:
            for slot_name, slot in local_memory._slots.items():
                if slot_name.startswith("_"):
                    continue  # Convention: _ prefix = intentionally unused
                if slot_name == "self":
                    continue  # 'self' is always implicit in class methods; never warn about it
                if not slot.accessed and not isinstance(slot.value, (FunctionDefinition, ClassDefinition)):
                    print_warning(
                        f"Local variable '{slot_name}' in function '{self.name}' is never read",
                        line=slot.defined_line,
                    )

        # Liberar variables locales al final
        local_memory.release_block_variables(set(local_memory._slots.keys()))

        if self.return_type == "NULL":
            return None
        return None


@dataclass
class ClassDefinition:
    name: str
    body: list[str]
    source_path: Path | None = None
    parent_class: str | None = None
    defined_line: int | None = None
    is_reserved: bool = False  # True if declared with #reserved: every member is private,
                                # and the class itself cannot be instantiated/used from outside
                                # the scope where it was defined.
    defining_memory: "MemoryManager | None" = None  # Scope where the class was defined; used to
                                                       # tell apart internal vs external access for
                                                       # #reserved classes (e.g. via @from ... @as).

    def _is_internal_caller(self, caller_memory: "MemoryManager") -> bool:
        """True if caller_memory is the same scope the class was defined in, or a descendant
        of it (e.g. a function/class/block defined in the same file). False for callers reached
        only through an isolated namespace, such as `@from x.gbn @as alias` (alias is a plain
        dict, not a MemoryManager descendant), which is exactly the "outside" case we want to block.
        """
        if self.defining_memory is None:
            return True  # No recorded origin: don't block (defensive default).
        return _memory_descends_from(caller_memory, self.defining_memory)

    def instantiate(self, args: list[Value], parent_memory: MemoryManager, current_dir: Path, source_path: Path | None = None) -> dict[str, Any]:
        if self.is_reserved and not self._is_internal_caller(parent_memory):
            raise AttributeError(
                f"Class '{self.name}' is declared #reserved and cannot be instantiated "
                f"from outside the scope where it was defined"
            )
        source_path = source_path or self.source_path
        instance: dict[str, Any] = {
            "__class__": self.name,
            "__body__": self.body,
            "__fields__": {},
            "__parent__": self.parent_class,
            "__memory__": parent_memory,   # stored for bound-method calls
            "__dir__": current_dir,
            "__defining_memory__": self.defining_memory,  # scope the class was defined in
        }
        class_memory = MemoryManager(parent=parent_memory)
        class_memory.allocate("self", "any", instance)

        # Si hay clase padre, primero procesar su body
        if self.parent_class and parent_memory.has(self.parent_class):
            parent_def = parent_memory.get(self.parent_class)
            if isinstance(parent_def, ClassDefinition):
                process_source_lines(parent_def.body, class_memory, current_dir, trace=False, source_path=source_path,
                                     line_offset=parent_def.defined_line or 0)

        process_source_lines(self.body, class_memory, current_dir, trace=False, source_path=source_path,
                             line_offset=self.defined_line or 0)

        # Sort class members into three buckets:
        #  - __fields__: fully public, visible from anywhere.
        #  - __reserved__ (explicit): tagged #reserved on the member itself. Always private,
        #    even to code in the same file as the class — only `$self.x` from within the
        #    class's own methods can read these.
        #  - __class_reserved__ (inherited): the member itself has no tag, but the whole class
        #    is #reserved. Private to OTHER files/scopes, but behaves exactly like a public
        #    member for code in the same file/scope where the class was defined — i.e.
        #    "if the whole class is private, its content still works the same [internally]".
        instance["__reserved__"] = set()
        instance["__class_reserved__"] = set()
        instance["__reserved_fields__"] = {}
        for slot_name, slot in list(class_memory._slots.items()):
            if slot_name == "self":
                continue
            val = slot.value
            # Never expose ClassDefinition / EnumDefinition / built-in callables
            if isinstance(val, (ClassDefinition, EnumDefinition)):
                continue
            if callable(val) and not isinstance(val, FunctionDefinition):
                continue
            if slot.is_reserved:
                instance["__reserved__"].add(slot_name)
                instance["__reserved_fields__"][slot_name] = val
                continue
            if self.is_reserved:
                instance["__class_reserved__"].add(slot_name)
                instance["__reserved_fields__"][slot_name] = val
                continue
            if isinstance(val, FunctionDefinition):
                instance["__fields__"][slot_name] = val
            elif slot_name not in instance["__fields__"]:
                instance["__fields__"][slot_name] = val

        # Look for __init__ or init — local only to avoid picking up outer 'init'
        init_func = None
        for init_name in ("__init__", "init"):
            if class_memory.has_local(init_name):
                candidate = class_memory.get(init_name)
                if isinstance(candidate, FunctionDefinition):
                    init_func = candidate
                    break

        if init_func is not None:
            init_func.call(args, class_memory, current_dir, source_path=source_path, bound_self=instance)

        return instance


@dataclass
class EnumDefinition:
    name: str
    values: dict[str, Any]
    source_path: Path | None = None


def infer_type(value: Value) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "dict"
    return "any"


def _coerce_numeric_operands(a: Value, b: Value) -> tuple[Value, Value]:
    """Coerce int/float operands: if either is float, convert both to float.
    Returns the possibly converted pair (a, b)."""
    num_types = (int, float)
    if isinstance(a, num_types) and isinstance(b, num_types):
        if isinstance(a, float) or isinstance(b, float):
            return float(a), float(b)
    return a, b


class Pointer:
    def __init__(self, target: str, memory_manager: MemoryManager, current_dir: Path) -> None:
        self._target = target
        self._memory_manager = memory_manager
        self._current_dir = current_dir

    def get(self) -> Value:
        return evaluate_expression(self._target, self._memory_manager, self._current_dir)

    def set(self, value: Value) -> None:
        assign_target_expression(self._target, value, self._memory_manager, self._current_dir)

    @property
    def value(self) -> Value:
        return self.get()

    @value.setter
    def value(self, value: Value) -> None:
        self.set(value)

    def __repr__(self) -> str:
        return f"<Pointer target={self._target!r}>"


def assign_parsed_target(parsed: ast.expr, value: Value, memory_manager: MemoryManager, current_dir: Path) -> None:
    if isinstance(parsed, ast.Name):
        try:
            memory_manager.assign(parsed.id, value)
        except NameError:
            if value is None:
                return
            memory_manager.allocate(parsed.id, infer_type(value), value)
        return
    if isinstance(parsed, ast.Subscript):
        container = evaluate_ast(parsed.value, memory_manager, current_dir)
        key = evaluate_ast(parsed.slice, memory_manager, current_dir)
        # Resolve the container variable name (if simple) to validate element type annotation
        container_name: str | None = parsed.value.id if isinstance(parsed.value, ast.Name) else None
        if isinstance(container, dict):
            if "__fields__" in container and isinstance(key, str):
                if key in container.get("__reserved__", set()):
                    container.setdefault("__reserved_fields__", {})[key] = value
                else:
                    container.setdefault("__fields__", {})[key] = value
            else:
                if container_name:
                    memory_manager.validate_single_element(container_name, value)
                container[key] = value
            return
        if isinstance(container, list):
            if container_name:
                memory_manager.validate_single_element(container_name, value)
            container[key] = value
            return
        setattr(container, key, value)
        return
    if isinstance(parsed, ast.Attribute):
        container = evaluate_ast(parsed.value, memory_manager, current_dir)
        if isinstance(container, dict):
            if parsed.attr in ("__class__", "__body__", "__fields__"):
                container[parsed.attr] = value
            elif parsed.attr in container.get("__reserved__", set()):
                container.setdefault("__reserved_fields__", {})[parsed.attr] = value
            else:
                container.setdefault("__fields__", {})[parsed.attr] = value
            return
        setattr(container, parsed.attr, value)
        return
    raise SyntaxError(f"Cannot assign to target: {ast.dump(parsed)}")


def assign_target_expression(target: str, value: Value, memory_manager: MemoryManager, current_dir: Path) -> None:
    expression = target.strip()
    expression = replace_pointer_syntax(expression)
    expression = re.sub(r"\$(?=[A-Za-z_])", "", expression)
    parsed = parse_cached_expression(expression)
    assign_parsed_target(parsed, value, memory_manager, current_dir)


def collect_block(lines: list[str], start_index: int) -> tuple[list[str], int]:
    block: list[str] = []
    depth = 0
    i = start_index + 1
    while i < len(lines):
        stripped = lines[i].strip()
        if is_comment(stripped):
            i += 1
            continue
        # Strip a leading #reserved tag only for the purpose of recognizing block-opening
        # keywords (e.g. `#reserved func foo()` still opens a block like `func foo()` would).
        depth_probe = stripped
        while depth_probe.startswith("#reserved"):
            depth_probe = depth_probe[len("#reserved"):].strip()
        if depth_probe.startswith(("if ", "while ", "for ", "func ", "class ", "try ")) or depth_probe == "try":
            depth += 1
        elif stripped == "end":
            if depth == 0:
                return block, i + 1
            depth -= 1
        block.append(lines[i])
        i += 1
    raise SyntaxError("Block was not properly closed with 'end'")


def collect_if_group(lines: list[str], start_index: int) -> tuple[list[tuple[str | None, list[str]]], int]:
    groups: list[tuple[str | None, list[str]]] = []
    current_condition = lines[start_index].strip()[len("if"):].strip()
    current_block: list[str] = []
    depth = 0
    i = start_index + 1
    while i < len(lines):
        stripped = lines[i].strip()
        if is_comment(stripped):
            i += 1
            continue
        depth_probe = stripped
        while depth_probe.startswith("#reserved"):
            depth_probe = depth_probe[len("#reserved"):].strip()
        if depth_probe.startswith(("if ", "while ", "for ", "func ", "class ", "try ")) or depth_probe == "try":
            depth += 1
        elif stripped == "end":
            if depth == 0:
                groups.append((current_condition, current_block))
                return groups, i + 1
            depth -= 1
        elif depth == 0 and stripped.startswith("elseif "):
            groups.append((current_condition, current_block))
            current_condition = stripped[len("elseif "):].strip()
            current_block = []
            i += 1
            continue
        elif depth == 0 and stripped == "else":
            groups.append((current_condition, current_block))
            current_condition = None
            current_block = []
            i += 1
            continue
        current_block.append(lines[i])
        i += 1
    raise SyntaxError("Block was not properly closed with 'end'")


def collect_try_block(lines: list[str], start_index: int) -> tuple[list[str], list[str], int]:
    body: list[str] = []
    catch_body: list[str] = []
    current_block = body
    depth = 0
    i = start_index + 1
    while i < len(lines):
        stripped = lines[i].strip()
        if is_comment(stripped):
            i += 1
            continue
        depth_probe = stripped
        while depth_probe.startswith("#reserved"):
            depth_probe = depth_probe[len("#reserved"):].strip()
        if depth_probe.startswith(("if ", "while ", "for ", "func ", "class ", "try ")) or depth_probe == "try":
            depth += 1
        elif depth == 0 and stripped in ("catch", "except"):
            current_block = catch_body
            i += 1
            continue
        elif stripped == "end":
            if depth == 0:
                return body, catch_body, i + 1
            depth -= 1
        current_block.append(lines[i])
        i += 1
    raise SyntaxError("Try block was not properly closed with 'end'")


def evaluate_ast(node: ast.AST, memory_manager: MemoryManager, current_dir: Path) -> Value:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        name = node.id
        if name.lower() == "null":
            return None
        if name.lower() == "true":
            return True
        if name.lower() == "false":
            return False
        return memory_manager.get(name)
    if isinstance(node, ast.BinOp):
        left = evaluate_ast(node.left, memory_manager, current_dir)
        right = evaluate_ast(node.right, memory_manager, current_dir)
        left, right = _coerce_numeric_operands(left, right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Mod):
            return left % right
        if isinstance(node.op, ast.Pow):
            return left ** right
        raise SyntaxError(f"Operator not supported: {ast.dump(node.op)}")
    if isinstance(node, ast.BoolOp):
        values = [evaluate_ast(value, memory_manager, current_dir) for value in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)
        raise SyntaxError(f"Boolean operator not supported: {ast.dump(node.op)}")
    if isinstance(node, ast.UnaryOp):
        operand = evaluate_ast(node.operand, memory_manager, current_dir)
        if isinstance(node.op, ast.Not):
            return not operand
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return +operand
        raise SyntaxError(f"Unary operator not supported: {ast.dump(node.op)}")
    if isinstance(node, ast.Compare):
        left = evaluate_ast(node.left, memory_manager, current_dir)
        for operator, comparator in zip(node.ops, node.comparators):
            right = evaluate_ast(comparator, memory_manager, current_dir)
            # Only coerce numerics when both sides are numeric — never when comparing against
            # str/list/dict/None, as that would corrupt equality checks like x == "" or x == [].
            if isinstance(operator, (ast.Eq, ast.NotEq, ast.Is, ast.IsNot)):
                if isinstance(left, (int, float)) and isinstance(right, (int, float)):
                    left_cmp, right_cmp = _coerce_numeric_operands(left, right)
                else:
                    left_cmp, right_cmp = left, right
            else:
                left_cmp, right_cmp = _coerce_numeric_operands(left, right)
            if isinstance(operator, ast.Eq):
                if left_cmp != right_cmp:
                    return False
            elif isinstance(operator, ast.NotEq):
                if left_cmp == right_cmp:
                    return False
            elif isinstance(operator, ast.In):
                if left not in right:
                    return False
            elif isinstance(operator, ast.Is):
                # 'is' in user language means value-equality (same as ==)
                if left_cmp != right_cmp:
                    return False
            elif isinstance(operator, ast.IsNot):
                if left_cmp == right_cmp:
                    return False
            elif isinstance(operator, ast.Lt):
                if left_cmp >= right_cmp:
                    return False
            elif isinstance(operator, ast.LtE):
                if left_cmp > right_cmp:
                    return False
            elif isinstance(operator, ast.Gt):
                if left_cmp <= right_cmp:
                    return False
            elif isinstance(operator, ast.GtE):
                if left_cmp < right_cmp:
                    return False
            else:
                raise SyntaxError(f"Comparison operator not supported: {ast.dump(operator)}")
            left = right
        return True
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "__pointer__":
            if len(node.args) != 1 or not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, str):
                raise SyntaxError("Invalid pointer expression")
            return Pointer(node.args[0].value, memory_manager, current_dir)
        func = evaluate_ast(node.func, memory_manager, current_dir)
        args = [evaluate_ast(arg, memory_manager, current_dir) for arg in node.args]
        if isinstance(func, FunctionDefinition):
            return func.call(args, memory_manager, current_dir, source_path=func.source_path)
        if isinstance(func, ClassDefinition):
            return func.instantiate(args, memory_manager, current_dir, source_path=func.source_path)
        if callable(func):
            return func(*args)
        raise TypeError(f"Object {func!r} is not callable")
    if isinstance(node, ast.List):
        return [evaluate_ast(elt, memory_manager, current_dir) for elt in node.elts]
    if isinstance(node, ast.Dict):
        return {evaluate_ast(key, memory_manager, current_dir): evaluate_ast(value, memory_manager, current_dir)
                for key, value in zip(node.keys, node.values)}
    if isinstance(node, ast.Subscript):
        value = evaluate_ast(node.value, memory_manager, current_dir)
        key = evaluate_ast(node.slice, memory_manager, current_dir)
        if isinstance(value, dict) and isinstance(key, str) and "__fields__" in value:
            fields = value.get("__fields__", {})
            if key in fields:
                return fields[key]
        return value[key]
    if isinstance(node, ast.Attribute):
        value = evaluate_ast(node.value, memory_manager, current_dir)
        attr = node.attr
        if isinstance(value, EnumDefinition):
            if attr in value.values:
                return value.values[attr]
            raise AttributeError(f"Enum '{value.name}' has no member '{attr}'")
        if isinstance(value, list):
            if attr == "size":
                return lambda: len(value)
            if attr == "duplicate":
                return lambda: value.copy()
            # Resolve container name so we can validate element_type on mutation methods
            _list_var_name: str | None = node.value.id if isinstance(node.value, ast.Name) else None
            if attr in ("append", "push_back"):
                def _validated_append(item, _v=value, _n=_list_var_name, _mm=memory_manager):
                    if _n:
                        _mm.validate_single_element(_n, item)
                    _v.append(item)
                return _validated_append
            if attr == "insert":
                def _validated_insert(index, item, _v=value, _n=_list_var_name, _mm=memory_manager):
                    if _n:
                        _mm.validate_single_element(_n, item)
                    _v.insert(index, item)
                return _validated_insert
            if attr == "remove":
                return lambda index: value.pop(int(index) if isinstance(index, float) else index)
        if isinstance(value, dict):
            if attr == "size":
                return lambda: len(value)
            if attr == "duplicate":
                return lambda: value.copy()
            if attr == "remove":
                return lambda key: value.pop(key, None)
            # Resolve container name so we can validate element_type on mutation methods
            _dict_var_name: str | None = node.value.id if isinstance(node.value, ast.Name) else None
            if attr in ("set", "update"):
                def _validated_dict_set(key, item, _v=value, _n=_dict_var_name, _mm=memory_manager):
                    if _n:
                        _mm.validate_single_element(_n, item)
                    _v[key] = item
                return _validated_dict_set
        if isinstance(value, dict) and "__class__" in value:
            # Explicit #reserved members: only `self.attr` resolving to this exact instance
            # (i.e. called from within one of the class's own methods) can read them.
            is_self_access = (
                isinstance(node.value, ast.Name) and node.value.id == "self"
                and memory_manager.has("self") and memory_manager.get("self") is value
            )
            explicit_reserved = value.get("__reserved__", set())
            if attr in explicit_reserved and not is_self_access:
                raise AttributeError(
                    f"'{value.get('__class__')}' has no public member '{attr}' "
                    f"(it is declared #reserved)"
                )

            # Class-inherited reserved members (the whole class is #reserved, member itself
            # isn't tagged): behave like public members for any caller in the same file/scope
            # the class was defined in, but are invisible to truly external callers.
            class_reserved = value.get("__class_reserved__", set())
            if attr in class_reserved and not is_self_access:
                defining_memory = value.get("__defining_memory__")
                is_same_file_scope = defining_memory is None or _memory_descends_from(memory_manager, defining_memory)
                if not is_same_file_scope:
                    raise AttributeError(
                        f"'{value.get('__class__')}' has no public member '{attr}' "
                        f"(the class is declared #reserved)"
                    )
        if isinstance(value, dict):
            # Check __fields__ first (class instance fields and methods)
            if "__fields__" in value:
                fields = value["__fields__"]
                if attr in fields:
                    field_val = fields[attr]
                    # Bind self using __memory__/__dir__ stored at instantiation time
                    # so method calls never inherit the caller's local scope.
                    if isinstance(field_val, FunctionDefinition):
                        _func = field_val
                        _inst = value
                        _mm = value.get("__memory__", memory_manager)
                        _cd = value.get("__dir__", current_dir)
                        # `self` is bound via a dedicated child scope (not as a positional arg),
                        # so declared parameters map 1:1 to the values the caller passes.
                        return lambda *args, f=_func, s=_inst, m=_mm, d=_cd: f.call(list(args), _bind_self_scope(s, m), d, source_path=f.source_path, bound_self=s)
                    return field_val
            if "__class__" in value and (attr in value.get("__reserved__", set()) or attr in value.get("__class_reserved__", set())):
                # Reserved member (explicit or class-inherited), access already validated
                # above: read it from the dedicated __reserved_fields__ store (kept out of
                # __fields__ on purpose).
                reserved_val = value.get("__reserved_fields__", {}).get(attr)
                if isinstance(reserved_val, FunctionDefinition):
                    _func = reserved_val
                    _inst = value
                    _mm = value.get("__memory__", memory_manager)
                    _cd = value.get("__dir__", current_dir)
                    return lambda *args, f=_func, s=_inst, m=_mm, d=_cd: f.call(list(args), _bind_self_scope(s, m), d, source_path=f.source_path, bound_self=s)
                return reserved_val
            if attr in value:
                attr_val = value[attr]
                if isinstance(attr_val, FunctionDefinition) and "__class__" in value:
                    _func = attr_val
                    _inst = value
                    _mm = value.get("__memory__", memory_manager)
                    _cd = value.get("__dir__", current_dir)
                    return lambda *args, f=_func, s=_inst, m=_mm, d=_cd: f.call(list(args), _bind_self_scope(s, m), d, source_path=f.source_path, bound_self=s)
                return attr_val
            raise AttributeError(f"Object has no member '{attr}'")
        return getattr(value, node.attr)
    raise SyntaxError(f"Expression not supported: {ast.dump(node)}")


def parse_cached_expression(expression: str) -> ast.expr:
    expression = expression.strip()
    if expression in EXPRESSION_AST_CACHE:
        return EXPRESSION_AST_CACHE[expression]
    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise SyntaxError(f"Invalid expression: {expression}") from exc
    EXPRESSION_AST_CACHE[expression] = parsed.body
    return parsed.body


def evaluate_expression(expression: str, memory_manager: MemoryManager, current_dir: Path) -> Value:
    expression = expression.strip()
    if not expression:
        return None
    expression = replace_pointer_syntax(expression)
    expression = re.sub(r"\$(?=[A-Za-z_])", "", expression)
    parsed_body = parse_cached_expression(expression)
    return evaluate_ast(parsed_body, memory_manager, current_dir)


def evaluate_dollar_expression(token: str, memory_manager: MemoryManager, current_dir: Path) -> Value:
    token = token.strip()
    if not token:
        raise SyntaxError("'$' expression cannot be empty")
    if token.endswith(")") and "(" in token:
        function_name, args_text = token.split("(", 1)
        function_name = function_name.strip()
        args_text = args_text[:-1].strip()
        if memory_manager.has(function_name):
            function_value = memory_manager.get(function_name)
        else:
            raise NameError(f"Function or class not declared: {function_name}")
        if isinstance(function_value, FunctionDefinition):
            args = [evaluate_expression(arg, memory_manager, current_dir)
                    for arg in split_call_arguments(args_text)]
            return function_value.call(args, memory_manager, current_dir, source_path=function_value.source_path)
        if isinstance(function_value, ClassDefinition):
            args = [evaluate_expression(arg, memory_manager, current_dir)
                    for arg in split_call_arguments(args_text)]
            return function_value.instantiate(args, memory_manager, current_dir, source_path=function_value.source_path)
        if callable(function_value):
            args = [evaluate_expression(arg, memory_manager, current_dir)
                    for arg in split_call_arguments(args_text)]
            return function_value(*args)
        raise TypeError(f"Symbol '{function_name}' exists but is not callable")

    # Handle class instantiation without arguments: $ClassName
    if memory_manager.has(token):
        value = memory_manager.get(token)
        if isinstance(value, ClassDefinition):
            return value.instantiate([], memory_manager, current_dir, source_path=value.source_path)

    return memory_manager.get(token)


def assign_variable(source: str, memory_manager: MemoryManager, current_dir: Path) -> None:
    is_ready = False
    is_reserved = False
    source = source.strip()
    # Accept #reserved and #onready in either order, each optional
    while True:
        if source.startswith("#onready"):
            is_ready = True
            source = source[len("#onready"):].strip()
        elif source.startswith("#reserved"):
            is_reserved = True
            source = source[len("#reserved"):].strip()
        else:
            break

    name, annotation, value_text = parse_variable_declaration(source)
    # Soporte shorthand nombre[tamaño] en la declaración (ej: var lista[2] = ...)
    size_from_name: int | None = None
    m = re.match(r"^([A-Za-z_]\w*)\[(\d+)\]$", name)
    if m:
        name = m.group(1)
        try:
            size_from_name = int(m.group(2))
        except ValueError:
            raise SyntaxError(f"Invalid size in declaration: {m.group(2)}")

    if not annotation:
        raise SyntaxError(f"Invalid var header: missingtype annotation")

    value = evaluate_expression(value_text, memory_manager, current_dir)

    try:
        base_type, max_size, element_type = parse_annotation(annotation)
    except TypeError:
        # Not a primitive/array/dict annotation: fall back to class-name resolution
        # (e.g. `var p: Persona = ...`), validated lazily via MemoryManager.
        base_type, max_size, element_type = _resolve_annotation_for_value(annotation, memory_manager)
    if max_size is None and size_from_name is not None:
        max_size = size_from_name
    if not base_type:
        base_type = infer_type(value)
    # Si el valor es nulo y la variable no existe aún, no crearla en memoria
    if value is None and not memory_manager.has(name):
        return

    if name in memory_manager._slots and not is_ready:
        memory_manager.assign(name, value, base_type)
    else:
        memory_manager.allocate(name, base_type, value, max_size=max_size, element_type=element_type, is_ready=is_ready, defined_line=_CURRENT_LINE, is_reserved=is_reserved)


def assign_constant(source: str, memory_manager: MemoryManager, current_dir: Path) -> None:
    is_ready = False
    is_reserved = False
    source = source.strip()
    while True:
        if source.startswith("#onready"):
            is_ready = True
            source = source[len("#onready"):].strip()
        elif source.startswith("#reserved"):
            is_reserved = True
            source = source[len("#reserved"):].strip()
        else:
            break

    name, annotation, value_text = parse_constant_declaration(source)

    # Soporte shorthand nombre[tamaño] en la declaración (ej: const lista[2] = ...)
    size_from_name: int | None = None
    m = re.match(r"^([A-Za-z_]\w*)\[(\d+)\]$", name)
    if m:
        name = m.group(1)
        try:
            size_from_name = int(m.group(2))
        except ValueError:
            raise SyntaxError(f"Invalid size in declaration: {m.group(2)}")

    if not annotation:
        raise SyntaxError(f"Invalid const header: missing type annotation")

    value = evaluate_expression(value_text, memory_manager, current_dir)

    try:
        base_type, max_size, element_type = parse_annotation(annotation)
    except TypeError:
        base_type, max_size, element_type = _resolve_annotation_for_value(annotation, memory_manager)
    if max_size is None and size_from_name is not None:
        max_size = size_from_name
    if not base_type:
        base_type = infer_type(value)

    if value is None and not memory_manager.has(name):
        return

    memory_manager.allocate(name, base_type, value, immutable=True, max_size=max_size, element_type=element_type, is_ready=is_ready, defined_line=_CURRENT_LINE, is_reserved=is_reserved)


def assign_to_variable(target: str, expression: str, memory_manager: MemoryManager, current_dir: Path) -> None:
    value = evaluate_expression(expression, memory_manager, current_dir)
    if target.startswith("$$"):
        assign_target_expression(target[2:], value, memory_manager, current_dir)
        return
    normalized_target = target[1:] if target.startswith("$") else target
    try:
        parsed = parse_cached_expression(normalized_target)
    except SyntaxError:
        try:
            memory_manager.assign(normalized_target, value)
            return
        except NameError:
            if value is None:
                return
            type_name = infer_type(value)
            memory_manager.allocate(normalized_target, type_name, value)
            return

    if isinstance(parsed, ast.Name):
        try:
            memory_manager.assign(parsed.id, value)
        except NameError:
            if value is None:
                return
            memory_manager.allocate(parsed.id, infer_type(value), value)
        return
    if isinstance(parsed, ast.Subscript):
        container = evaluate_ast(parsed.value, memory_manager, current_dir)
        key = evaluate_ast(parsed.slice, memory_manager, current_dir)
        if isinstance(container, dict):
            if "__fields__" in container and isinstance(key, str):
                if key in container.get("__reserved__", set()):
                    container.setdefault("__reserved_fields__", {})[key] = value
                else:
                    container.setdefault("__fields__", {})[key] = value
            else:
                container[key] = value
            return
        if isinstance(container, list):
            container[key] = value
            return
        setattr(container, key, value)
        return
    if isinstance(parsed, ast.Attribute):
        container = evaluate_ast(parsed.value, memory_manager, current_dir)
        if isinstance(container, dict):
            if parsed.attr in ("__class__", "__body__", "__fields__"):
                container[parsed.attr] = value
            elif parsed.attr in container.get("__reserved__", set()):
                container.setdefault("__reserved_fields__", {})[parsed.attr] = value
            else:
                container.setdefault("__fields__", {})[parsed.attr] = value
            return
        setattr(container, parsed.attr, value)
        return

    memory_manager.assign(normalized_target, value)


def assign_value_to_variable(target: str, value: Value, memory_manager: MemoryManager, current_dir: Path) -> None:
    if target.startswith("$$"):
        assign_target_expression(target[2:], value, memory_manager, current_dir)
        return
    normalized_target = target[1:] if target.startswith("$") else target
    normalized_target = replace_pointer_syntax(normalized_target)
    normalized_target = re.sub(r"\$(?=[A-Za-z_])", "", normalized_target)
    try:
        parsed = ast.parse(normalized_target, mode="eval").body
    except SyntaxError:
        memory_manager.assign(normalized_target, value)
        return

    if isinstance(parsed, ast.Name):
        memory_manager.assign(parsed.id, value)
        return
    if isinstance(parsed, ast.Subscript):
        container = evaluate_ast(parsed.value, memory_manager, current_dir)
        key = evaluate_ast(parsed.slice, memory_manager, current_dir)
        if isinstance(container, dict):
            if "__fields__" in container and isinstance(key, str):
                if key in container.get("__reserved__", set()):
                    container.setdefault("__reserved_fields__", {})[key] = value
                else:
                    container.setdefault("__fields__", {})[key] = value
            else:
                container[key] = value
            return
        if isinstance(container, list):
            container[key] = value
            return
        setattr(container, key, value)
        return
    if isinstance(parsed, ast.Attribute):
        container = evaluate_ast(parsed.value, memory_manager, current_dir)
        if isinstance(container, dict):
            if parsed.attr in ("__class__", "__body__", "__fields__"):
                container[parsed.attr] = value
            elif parsed.attr in container.get("__reserved__", set()):
                container.setdefault("__reserved_fields__", {})[parsed.attr] = value
            else:
                container.setdefault("__fields__", {})[parsed.attr] = value
            return
        setattr(container, parsed.attr, value)
        return

    memory_manager.assign(normalized_target, value)


def define_function(header: str, body: list[str], memory_manager: MemoryManager, source_path: Path | None = None, is_reserved: bool = False) -> None:
    name, params, return_type = parse_function_header(header)

    # Validate return type annotation. "NULL" is kept as a sentinel (no return value expected).
    # Everything else (primitives, array[T][N], str[N], dict[V][N], class names, multi-type) is
    # validated via parse_annotation/class lookup, mirroring parameter annotations.
    return_base, return_max_size, return_element_type = (return_type, None, None)
    if return_type not in ("NULL", "any"):
        try:
            return_base, return_max_size, return_element_type = parse_annotation(return_type)
        except TypeError:
            # Not a primitive/array/dict annotation -> might be a class name; validated lazily at
            # return time (the class may be defined after this function in the source).
            return_base, return_max_size, return_element_type = return_type.strip(), None, None

    # Validate parameter type annotations using parse_annotation (handles array[T][N], str[N], etc.)
    # Unrecognized bare identifiers are treated as class-name annotations and validated lazily.
    for param in params:
        if ":" in param:
            _pname, _ptype_raw = param.split(":", 1)
            _ptype_clean = _ptype_raw.strip()
            if _ptype_clean and _ptype_clean.lower() not in TYPE_MAP and _ptype_clean.lower() != "any":
                try:
                    parse_annotation(_ptype_clean)
                except TypeError:
                    if not is_valid_identifier(_ptype_clean):
                        raise TypeError(
                            f"Function '{name}': invalid type annotation '{_ptype_clean}' for parameter '{_pname.strip()}'"
                        )

    func_def = FunctionDefinition(
        name=name, params=params, body=body, return_type=return_base,
        return_max_size=return_max_size, return_element_type=return_element_type,
        return_type_raw=return_type, source_path=source_path, defined_line=_CURRENT_LINE,
        defining_memory=memory_manager,
    )
    memory_manager.allocate(name, "any", func_def, defined_line=_CURRENT_LINE, is_reserved=is_reserved)


def define_class(header: str, body: list[str], memory_manager: MemoryManager, source_path: Path | None = None, is_reserved: bool = False) -> None:
    name, parent_class = parse_class_header(header)
    class_def = ClassDefinition(
        name=name, body=body, source_path=source_path, parent_class=parent_class,
        defined_line=_CURRENT_LINE, is_reserved=is_reserved, defining_memory=memory_manager,
    )
    memory_manager.allocate(name, "any", class_def, defined_line=_CURRENT_LINE, is_reserved=is_reserved)


def parse_enum_header(line: str) -> tuple[str, str]:
    # Format: enum Name[: type] = {...}
    # Type annotation is optional; enums are always stored as int internally.
    header = line.strip()[len("enum"):].strip()

    if ":" in header:
        name, rest = header.split(":", 1)
        name = name.strip()
        if "=" in rest:
            enum_type = rest.split("=", 1)[0].strip()
        else:
            enum_type = rest.strip()
    else:
        name = header.split("=", 1)[0].strip() if "=" in header else header.strip()
        enum_type = "int"  # Enums are always integers internally

    return name, enum_type


def define_enum_line(line: str, memory_manager: MemoryManager, source_path: Path | None = None) -> None:
    # Parse: enum Name[: type] = {VALUE1, VALUE2, ...}
    # Type annotation is optional; enums are always stored as int internally.
    header = line.strip()[len("enum"):].strip()

    if "=" not in header:
        raise SyntaxError("Enum definition requires '=' and values")

    name_part, values_part = header.split("=", 1)

    if ":" in name_part:
        name, enum_type = name_part.split(":", 1)
        name = name.strip()
        enum_type = enum_type.strip()
    else:
        name = name_part.strip()
        enum_type = "int"  # Enums are always integers internally
    values_part = values_part.strip()

    # Parse the values dictionary from {...}
    enum_values: dict[str, Any] = {}

    # Remove braces if present
    if values_part.startswith("{") and values_part.endswith("}"):
        values_part = values_part[1:-1]

    # Split by comma and add each value
    for value in values_part.split(","):
        value = value.strip()
        if value:
            enum_values[value] = len(enum_values)

    enum_def = EnumDefinition(name=name, values=enum_values, source_path=source_path)
    memory_manager.allocate(name, "any", enum_def)


def execute_block(lines: list[str], memory_manager: MemoryManager, current_dir: Path, trace: bool = True, source_path: Path | None = None, line_offset: int = 0) -> None:
    process_source_lines(lines, memory_manager, current_dir, trace=trace, source_path=source_path, line_offset=line_offset)


def evaluate_condition(expression: str, memory_manager: MemoryManager, current_dir: Path) -> bool:
    result = evaluate_expression(expression, memory_manager, current_dir)
    # Accept any truthy/falsy value, not just strict bool.
    # This allows: if $lista, if $texto, if $x == "", if $d == {}, etc.
    return bool(result)


def execute_if_group(groups: list[tuple[str | None, list[str]]], memory_manager: MemoryManager, current_dir: Path, trace: bool = True, source_path: Path | None = None, line_offset: int = 0) -> None:
    # Accumulate the offset for each branch as we skip past earlier ones.
    branch_offset = line_offset
    for condition, body in groups:
        if condition is None or evaluate_condition(condition, memory_manager, current_dir):
            block_memory = MemoryManager(parent=memory_manager)
            try:
                execute_block(body, block_memory, current_dir, trace=trace, source_path=source_path,
                              line_offset=branch_offset)
            finally:
                block_memory.release_block_variables(set(block_memory._slots.keys()))
            return
        branch_offset += len(body) + 1  # +1 for the elseif/else header line


def execute_while(condition: str, body: list[str], memory_manager: MemoryManager, current_dir: Path, trace: bool = True, source_path: Path | None = None, line_offset: int = 0) -> None:
    loop_memory = MemoryManager(parent=memory_manager)
    try:
        while evaluate_condition(condition, memory_manager, current_dir):
            try:
                execute_block(body, loop_memory, current_dir, trace=trace, source_path=source_path,
                              line_offset=line_offset)
            except ContinueSignal:
                continue
            except LoopSignal:
                continue   # same as continue — restart from condition check
            except BreakSignal:
                break
    finally:
        loop_memory.release_block_variables(set(loop_memory._slots.keys()))


def execute_for(target: str, source_expression: str, body: list[str], memory_manager: MemoryManager, current_dir: Path, trace: bool = True, source_path: Path | None = None, line_offset: int = 0, target_annotation: str = "") -> None:
    iterable = evaluate_expression(source_expression, memory_manager, current_dir)
    if isinstance(iterable, dict):
        iterator = list(iterable.keys())
    elif isinstance(iterable, (list, tuple, range, str)):
        iterator = iterable
    elif hasattr(iterable, "__iter__"):
        iterator = iterable
    else:
        raise TypeError("For-loop source is not iterable")

    loop_memory = MemoryManager(parent=memory_manager)

    # Resolve the loop variable's declared type once.
    # Empty annotation means untyped ("any"), matching the previous behavior.
    target_base = "any"
    if target_annotation.strip():
        target_base, _t_max, _t_elem = _resolve_annotation_for_value(target_annotation, loop_memory)

    try:
        for item in iterator:
            if target_base != "any":
                _validate_class_annotation(target_base, item, loop_memory, context=f"For-loop variable '{target}'")
                if (target_base in TYPE_MAP or "," in target_base) and item is not None:
                    allowed = [TYPE_MAP[t.strip()] for t in target_base.split(",") if t.strip() in TYPE_MAP]
                    if allowed and not any(isinstance(item, t) for t in allowed):
                        raise TypeError(
                            f"For-loop variable '{target}' declared as '{target_annotation.strip()}', "
                            f"but got {type(item).__name__}"
                        )
            if loop_memory.has_local(target):
                if loop_memory._slots[target].is_ready:
                    if loop_memory._slots[target].value != item:
                        loop_memory.assign(target, item)
                else:
                    loop_memory.assign(target, item)
            else:
                loop_memory.allocate(target, target_base, item)
            try:
                execute_block(body, loop_memory, current_dir, trace=trace, source_path=source_path,
                              line_offset=line_offset)
            except ContinueSignal:
                continue
            except LoopSignal:
                continue   # restart from next iteration (same as continue in for)
            except BreakSignal:
                break
    finally:
        loop_memory.release_block_variables(set(loop_memory._slots.keys()))


def is_valid_identifier(name: str) -> bool:
    # Verifica si un nombre es un identificador válido
    if not name:
        return False
    if not name[0].isalpha() and name[0] != '_':
        return False
    return all(c.isalnum() or c == '_' for c in name)


def prepare_source_lines(lines: list[str], memory_manager: MemoryManager, current_dir: Path) -> list[str]:
    """Remove comments and run #onready declarations before normal execution."""
    if lines and lines[0].startswith("#!"):
        lines = lines[1:]

    lines = remove_comments(lines)
    processed_lines: list[str] = []
    for raw_line in lines:
        line = strip_comments(raw_line).strip()
        if process_onready_declaration(line, raw_line, memory_manager, current_dir):
            continue
        processed_lines.append(raw_line)
    return processed_lines


def process_onready_declaration(line: str, raw_line: str, memory_manager: MemoryManager, current_dir: Path) -> bool:
    if not line.startswith("#onready") or len(line.split()) <= 1:
        return False

    token = line.split()[1]
    if token == "var":
        assign_variable(strip_comments(raw_line), memory_manager, current_dir)
        return True
    if token == "const":
        assign_constant(strip_comments(raw_line), memory_manager, current_dir)
        return True
    return False


def should_skip_line(line: str) -> bool:
    return is_blank(line) or is_comment(line)


def trace_statement(index: int, line: str, trace: bool) -> None:
    if trace:
        print(f"{index + 1:4}: {line}")


def execute_flow_statement(line: str, memory_manager: MemoryManager, current_dir: Path) -> bool:
    if line.upper() == "PASS":
        return True
    if line == "continue":
        raise ContinueSignal()
    if line == "break":
        raise BreakSignal()
    if line == "loop":
        raise LoopSignal()
    if line.startswith("return"):
        return_value = evaluate_expression(line[len("return"):].strip(), memory_manager, current_dir)
        if SHOW_RETURNS:
            if isinstance(return_value, (dict, list)):
                print(f"--> return: {_display_repr(return_value)}")
            else:
                print(f"--> return: {return_value!r}")
        raise ReturnSignal(return_value)
    return False


def execute_declaration_statement(line: str, memory_manager: MemoryManager, current_dir: Path) -> bool:
    # Peek past optional #reserved/#onready tags (in either order) to find the real keyword.
    probe = line.strip()
    while True:
        if probe.startswith("#reserved"):
            probe = probe[len("#reserved"):].strip()
        elif probe.startswith("#onready"):
            probe = probe[len("#onready"):].strip()
        else:
            break
    if probe.startswith("var "):
        assign_variable(line, memory_manager, current_dir)
        return True
    if probe.startswith("const "):
        assign_constant(line, memory_manager, current_dir)
        return True
    return False


def execute_import_statement(line: str, memory_manager: MemoryManager, current_dir: Path, importer_lines: list[str] | None = None) -> bool:
    if line.startswith("@use "):
        include_path = line[len("@use "):].strip()
        file_path = resolve_path(include_path, current_dir)
        execute_use(file_path, memory_manager, importer_lines=importer_lines)
        return True
    if line.startswith("@from "):
        include_path, alias = parse_from_alias_statement(line)
        file_path = resolve_path(include_path, current_dir)
        execute_from(file_path, alias, memory_manager, importer_lines=importer_lines)
        return True
    return False


def execute_definition_statement(
    line: str,
    lines: list[str],
    index: int,
    memory_manager: MemoryManager,
    source_path: Path | None = None,
) -> int | None:
    is_reserved = False
    probe = line.strip()
    while probe.startswith("#reserved"):
        is_reserved = True
        probe = probe[len("#reserved"):].strip()

    if probe.startswith("func "):
        block, next_index = collect_block(lines, index)
        define_function(probe, block, memory_manager, source_path=source_path, is_reserved=is_reserved)
        return next_index
    if probe.startswith("class "):
        block, next_index = collect_block(lines, index)
        define_class(probe, block, memory_manager, source_path=source_path, is_reserved=is_reserved)
        return next_index
    if probe.startswith("enum "):
        define_enum_line(probe, memory_manager, source_path=source_path)
        return index + 1
    return None


def execute_try_block(
    lines: list[str],
    index: int,
    memory_manager: MemoryManager,
    current_dir: Path,
    trace: bool = True,
    source_path: Path | None = None,
    line_offset: int = 0,
) -> int:
    body, catch_body, next_index = collect_try_block(lines, index)
    try:
        execute_block(body, memory_manager, current_dir, trace=trace, source_path=source_path,
                      line_offset=line_offset + index + 1)
    except Exception:
        if not catch_body:
            raise
        execute_block(catch_body, memory_manager, current_dir, trace=trace, source_path=source_path,
                      line_offset=line_offset + index + 1 + len(body) + 1)
    return next_index


def execute_control_block_statement(
    line: str,
    lines: list[str],
    index: int,
    memory_manager: MemoryManager,
    current_dir: Path,
    trace: bool = True,
    source_path: Path | None = None,
    line_offset: int = 0,
) -> int | None:
    if line.startswith("if "):
        groups, next_index = collect_if_group(lines, index)
        execute_if_group(groups, memory_manager, current_dir, trace=trace, source_path=source_path,
                         line_offset=line_offset + index + 1)
        return next_index
    if line == "try" or line.startswith("try "):
        return execute_try_block(lines, index, memory_manager, current_dir, trace=trace, source_path=source_path,
                                 line_offset=line_offset)
    if line.startswith("while "):
        block, next_index = collect_block(lines, index)
        condition = line[len("while"):].strip()
        execute_while(condition, block, memory_manager, current_dir, trace=trace, source_path=source_path,
                      line_offset=line_offset + index + 1)
        return next_index
    if line.startswith("for "):
        block, next_index = collect_block(lines, index)
        target, target_annotation, source_expression = parse_for_header(line)
        execute_for(target, source_expression, block, memory_manager, current_dir, trace=trace, source_path=source_path,
                    line_offset=line_offset + index + 1, target_annotation=target_annotation)
        return next_index
    return None


def execute_free_statement(line: str, memory_manager: MemoryManager) -> bool:
    normalized = line[1:] if line.startswith("$") else line
    if not (normalized.startswith("free ") or normalized.startswith("free(")):
        return False

    target = normalized[4:].strip().strip("()").strip()
    if target.startswith("$"):
        target = target[1:]
    if memory_manager.has(target):
        memory_manager.release(target)
        return True
    raise NameError(f"free: variable '{target}' not found")


def execute_expand_memory_statement(line: str, memory_manager: MemoryManager, current_dir: Path) -> bool:
    normalized = line[1:] if line.startswith("$") else line
    if not (normalized.startswith("expand_memory ") or normalized.startswith("expand_memory(")):
        return False

    raw = normalized.split("(", 1)[-1].rstrip(")").strip() if "(" in normalized else normalized[len("expand_memory"):].strip()
    try:
        extra = int(evaluate_expression(raw, memory_manager, current_dir))
    except Exception:
        raise ValueError(f"expand_memory: expected integer, got '{raw}'")
    if extra <= 0:
        raise ValueError(f"expand_memory: value must be positive, got {extra}")
    new_max = memory_manager.max_slots + extra
    import sys as _sys
    print(
        f"Warning: expand_memory({extra}) — memory slots expanded "
        f"from {memory_manager.max_slots} to {new_max}",
        file=_sys.stderr
    )
    memory_manager.max_slots = new_max
    return True


def _execute_breakpoint(memory_manager: MemoryManager, current_dir: Path, source_path: Path | None = None) -> None:
    """Interactive debugger breakpoint.
    Prints current memory state and opens a mini REPL where the user can evaluate
    GBN expressions against the live memory. Type 'continue' or press Ctrl-D to resume."""
    import sys as _sys
    header = "=" * 60
    print(header, file=_sys.stderr)
    print("  BREAKPOINT", file=_sys.stderr)
    if source_path:
        print(f"  File: {source_path}  Line: {_CURRENT_LINE}", file=_sys.stderr)
    print(header, file=_sys.stderr)

    # Print all visible slots (skip builtins and callables)
    from Core.native_io import BUILTIN_FUNCTIONS as _BF
    _builtin_names = set(_BF.keys())
    _mgr: MemoryManager | None = memory_manager
    _scope_label = "local"
    while _mgr is not None:
        slots_to_show = {
            k: v for k, v in _mgr._slots.items()
            if k not in _builtin_names and not callable(v.value)
        }
        if slots_to_show:
            print(f"  [{_scope_label} scope]", file=_sys.stderr)
            for k, slot in slots_to_show.items():
                print(f"    {slot.type_name} {k} = {slot.value!r}", file=_sys.stderr)
        _mgr = _mgr.parent
        _scope_label = "outer"
    print(header, file=_sys.stderr)
    print("  Type a GBN expression to evaluate, or 'continue' / Ctrl-D to resume.", file=_sys.stderr)
    print(header, file=_sys.stderr)

    while True:
        try:
            raw = input("breakpoint> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nResuming...", file=_sys.stderr)
            break
        if raw in ("continue", "cont", "c", "exit", "quit", ""):
            print("Resuming...", file=_sys.stderr)
            break
        try:
            result = evaluate_expression(raw, memory_manager, current_dir)
            print(f"  => {result!r}")
        except Exception as _bp_err:
            print(f"  Error: {_bp_err}", file=_sys.stderr)


def execute_runtime_statement(line: str, memory_manager: MemoryManager, current_dir: Path, source_path: Path | None = None) -> bool:
    if execute_free_statement(line, memory_manager):
        return True
    if execute_expand_memory_statement(line, memory_manager, current_dir):
        return True
    # Accept both `$breakpoint()` and `breakpoint()`
    _bp_normalized = line[1:] if line.startswith("$") else line
    if _bp_normalized in ("breakpoint()", "breakpoint"):
        _execute_breakpoint(memory_manager, current_dir, source_path=source_path)
        return True
    if line == "run":
        run_program(memory_manager, current_dir)
        return True
    if line.startswith("await "):
        condition = line[len("await"):].strip()
        while not evaluate_condition(condition, memory_manager, current_dir):
            time.sleep(0.01)
        return True
    return False


def calculate_compound_value(current_value: Value, right_value: Value, operator: str) -> Value:
    if operator == "+=":
        return current_value + right_value
    if operator == "-=":
        return current_value - right_value
    if operator == "*=":
        return current_value * right_value
    return current_value / right_value


def parse_assignable_dollar_target(target: str) -> ast.expr | None:
    normalized_target = replace_pointer_syntax(target[1:])
    normalized_target = re.sub(r"\$(?=[A-Za-z_])", "", normalized_target)
    try:
        parsed_target = parse_cached_expression(normalized_target)
    except SyntaxError:
        return None
    if isinstance(parsed_target, ast.Call):
        return None
    return parsed_target


def is_assignable_dollar_target(target: str) -> bool:
    if target.startswith("$$") and len(target) > 2:
        return True
    if target.startswith("$") and len(target) > 1:
        return parse_assignable_dollar_target(target) is not None
    return False


def execute_compound_assignment(line: str, memory_manager: MemoryManager, current_dir: Path) -> bool:
    if not line.startswith("$"):
        return False

    for operator in ["+=", "-=", "*=", "/="]:
        if operator not in line:
            continue
        target, expression = map(str.strip, line.split(operator, 1))
        if not is_assignable_dollar_target(target):
            continue
        current_expression = target[1:] if target.startswith("$$") else target
        current_value = evaluate_expression(current_expression, memory_manager, current_dir)
        right_value = evaluate_expression(expression, memory_manager, current_dir)
        new_value = calculate_compound_value(current_value, right_value, operator)
        assign_value_to_variable(target, new_value, memory_manager, current_dir)
        return True
    return False


def execute_dollar_assignment(line: str, memory_manager: MemoryManager, current_dir: Path) -> bool:
    if not (line.startswith("$") and "=" in line):
        return False

    first_part = line.split("=", 1)[0].strip()
    if not is_assignable_dollar_target(first_part):
        return False
    target, expression = map(str.strip, line.split("=", 1))
    assign_to_variable(target, expression, memory_manager, current_dir)
    return True


def execute_dollar_expression(line: str, memory_manager: MemoryManager, current_dir: Path) -> bool:
    if not line.startswith("$"):
        return False
    evaluate_expression(line, memory_manager, current_dir)
    return True


def execute_assignment_or_expression_statement(line: str, memory_manager: MemoryManager, current_dir: Path) -> bool:
    if execute_compound_assignment(line, memory_manager, current_dir):
        return True
    if execute_dollar_assignment(line, memory_manager, current_dir):
        return True
    if execute_dollar_expression(line, memory_manager, current_dir):
        return True
    if "=" in line:
        raise SyntaxError("Assignments must use '$' before the variable name")
    return False


def execute_source_line(
    line: str,
    lines: list[str],
    index: int,
    memory_manager: MemoryManager,
    current_dir: Path,
    trace: bool = True,
    source_path: Path | None = None,
    line_offset: int = 0,
) -> int:
    trace_statement(index, line, trace)

    if execute_flow_statement(line, memory_manager, current_dir):
        return index + 1
    if execute_declaration_statement(line, memory_manager, current_dir):
        return index + 1
    if execute_import_statement(line, memory_manager, current_dir, importer_lines=lines):
        return index + 1

    next_index = execute_definition_statement(line, lines, index, memory_manager, source_path=source_path)
    if next_index is not None:
        return next_index

    next_index = execute_control_block_statement(
        line, lines, index, memory_manager, current_dir, trace=trace, source_path=source_path,
        line_offset=line_offset,
    )
    if next_index is not None:
        return next_index

    if execute_runtime_statement(line, memory_manager, current_dir, source_path=source_path):
        return index + 1
    if execute_assignment_or_expression_statement(line, memory_manager, current_dir):
        return index + 1

    raise SyntaxError(f"Unsupported syntax or invalid statement: '{line}'")


def process_source_lines(lines: list[str], memory_manager: MemoryManager, current_dir: Path, trace: bool = True, source_path: Path | None = None, line_offset: int = 0) -> None:
    processed_lines = prepare_source_lines(lines, memory_manager, current_dir)

    index = 0
    while index < len(processed_lines):
        raw_line = processed_lines[index]
        line = strip_comments(raw_line).strip()
        global _CURRENT_LINE
        _CURRENT_LINE = line_offset + index + 1
        try:
            if should_skip_line(line):
                index += 1
                continue
            index = execute_source_line(line, processed_lines, index, memory_manager, current_dir, trace=trace, source_path=source_path, line_offset=line_offset,)
        except (ContinueSignal, BreakSignal, ReturnSignal, LoopSignal):
            raise
        except Exception as exc:
            raise _wrap_parser_error(exc, source_path, line_offset + index + 1, _guess_error_column(raw_line)) from exc


def resolve_path(path_text: str, current_dir: Path) -> Path:
    import sys as _sys

    candidate = Path(path_text)
    if not candidate.is_absolute():
        candidate = current_dir / candidate

    # If the candidate already has a suffix and exists, return it
    if candidate.suffix and candidate.exists():
        return candidate

    # Try supported extensions in order
    base = candidate.with_suffix("")
    for ext in SUPPORTED_IMPORT_EXTS:
        candidate_with_ext = base.with_suffix(ext)
        if candidate_with_ext.exists():
            return candidate_with_ext

    # When running as a PyInstaller frozen binary, also search _MEIPASS for
    # bundled libraries (all supported types, embedded flat in the bundle root).
    if getattr(_sys, "frozen", False) and hasattr(_sys, "_MEIPASS"):
        meipass = Path(_sys._MEIPASS)
        # Strip any leading dots or path separators to get a clean bare name
        bare_name = Path(path_text).name.lstrip(".")
        if not bare_name:
            bare_name = Path(path_text).stem.lstrip(".")
        # If the bare name already has a supported extension, try it directly first
        if Path(bare_name).suffix.lower() in SUPPORTED_IMPORT_EXTS:
            mei_candidate = meipass / bare_name
            if mei_candidate.exists():
                return mei_candidate
        # Otherwise try appending each supported extension
        stem_only = Path(bare_name).stem if Path(bare_name).suffix else bare_name
        for ext in SUPPORTED_IMPORT_EXTS:
            mei_candidate = meipass / (stem_only + ext)
            if mei_candidate.exists():
                return mei_candidate

    # Auto-search in libs/ if path is just a bare filename (no "/" separators).
    if "/" not in path_text:
        bare_name = Path(path_text).name.lstrip(".")
        if bare_name:
            base_name = bare_name.split(".")[0] if "." in bare_name else bare_name

            # Skip auto-search for stdutils (it's imported from Core/)
            if base_name.lower() != "stdutils":
                # libs/ doesn't have to sit exactly next to the installation: walk
                # upward looking for it (see find_libs_dir()), so it's found whether
                # it lives right beside the executable or one level higher (e.g. the
                # executable was placed inside its own "Core/"-style subfolder).
                libs_dir = find_libs_dir()
                if libs_dir is not None:
                    libs_path = libs_dir / base_name
                    # If the original name carried an explicit, supported extension, try
                    # that exact one first so it takes priority over guessing the full list.
                    explicit_suffix = Path(bare_name).suffix.lower()
                    if explicit_suffix in SUPPORTED_IMPORT_EXTS:
                        explicit_candidate = libs_path.with_suffix(explicit_suffix)
                        if explicit_candidate.exists():
                            return explicit_candidate
                    for ext in SUPPORTED_IMPORT_EXTS:
                        libs_candidate = libs_path.with_suffix(ext)
                        if libs_candidate.exists():
                            return libs_candidate

    # Fallback: append the default .gbn suffix
    return base.with_suffix(f".{EXTFILE}")


def _load_python_module(file_path: Path) -> types.ModuleType:
    """Load a Python file as a module and return it."""
    module_name = f"gbn_user_{file_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load Python module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    loader = spec.loader
    assert loader is not None
    loader.exec_module(module)
    return module


def _scan_text_for_names(text: str, candidate_names: set[str]) -> set[str]:
    """Return the subset of candidate_names that appear as whole-word identifiers in text."""
    import re as _re
    found: set[str] = set()
    for name in candidate_names:
        if _re.search(rf"\b{_re.escape(name)}\b", text):
            found.add(name)
    return found


def _find_dotted_used_names(text: str, alias: str, candidate_names: set[str]) -> set[str]:
    """Return the subset of candidate_names referenced as `<alias>.<name>` in text
    (the access pattern used for `@from ... @as alias` namespaces)."""
    import re as _re
    found: set[str] = set()
    alias_re = _re.escape(alias)
    for name in candidate_names:
        if _re.search(rf"\b{alias_re}\s*\.\s*{_re.escape(name)}\b", text):
            found.add(name)
    return found


def _module_symbol_text(value: Any) -> str:
    """Concatenate the raw source text associated with a module-level symbol's own
    definition (function body + parameter/return annotations, or class body + parent
    class name), so internal references to OTHER module symbols can be detected with
    a plain text scan."""
    parts: list[str] = []
    if isinstance(value, FunctionDefinition):
        parts.extend(value.body)
        parts.extend(value.params)
        parts.append(value.return_type_raw or "")
    elif isinstance(value, ClassDefinition):
        parts.extend(value.body)
        if value.parent_class:
            parts.append(value.parent_class)
    return "\n".join(parts)


def _resolve_used_module_symbols(temp_memory: "MemoryManager", seed_names: set[str]) -> set[str]:
    """Expand a seed set of module symbols (the ones directly referenced by the
    importer) into the full transitive closure: if a kept function/class internally
    references another module symbol, that symbol is kept too — even
    though the importer's own code never names it. Repeats until no new symbol turns up."""
    all_names = set(temp_memory._slots.keys())
    reachable: set[str] = set()
    pending = [n for n in seed_names if n in all_names]
    remaining = all_names - set(pending)
    while pending:
        name = pending.pop()
        if name in reachable:
            continue
        reachable.add(name)
        slot = temp_memory._slots.get(name)
        if slot is None:
            continue
        text = _module_symbol_text(slot.value)
        if not text:
            continue
        newly_found = _scan_text_for_names(text, remaining)
        if newly_found:
            remaining -= newly_found
            pending.extend(newly_found)
    return reachable


def execute_use(file_path: Path, memory_manager: MemoryManager, importer_lines: list[str] | None = None) -> None:
    resolved_path = file_path.resolve()
    if str(resolved_path) in LOADED_MODULES:
        return
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    LOADED_MODULES.add(str(resolved_path))
    ext = file_path.suffix.lower()
    if ext == f".{EXTFILE}":
        # Run the imported file in its own scope (child of memory_manager) instead of directly
        # in memory_manager. This mirrors @from...@as: functions/classes defined in the
        # imported file keep `defining_memory` pointing at this temp scope, so they can still
        # see their own internal symbols (including reserved ones) when called later. Only
        # NON-reserved symbols get copied up into the importer's memory_manager — #reserved
        # symbols stay only in temp_memory and are never visible to the importing file, exactly
        # like #reserved is invisible from outside the script that declared it.
        lines = read_lines(str(file_path))
        temp_memory = MemoryManager(parent=memory_manager)
        process_source_lines(lines, temp_memory, file_path.parent, trace=TRACE, source_path=file_path)

        candidate_names = {name for name, slot in temp_memory._slots.items() if not slot.is_reserved}
        if importer_lines is not None:
            importer_text = "".join(importer_lines)
            seed_names = _scan_text_for_names(importer_text, candidate_names)
            used_names = _resolve_used_module_symbols(temp_memory, seed_names) & candidate_names
        else:
            # No importer context available: keep everything,
            # exactly like before this filtering was added.
            used_names = candidate_names

        for name, slot in temp_memory._slots.items():
            if slot.is_reserved or name not in used_names:
                continue
            memory_manager.allocate(
                name, slot.type_name, slot.value, immutable=slot.immutable,
                max_size=slot.max_size, element_type=slot.element_type,
                defined_line=slot.defined_line,
            )
        return

    if ext == ".py":
        module = _load_python_module(file_path)
        candidate_names = {name for name in dir(module) if not name.startswith("_")}
        if importer_lines is not None:
            used_names = _scan_text_for_names("".join(importer_lines), candidate_names)
        else:
            used_names = candidate_names
        # expose public attributes into memory manager
        for name in used_names:
            try:
                val = getattr(module, name)
            except Exception:
                continue
            # allocate or assign
            try:
                memory_manager.assign(name, val)
            except NameError:
                memory_manager.allocate(name, infer_type(val), val)
        return

    # For languages we don't execute (C/C++/ASM/Bash), expose source as a dict under the filename
    if ext in (".h", ".c", ".cpp", ".asm", ".sh", ".bash"):
        source = file_path.read_text(encoding="utf-8")
        namespace = {"__source__": source, "__path__": str(file_path), "__lang__": ext.lstrip(".")}
        name = file_path.stem
        try:
            memory_manager.assign(name, namespace)
        except NameError:
            memory_manager.allocate(name, "dict", namespace)
        return


def parse_from_alias_statement(line: str) -> tuple[str, str | None]:
    parts = line.split()
    if len(parts) < 2:
        raise SyntaxError("Invalid @from statement")
    alias = None
    if "@as" in parts:
        as_index = parts.index("@as")
        include_path = " ".join(parts[1:as_index]).strip()
        if as_index + 1 >= len(parts):
            raise SyntaxError("Invalid @from ... @as alias statement")
        alias = parts[as_index + 1].strip()
    else:
        include_path = " ".join(parts[1:]).strip()
    if not include_path:
        raise SyntaxError("Invalid @from statement: missing path")
    return include_path, alias


def execute_from(file_path: Path, alias: str | None, memory_manager: MemoryManager, importer_lines: list[str] | None = None) -> None:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if alias is None:
        execute_use(file_path, memory_manager, importer_lines=importer_lines)
        return

    importer_text = "".join(importer_lines) if importer_lines is not None else None

    ext = file_path.suffix.lower()
    if ext == f".{EXTFILE}":
        temp_memory = MemoryManager(parent=memory_manager)
        process_source_lines(read_lines(str(file_path)), temp_memory, file_path.parent, trace=False, source_path=file_path)
        # Symbols declared #reserved in the imported file are never exposed through the
        # namespace's attribute surface — there is no way to reach the `alias` variable except
        # by being the file that wrote this @from, so "reserved" here simply means "never put
        # it where `$alias.x` can see it", with no scope comparison needed.
        candidate_names = {name for name, slot in temp_memory._slots.items() if not slot.is_reserved}
        if importer_text is not None:
            seed_names = _find_dotted_used_names(importer_text, alias, candidate_names)
            used_names = _resolve_used_module_symbols(temp_memory, seed_names) & candidate_names
        else:
            used_names = candidate_names
        namespace: dict[str, Any] = {}
        for name, slot in temp_memory._slots.items():
            if slot.is_reserved or name not in used_names:
                continue
            namespace[name] = slot.value
        memory_manager.allocate(alias, "any", namespace)
        return

    if ext == ".py":
        module = _load_python_module(file_path)
        candidate_names = {name for name in dir(module) if not name.startswith("_")}
        if importer_text is not None:
            used_names = _find_dotted_used_names(importer_text, alias, candidate_names)
        else:
            used_names = candidate_names
        namespace: dict[str, Any] = {}
        for name in used_names:
            try:
                namespace[name] = getattr(module, name)
            except Exception:
                continue
        memory_manager.allocate(alias, "any", namespace)
        return

    if ext in (".c", ".cpp", ".asm", ".sh", ".bash"):
        source = file_path.read_text(encoding="utf-8")
        namespace = {"__source__": source, "__path__": str(file_path), "__lang__": ext.lstrip(".")}
        memory_manager.allocate(alias, "any", namespace)
        return


def run_program(memory_manager: MemoryManager, current_dir: Path) -> None:
    if not memory_manager.has("init"):
        raise NameError("'init()' function not found for run")
    init_value = memory_manager.get("init")
    if not isinstance(init_value, FunctionDefinition):
        raise TypeError("'init()' is not a function")
    init_value.call([], memory_manager, current_dir, source_path=init_value.source_path)


def emit_post_execution_warnings(mem: MemoryManager, source_path: Path | None = None) -> None:
    """Emit all global-scope warnings after the program has finished executing.

    Checks:
    - Unused variables / constants / functions / classes
    - Empty functions (body contains only blanks/comments)
    - Empty classes  (always warned, even if accessed)
    - Multi-type variables with >3 distinct types actually used
    - Memory-leak candidates: large containers at global scope never read
    """
    if not WARNINGS:
        return

    BUILTIN_NAMES: set[str] = set(BUILTIN_FUNCTIONS.keys())
    SKIP_PREFIXES = ("_",)  # Convention: _ prefix = intentionally unused

    for slot_name, slot in mem._slots.items():
        if slot_name in BUILTIN_NAMES:
            continue
        if slot_name in STDLIB_SYMBOLS:
            continue
        if any(slot_name.startswith(p) for p in SKIP_PREFIXES):
            continue

        val = slot.value
        line = slot.defined_line
        fp = source_path

        # Class warnings: always emit, never skip due to empty body or lack of instantiation.
        # Both conditions (empty body AND never instantiated) can be reported independently.
        if isinstance(val, ClassDefinition):
            non_blank = [l for l in val.body if l.strip() and not l.strip().startswith("--")]
            if not non_blank:
                print_warning(f"Class '{slot_name}' has an empty body", fp, line)
            if not slot.accessed:
                print_warning(f"Class '{slot_name}' is defined but never instantiated", fp, line)
            continue  # Class warnings fully handled above; skip generic unused-symbol block

        # Unused symbol
        if not slot.accessed:
            if isinstance(val, FunctionDefinition):
                non_blank = [l for l in val.body if l.strip() and not l.strip().startswith("--")]
                if not non_blank:
                    print_warning(f"Function '{slot_name}' has an empty body", fp, line)
                else:
                    print_warning(f"Function '{slot_name}' is defined but never called", fp, line)
            elif isinstance(val, EnumDefinition):
                print_warning(f"Enum '{slot_name}' is defined but never used", fp, line)
            elif not (isinstance(val, dict) and "__lang__" in val):
                kind = "Constant" if slot.immutable else "Variable"
                print_warning(f"{kind} '{slot_name}' is declared but never read", fp, line)

                # ── Potential memory leak: large unreleased global container ─
                if isinstance(val, (list, dict)) and len(val) > 256:
                    print_warning(
                        f"  └─ '{slot_name}' is a large {type(val).__name__} ({len(val)} items) "
                        f"at global scope and never read — possible memory leak",
                        fp, line,
                    )

        # Multi-type variable with >3 distinct used types
        if slot.allowed_types and slot.used_types and len(slot.used_types) > 3:
            print_warning(
                f"'{slot_name}' has been assigned {len(slot.used_types)} different types "
                f"({', '.join(sorted(slot.used_types))}); consider splitting into separate variables",
                fp, line,
            )


def _gc_release_unused(mem: MemoryManager) -> None:
    """Garbage-collect global-scope symbols that were never read."""
    BUILTIN_NAMES: set[str] = set(BUILTIN_FUNCTIONS.keys())
    to_release = []
    for name, slot in mem._slots.items():
        if name in BUILTIN_NAMES:
            continue
        if name in STDLIB_SYMBOLS:
            continue
        if name.startswith("_"):
        # Keep all definitions and imported namespaces
            continue
        if isinstance(slot.value, (FunctionDefinition, EnumDefinition)):
            continue
        if isinstance(slot.value, ClassDefinition):
            continue  # Always keep classes (even empty ones — per spec)
        if isinstance(slot.value, dict) and "__lang__" in slot.value:
            continue
        if not slot.accessed:
            to_release.append(name)
    for name in to_release:
        mem.release(name)
