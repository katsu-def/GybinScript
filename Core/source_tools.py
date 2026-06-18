from __future__ import annotations

# ALL:
# Este archivo contiene herramientas puras de lectura de codigo fuente.
# Las funciones no ejecutan programas ni modifican memoria; solo convierten
# texto gbn en piezas que el motor puede interpretar.
# `parse_annotation` entiende tipos, limites y elementos de arrays/dicts.
# `replace_pointer_syntax` transforma `$$x` en una llamada interna segura.
# Los parsers de declaraciones y headers separan nombres, tipos y cuerpos.
# Los helpers de comentarios/bloques limpian texto preservando strings.
# `is_blank` e `is_comment` ayudan al despachador de lineas del motor.

from Core.runtime import TYPE_MAP


def parse_annotation(annotation: str) -> tuple[str, int | None, str | None]:
    """
    Analiza anotaciones de tipo con restricciones.
    Ejemplos: "str", "str[10]", "int, str", "array[int, str][3]".
    Retorna: (tipo_base, tamaño_maximo, tipo_elemento).
    """
    annotation_text = annotation.strip().lower()
    if annotation_text == "":
        return "", None, None

    if "," in annotation_text and not (annotation_text.startswith("array[") or annotation_text.startswith("dict[")):
        types_list = [t.strip() for t in annotation_text.split(",")]
        for t in types_list:
            if t not in TYPE_MAP:
                raise TypeError(f"Unsupported type in multi-type annotation: {t}")
        return ",".join(types_list), None, None

    if annotation_text.startswith("array[") or annotation_text.startswith("dict["):
        base_type = "array" if annotation_text.startswith("array[") else "dict"
        content = annotation_text[len(base_type) + 1:-1]
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
                for t in element_types:
                    if t not in TYPE_MAP:
                        raise TypeError(f"Unsupported element type in array: {t}")
                element_type = ",".join(element_types)
            else:
                if "," in element_type:
                    key_type, value_type = [part.strip() for part in element_type.split(",", 1)]
                    if key_type not in TYPE_MAP or value_type not in TYPE_MAP:
                        raise TypeError(f"Unsupported dict key/value types: {element_type}")
                elif element_type not in TYPE_MAP:
                    raise TypeError(f"Unsupported dict value type: {element_type}")

        return base_type, max_size, element_type

    if annotation_text.startswith("[") and annotation_text.endswith("]"):
        inner = annotation_text[1:-1].strip()
        if inner == "":
            return "", None, None
        if inner.isdigit():
            return "", int(inner), None
        if inner in TYPE_MAP or "," in inner:
            return "", None, inner
        raise TypeError(f"Invalid bracket annotation: {annotation}")

    if annotation_text.startswith("str[") and annotation_text.endswith("]"):
        try:
            max_size = int(annotation_text[4:-1])
            return "str", max_size, None
        except ValueError:
            raise TypeError(f"Invalid string size: {annotation_text[4:-1]}")

    if annotation_text in TYPE_MAP:
        return annotation_text, None, None

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
        return_type = return_part.strip().lower()
        if return_type == "null":
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
    """Elimina comentarios de una sola linea desde '--' fuera de cadenas."""
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


def parse_for_header(line: str) -> tuple[str, str]:
    header = line.strip()[len("for"):].strip()
    if " in " not in header:
        raise SyntaxError("Invalid for header: missing ' in '")
    target, source = map(str.strip, header.split(" in ", 1))
    if not target or not source:
        raise SyntaxError("Invalid for header: target and source cannot be empty")
    return target, source


def split_call_arguments(argument_text: str) -> list[str]:
    raw_args = [part.strip() for part in argument_text.split(",")]
    return [arg for arg in raw_args if arg != ""]


def is_comment(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("--") or stripped.startswith("!*")


def is_blank(line: str) -> bool:
    return not line.strip()
