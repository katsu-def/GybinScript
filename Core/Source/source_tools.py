from __future__ import annotations

# ALL:
# Este archivo contiene herramientas puras de lectura de codigo fuente.
# Las funciones no ejecutan programas ni modifican memoria; solo convierten
# texto gbn en piezas que el motor puede interpretar.
# `parse_annotation` entiende tipos, limites y elementos de arrays/dicts.
# Los tipos primitivos se normalizan a minusculas; cualquier identificador
# desconocido (posible nombre de clase o enum) conserva su mayus/minus
# original, ya que su existencia real se valida despues en el motor
# (este modulo no tiene acceso a memoria/clases/enums declarados).
# `replace_pointer_syntax` transforma `$$x` en una llamada interna segura.
# Los parsers de declaraciones y headers separan nombres, tipos y cuerpos.
# Los helpers de comentarios/bloques limpian texto preservando strings.
# `is_blank` e `is_comment` ayudan al despachador de lineas del motor.

from Core.runtime import TYPE_MAP


def _is_identifier(name: str) -> bool:
    """Mirrors engine.is_valid_identifier(): ASCII-only, starts with a letter or
    underscore, followed by letters/digits/underscores. Used to recognize potential
    class/enum names without needing to know whether they actually exist — this
    module has no access to memory/runtime, so existence is checked by the engine."""
    if not name:
        return False
    if not name[0].isalpha() and name[0] != "_":
        return False
    return all(c.isalnum() or c == "_" for c in name)


def _normalize_type_or_identifier(type_text: str, context: str) -> str:
    """Lowercase known primitive type names; otherwise keep the original casing so a
    class or enum name (case-sensitive identifiers) can later be resolved by the
    engine, which has access to the declared classes/enums."""
    lowered = type_text.lower()
    if lowered in TYPE_MAP:
        return lowered
    if _is_identifier(type_text):
        return type_text
    raise TypeError(f"Unsupported {context} type: {type_text}")


def parse_annotation(annotation: str) -> tuple[str, int | None, str | None]:
    annotation_text = annotation.strip()
    lowered = annotation_text.lower()
    if annotation_text == "":
        return "", None, None

    if "," in annotation_text and not (lowered.startswith("array[") or lowered.startswith("dict[")):
        types_list = [t.strip() for t in annotation_text.split(",")]
        normalized_list = [t.lower() for t in types_list]
        for t in normalized_list:
            if t not in TYPE_MAP:
                raise TypeError(f"Unsupported type in multi-type annotation: {t}")
        return ",".join(normalized_list), None, None

    if lowered.startswith("array[") or lowered.startswith("dict["):
        base_type = "array" if lowered.startswith("array[") else "dict"
        if not annotation_text.endswith("]"):
            raise TypeError(f"Invalid {base_type} annotation: {annotation}")
        content = annotation_text[len(base_type) + 1:-1]  # casing preserved
        max_size: int | None = None
        element_type: str | None = None

        if "][" in content:
            parts = content.split("][")
            if len(parts) == 2:
                element_type = parts[0].strip()
                try:
                    max_size = int(parts[1].strip())
                except ValueError:
                    raise TypeError(f"Invalid {base_type} size: {parts[1]}")
            else:
                raise TypeError(f"Invalid {base_type} annotation: {annotation}")
        else:
            element_type = content.strip() if content.strip() != "" else None

        if element_type is not None:
            if base_type == "array":
                element_types = [t.strip() for t in element_type.split(",")]
                element_type = ",".join(
                    _normalize_type_or_identifier(t, "array element") for t in element_types
                )
            else:
                if "," in element_type:
                    key_type, value_type = [part.strip() for part in element_type.split(",", 1)]
                    key_type = _normalize_type_or_identifier(key_type, "dict key")
                    value_type = _normalize_type_or_identifier(value_type, "dict value")
                    element_type = f"{key_type},{value_type}"
                else:
                    element_type = _normalize_type_or_identifier(element_type, "dict value")

        return base_type, max_size, element_type

    if annotation_text.startswith("[") and annotation_text.endswith("]"):
        inner = annotation_text[1:-1].strip()
        if inner == "":
            return "", None, None
        if inner.isdigit():
            return "", int(inner), None
        inner_lower = inner.lower()
        if inner_lower in TYPE_MAP:
            return "", None, inner_lower
        if "," in inner or _is_identifier(inner):
            return "", None, inner
        raise TypeError(f"Invalid bracket annotation: {annotation}")

    if lowered.startswith("str[") and lowered.endswith("]"):
        try:
            max_size = int(annotation_text[4:-1])
            return "str", max_size, None
        except ValueError:
            raise TypeError(f"Invalid string size: {annotation_text[4:-1]}")

    if lowered in TYPE_MAP:
        return lowered, None, None

    raise TypeError(f"Invalid type annotation: {annotation}")


def parse_annotation_legacy(annotation: str) -> str:
    """Version legada para compatibilidad."""
    annotation_text = annotation.strip().lower()
    if annotation_text == "":
        return ""
    base_type, _, _ = parse_annotation(annotation)
    if base_type not in TYPE_MAP:
        raise TypeError(f"Invalid type annotation: {annotation}")
    return base_type


def replace_pointer_syntax(expression: str) -> str:
    result: list[str] = []
    i = 0
    in_string: str | None = None
    while i < len(expression):
        char = expression[i]
        if in_string is not None:
            result.append(char)
            if char == in_string and (i == 0 or expression[i - 1] != "\\"):
                in_string = None
            i += 1
            continue
        if char in ('"', "'"):
            in_string = char
            result.append(char)
            i += 1
            continue
        if expression.startswith("$$", i):
            j = i + 2
            if j < len(expression) and (expression[j].isalpha() or expression[j] == "_"):
                start = j
                while j < len(expression) and (expression[j].isalnum() or expression[j] == "_"):
                    j += 1
                while True:
                    if j < len(expression) and expression[j] == ".":
                        j += 1
                        if j < len(expression) and (expression[j].isalpha() or expression[j] == "_"):
                            while j < len(expression) and (expression[j].isalnum() or expression[j] == "_"):
                                j += 1
                            continue
                        break
                    if j < len(expression) and expression[j] == "[":
                        bracket_depth = 1
                        j += 1
                        while j < len(expression) and bracket_depth > 0:
                            if expression[j] == "[":
                                bracket_depth += 1
                            elif expression[j] == "]":
                                bracket_depth -= 1
                            elif expression[j] in ('"', "'"):
                                quote = expression[j]
                                j += 1
                                while j < len(expression) and expression[j] != quote:
                                    if expression[j] == "\\":
                                        j += 2
                                    else:
                                        j += 1
                                continue
                            j += 1
                        continue
                    break
                target = expression[start:j]
                result.append(f"__pointer__({repr(target)})")
                i = j
                continue
        result.append(char)
        i += 1
    return "".join(result)


def parse_variable_declaration(source: str) -> tuple[str, str, str]:
    text = source.strip()[len("var"):].strip()
    if "=" not in text:
        raise SyntaxError("Variable declaration requires '='")

    left, right = map(str.strip, text.split("=", 1))
    if ":" in left:
        name, annotation = map(str.strip, left.split(":", 1))
    else:
        name, annotation = left, ""

    if not name:
        raise SyntaxError("Invalid variable name")

    return name, annotation, right


def parse_constant_declaration(source: str) -> tuple[str, str, str]:
    text = source.strip()[len("const"):].strip()
    if "=" not in text:
        raise SyntaxError("Constant declaration requires '='")

    left, right = map(str.strip, text.split("=", 1))
    if ":" in left:
        name, annotation = map(str.strip, left.split(":", 1))
    else:
        name, annotation = left, ""

    if not name:
        raise SyntaxError("Invalid constant name")

    return name, annotation, right


def parse_function_header(line: str) -> tuple[str, list[str], str]:
    header = line.strip()[len("func"):].strip()
    if "(" not in header or (")" not in header and "->" not in header):
        raise SyntaxError("Invalid function header: missing parentheses or return type")

    if "->" in header:
        func_part, return_part = header.rsplit("->", 1)
        return_type = return_part.strip()
        if return_type.lower() == "null":
            return_type = "NULL"
    else:
        func_part = header
        return_type = "any"

    func_part = func_part.strip()
    if not func_part.endswith(")"):
        raise SyntaxError("Invalid function header: missing closing parenthesis")

    name, args_text = func_part.split("(", 1)
    name = name.strip()
    args_text = args_text[:-1].strip()  # remove trailing )
    params = [arg.strip() for arg in args_text.split(",") if arg.strip()] if args_text else []
    if not name:
        raise SyntaxError("Invalid function header: missing function name")

    return name, params, return_type


def parse_class_header(line: str) -> tuple[str, str | None]:
    header = line.strip()[len("class"):].strip()
    if not header:
        raise SyntaxError("Invalid class header: missing class name")

    if " extends " in header:
        name, parent = header.split(" extends ", 1)
        return name.strip(), parent.strip()

    return header, None


def remove_comments(lines: list[str]) -> list[str]:
    cleaned_lines: list[str] = []
    in_block_comment = False

    for raw_line in lines:
        line = raw_line.rstrip("\n")
        result: list[str] = []
        i = 0
        in_string = None

        while i < len(line):
            char = line[i]
            if in_string is not None:
                result.append(char)
                if char == in_string and (i == 0 or line[i - 1] != "\\"):
                    in_string = None
                i += 1
                continue

            if char in ('"', "'"):
                in_string = char
                result.append(char)
                i += 1
                continue

            if line.startswith("!*", i):
                in_block_comment = not in_block_comment
                i += 2
                continue

            if not in_block_comment and line.startswith("--", i):
                break

            if not in_block_comment:
                result.append(char)

            i += 1

        if raw_line.endswith("\n"):
            cleaned_lines.append("".join(result) + "\n")
        else:
            cleaned_lines.append("".join(result))

    if in_block_comment:
        raise SyntaxError("Block comment not terminated")

    return cleaned_lines


def strip_comments(line: str) -> str:
    in_string = None
    result: list[str] = []
    i = 0
    while i < len(line):
        char = line[i]
        if in_string is not None:
            result.append(char)
            if char == in_string and (i == 0 or line[i - 1] != "\\"):
                in_string = None
            i += 1
            continue

        if char in ('"', "'"):
            in_string = char
            result.append(char)
            i += 1
            continue

        if line.startswith("--", i):
            break

        result.append(char)
        i += 1

    return "".join(result)


def parse_for_header(line: str) -> tuple[str, str, str]:
    header = line.strip()[len("for"):].strip()
    if " in " not in header:
        raise SyntaxError("Invalid for header: missing ' in '")
    target_part, source = map(str.strip, header.split(" in ", 1))
    if not target_part or not source:
        raise SyntaxError("Invalid for header: target and source cannot be empty")

    if ":" in target_part:
        target, target_annotation = map(str.strip, target_part.split(":", 1))
    else:
        target, target_annotation = target_part, ""

    if not target:
        raise SyntaxError("Invalid for header: target name cannot be empty")

    return target, target_annotation, source


def split_call_arguments(argument_text: str) -> list[str]:
    raw_args = [part.strip() for part in argument_text.split(",")]
    return [arg for arg in raw_args if arg != ""]


def is_comment(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("--") or stripped.startswith("!*")


def is_blank(line: str) -> bool:
    return not line.strip()
