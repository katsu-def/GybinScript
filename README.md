# GybinScript — User Manual 

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/katsu-def/GybinScript)

> [Read this manual in Spanish (README-ES.md)](./README-ES.md)

> **Version:** 1.5  
> **File extension:** `.gbn`  
> **Interpreter:** `Core/Gybin` \ `/usr/bin/Gybin`
> **Execution:** `Gybin (File path: My_script.gbn)`

> ! You can also declare the interpreter on the first line of your code and run it like any other program. (Linux only) E.g.:

```gbn
#!/usr/bin/Gybin -- Parser path

$print("Hello!") 
```

```bash
chmod +x My_script.gbn
./My_script.gbn
```

> Run setup-linux to configure the Gybin launcher in '/usr/bin'
> Run setup-termux to set up the language inside a Termux environment

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Running from the console](#2-running-from-the-console)
3. [Data types](#3-data-types)
4. [Variables and constants](#4-variables-and-constants)
5. [Comments](#5-comments)
6. [Operators](#6-operators)
7. [Functions](#7-functions)
8. [Classes](#8-classes)
9. [Inheritance](#9-inheritance)
10. [Enums](#10-enums)
11. [Arrays](#11-arrays)
12. [Dictionaries](#12-dictionaries)
13. [Control structures](#13-control-structures)
14. [Error handling](#14-error-handling)
15. [Pointers](#15-pointers)
16. [Events](#16-events)
17. [Modules and imports](#17-modules-and-imports)
18. [Memory management](#18-memory-management)
19. [Built-in functions](#19-built-in-functions)
20. [Standard library (stdutils)](#20-standard-library-stdutils)
21. [Compiling to an executable](#21-compiling-to-an-executable)
22. [Warnings and static analysis](#22-warnings-and-static-analysis)
23. [Rules and best practices](#23-rules-and-best-practices)

---

## 1. Introduction

GybinScript is a statically typed, interpreted scripting language with controlled memory management. It is designed to be expressive and predictable: every variable must be declared with a type, blocks are closed with `end`, and the `$` sign is the mandatory prefix for reading or modifying any variable or calling any function.

---

## 2. Running from the console

```bash
Gybin my_script.gbn [options]
```

### Available options

| Flag | Description |
|------|-------------|
| `--sm` | Shows the memory state when execution finishes |
| `--pr` | Automatically prints every value returned by `return` |
| `--t` | Shows the execution time |
| `--tr` | Shows each executed line instead of the normal output |
| `--c` | Compiles the script into an executable — see [§21](#21-compiling-to-an-executable). Does **not** run the script |
| `--fc` | Compiles the script unconditionally, even if it has errors — see [§21](#21-compiling-to-an-executable) |
| `--n NAME` | Custom name for the compiled executable (only with `--c`/`--fc`) |
| `--ad PATH[=DEST]` | Bundles an extra file/folder into the compiled executable; repeatable (only with `--c`/`--fc`) |
| `--i ICON_PATH` | Icon for the compiled executable (only with `--c`/`--fc`) |
| `--w` | Enables warning messages (static analysis) |
| `--nc` | Suppresses all standard output (errors are still shown) |

### Example

```bash
Gybin game.gbn --sm --w --t
```

---

## 3. Data types

GybinScript has six primitive types and two collection types:

| Type | Description | Example |
|------|-------------|---------|
| `int` | Integer | `20` |
| `float` | Decimal | `3.1416` |
| `str[N]` | String with maximum size N | `"Carlos"` |
| `bool` | Boolean | `true` / `false` |
| `any` | No type restriction | — |
| `NULL` | Null value / absence of value | `NULL` |
| `array[T,...]` | Typed list of elements | `[1, 2, 3]` |
| `dict[V,...]` | Typed dictionary of values | `{"a": 1}` |
| `ptr` | Pointer/reference to another variable, constant, function, or class (see [§15](#15-pointers)) | `$$hp` |

**Automatic coercions:**
- An `int` assigned to a `float` is automatically converted to `float`.
- A `float` with no decimal part assigned to an `int` is converted to `int`.
- A `float` with decimals assigned to an `int` produces a type error.

```gbn
var age: int = 20
var pi: float = 3.1416
var alive: bool = true
var name: str[16] = "Carlos"

$print($age)
$print($pi)
$print($alive)
$print($name)
```

---

## 4. Variables and constants

### Declaring variables

The basic syntax is `var name: type = value`. The `$` sign is used to read or modify the variable after it has been declared.

```gbn
var hp: int = 100
$hp = 50
```

### Size in the name (shorthand)

You can specify the maximum size directly in the variable name instead of in the type annotation:

```gbn
var buffer[128]: str = "hello"
```

### Multiple types

A variable can accept more than one type by separating them with commas. It is recommended to use this sparingly:

```gbn
var data: int,str = 10
$data = "text"
```

### Constants

Constants are declared with `const` and cannot be reassigned:

```gbn
const MAX_HP: int = 200
```

Trying to modify a constant produces a type error (`Immutable constant`).

### `#onready`

The `#onready` modifier declares a variable before the program starts running, useful for early initialization of dependencies:

```gbn
#onready var config: str[64] = "default"
```

When used, reassignments of the same value are also prevented.

### `#reserved`

`#reserved` is used to declare elements of a script as private, meaning they cannot be used outside the script where they were declared:

```gbn
#reserved var critical: bool = false
```

### `NULL` as an empty value

`NULL` represents the absence of a value. Objects and complex variables are declared with `NULL` when they don't yet have definitive content:

```gbn
var name: str[32] = NULL
var hp: int = NULL
```

> ! The interpreter ignores objects with a `NULL` value until one is assigned to them. For arrays and dicts, it's better to initialize with `[]` or `{}` instead of `NULL` if you plan to add elements right away.

---

## 5. Comments

### Line comment

Starts with `--` and extends to the end of the line:

```gbn
var x: int = 5 -- this is a comment
```

### Block comment

Delimited by `!*` at the start and `!*` at the end. It can span multiple lines:

```gbn
!* This is a comment
   spanning multiple lines !*
```

> Block comments are not nested: the second `!*` closes the block opened by the first one.

---

## 6. Operators

### Arithmetic

| Operator | Operation |
|----------|-----------|
| `+` | Addition |
| `-` | Subtraction |
| `*` | Multiplication |
| `/` | Division |
| `%` | Modulo |
| `**` | Power |

### Comparison

| Operator | Meaning |
|----------|---------|
| `==` | Equal |
| `!=` | Not equal |
| `<` | Less than |
| `<=` | Less than or equal |
| `>` | Greater than |
| `>=` | Greater than or equal |
| `is` | Equal by value (equivalent to `==`) |

### Logical

| Operator | Meaning |
|----------|---------|
| `and` | Logical AND |
| `or` | Logical OR |
| `not` | Negation |

### Compound assignment

```gbn
$x += 5
$x -= 2
$x *= 3
$x /= 4
```

---

## 7. Functions

### Declaration

```gbn
func name(param1: type, param2: type) -> return_type
    -- body
end
```

The return type is mandatory. Use `NULL` if the function doesn't return anything:

```gbn
func greet(name: str[32]) -> NULL
    $print("Hello " + $name)
end
```

### Function with a return value

```gbn
func add(a: int, b: int) -> int
    return $a + $b
end

var result: int = $add(10, 20)
$print($result)
```

### Calling functions

All calls must be preceded by `$`:

```gbn
$greet("Carlos")
$print($multiply($result, 2))
```

### Main function (`init`) and `run`

The `run` keyword executes the `init()` function defined in the global scope. This is the standard way to structure a program's entry point:

```gbn
func init() -> NULL
    $print("Program start")
end

run
```

> The `init()` function inside a class is that class's constructor, and it doesn't clash with the global `init()` because they are used in different contexts.

---

## 8. Classes

### Declaration

```gbn
class ClassName
    var field: type = NULL

    func init(self, param: type) -> NULL
        $self.field = $param
    end

end
```

`self` refers to the current instance and is passed automatically as the first argument when a method is called. You don't need to pass it when instantiating:

```gbn
var p: any = $Player("John")
$print($p.name)
$print($p.hp)
```

### Methods

Methods are defined inside the class just like functions, receiving `self` as the first parameter:

```gbn
class Player
    var hp: int = NULL

    func init(self) -> NULL
        $self.hp = 100
    end

    func damage(self, amount: int) -> NULL
        $self.hp -= $amount
    end

end

var p: Player = $Player()
$p.damage(30)
$print($p.hp)  -- 70
```

### Accessing fields

Accessed with a dot (`.`) without `$`:

```gbn
$print($p.name)
$p.hp = 50
```

---

## 9. Inheritance

A class can extend another with `extends`:

```gbn
class Entity
    var hp: int = NULL

    func init(self) -> NULL
        $self.hp = 100
    end

end

class Enemy extends Entity
    var damage: int = NULL

    func __init__(self) -> NULL
        $self.hp = 50
        $self.damage = 10
    end

end

var e: Enemy = $Enemy()
$print($e.hp)     -- 50
$print($e.damage) -- 10
```

> ! If the parent class already has an `init()` method, the child class must use `__init__()` instead to avoid a name conflict. The child class inherits all fields and methods from the parent class.

---

## 10. Enums

Enums group named constants under a common type:

```gbn
enum Direction = {UP, DOWN, LEFT, RIGHT}

var dir: int = Direction.UP
$print($dir)  -- 0
```

Values are automatically assigned starting from `0`. They are accessed with `EnumName.MEMBER`.

### Enums in classes

```gbn
enum ItemType = {WEAPON, ARMOR, CONSUMABLE}

class Item
    var name: str[32] = NULL
    var type: any = NULL

    func init(self, name: str[32], type: ItemType) -> NULL
        $self.name = $name
        $self.type = $type
    end

end

var sword: Item = $Item("Sword", $ItemType.WEAPON)
```

---

## 11. Arrays

### Declaration

```gbn
var numbers: array[int] = []
```

Use `[]` to initialize an empty array. Using `NULL` without immediately assigning elements will cause an error when trying to add to it.

### Array methods

| Method | Description |
|--------|-------------|
| `.append(value)` | Adds an element to the end |
| `.remove(index)` | Removes the element at the given position |
| `.size()` | Returns the number of elements |
| `.duplicate()` | Returns a copy of the array |
| `.push_back(value)` | Alias for `append` |

```gbn
$numbers.append(10)
$numbers.append(20)
$numbers.append(30)

$print($numbers)       -- [10, 20, 30]

$numbers[1] = 50
$print($numbers)       -- [10, 50, 30]
```

### Arrays with a maximum size

```gbn
var list: array[int][10] = []
```

This limits the array to a maximum of 10 elements.

### Arrays of objects

```gbn
var enemies: array[any] = []
$enemies.append($Enemy(10))
$print($enemies[2].hp)
```

---

## 12. Dictionaries

### Declaration

```gbn
var inventory: dict[int] = {}
```

### Basic usage

```gbn
$inventory["Potion"] = 5
$inventory["Sword"] = 1
$print($inventory)  -- {"Potion": 5, "Sword": 1}
```

### Dictionaries of objects

```gbn
var inventory: dict[any] = {}
$inventory["weapon"] = Item("Sword")
$print($inventory["weapon"].name)
```

### Dictionary methods

| Method | Description |
|--------|-------------|
| `.size()` | Returns the number of entries |
| `.remove(key)` | Removes the entry with that key |
| `.duplicate()` | Returns a copy of the dictionary |

---

## 13. Control structures

### `if / elseif / else` conditional

```gbn
if $x > 10
    $print("greater")
elseif $x == 10
    $print("equal")
else
    $print("less")
end
```

### `while` loop

```gbn
var i: int = 0
while $i < 10
    $print($i)
    $i += 1
end
```

### `for in` loop

Iterates over arrays, ranges, or dictionaries:

```gbn
for item in $enemies
    $print($item.hp)
end

for n in $range(5)
    $print($n)
end
```

### `match` conditional (no fallthrough)

Compares one subject against several possible values. Each case opens with `case value1, value2` (multiple comma-separated labels allowed) and — like `if`/`elseif`/`else` — Only the first matching case (or `else`, if present) runs; there is no fallthrough between cases.

```gbn
match $day
    case 1
        $print("Monday")
    case 2, 3
        $print("Tuesday or Wednesday")
    else
        $print("Another day")
end
```

Case labels can be any evaluable expression: literals, variables, enum members (`Color.RED`), even array/dict literals (`[1, 2, 3]`, `{"a": 1}`). If nothing matches and there is no `else`, nothing happens — no error is raised.

### Loop control keywords

| Keyword | Behavior |
|---------|----------|
| `break` | Exits the current loop |
| `continue` | Jumps to the next iteration |
| `loop` | Restarts the current iteration from the beginning |
| `pass` | Does nothing (placeholder for an empty block) |

### `await`

Pauses execution until a condition is true (polling every 10ms):

```gbn
await $ready == true
```

---

## 14. Error handling

```gbn
try
    -- code that might fail
catch
    -- code that runs if there is an error
end
```

`except` is also accepted as an alias for `catch`:

```gbn
try
    var x: int = $int("not_a_number")
except
    $print("A conversion error occurred")
end
```

---

## 15. Pointers

The `$$` operator creates a pointer to an existing variable, constant, function, or class (e.g. `$$hp`, `$$Damage`, `$$self.hp`, `$$arr[0]`). Type it with `ptr` — the only annotation that can hold a pointer value:

```gbn
var hp: int = 100
var ref: ptr = $$hp
```

> ! Reading a pointer variable directly (`$print(ref)`) prints the pointer itself, not the value it refers to — use `.value` or `.get()` to read through it.

### Pointer methods and properties

A pointer never carries a copy of what it points to — it resolves the target again every time one of these is used:

| Member | Description |
|--------|-------------|
| `.value` | Gets the current value of the referenced variable/constant. Can also be assigned (`$ref.value = 75`) to write through the pointer |
| `.get()` | Same as `.value`, as a method call |
| `.set(value)` | Same as assigning `.value`, as a method call |
| `.call(args...)` | Invokes the referenced function/class, forwarding the given arguments |
| `.name` | The name of the referenced memory space |
| `.is_callable` | `true` if the pointer refers to a function or class, `false` for a variable/constant |
| `.is_mutable` | `true` only for a non-`#reserved`, non-constant variable |
| `.size` | Approximate size in bytes of the referenced value |
| `.ref` | The real memory address (identity) of the referenced value |

```gbn
var hp: int = 100
var ref: ptr = $$hp

$print(ref.value)   -- 100
$ref.value = 75
$print(hp)           -- 75

func greet(name: str) -> NULL
    $print("Hello " + name)
end

var fp: ptr = $$greet
$fp.call("Carlos")   -- Hello Carlos
```

### Rules

- Only variables can be changed through a pointer. Constants are always immutable, and functions/classes can't be assigned a value — `.set()`/`.value = ...` raises an error for either.
- A variable declared with `#reserved` can never be mutated through a pointer, even by code that has a reference to it.
- Writing through a pointer (`.set()`/`.value = ...`) accepts any value type; a mismatch against the target's declared type produces a warning (with `--w`) instead of a hard type error.
- Referencing a function or class by its bare name (no `$$`) is a script error — `$$name` is the only way to obtain a handle to one without invoking it.

Pointers allow indirect access and can point to complex paths (`$$object.field`, `$$array[0]`). They are useful for aliases, dynamic references, and passing function references around (e.g. connecting handlers to an [event](#16-events)).

---

## 16. Events

An `event` declares a lightweight signal: a name plus a parameter list:

```gbn
event player_is_dead(entity: str)
```

Parameter type annotations are documentation only — an event has no body to enforce them against.

### `.connect(handler)` and `.emit(...)`

Every event exposes two methods, both called with the `$` prefix like any other call:

| Method | Description |
|--------|-------------|
| `.connect(handler)` | Registers a function to run whenever the event fires. `handler` must be a function reference created with `$$function_name` — passing a bare function name raises an error |
| `.emit(args...)` | Calls every connected handler, in the order they were connected, forwarding the given arguments. The number of arguments must match the number of parameters the event declares |

```gbn
event player_is_dead(entity: str)

func on_player_dead(entity: str) -> NULL
    $print(entity + " died")
end

$player_is_dead.connect($$on_player_dead)

if $life <= 0
    $player_is_dead.emit("Zombie")
end
```

More than one handler can be connected to the same event; all of them run, in connection order, on `.emit(...)`.

---

## 17. Modules and imports

### `@use` — importing a module

Loads a `.gbn` file (or another supported type) and exposes all of its symbols in the current scope:

```gbn
@use "utils.gbn"
@use "helpers"        -- detects the extension automatically
```

The import is idempotent: if a module has already been loaded, it won't be run again.

### `@from` / `@as` — importing with an alias

Loads a module and exposes it as a named namespace:

```gbn
@from "utils.gbn" @as utils
$print($utils.my_function())
```

### Supported formats

| Extension | Behavior |
|-----------|----------|
| `.gbn` | Executed and merged into the current scope |
| `.py` | Loaded as a Python module; its public attributes are exposed |
| `.c`, `.cpp`, `.asm`, `.sh`, `.bash`, `.h` | The source code is exposed as a dictionary under `__source__` |

### Automatic module lookup

If the path doesn't contain `/` and doesn't start with `.`, the interpreter also looks in the project's `libs/` folder.

---

## 18. Memory management

The interpreter has a configurable limit of **1024 memory slots** by default.

### `free` — releasing a variable

Explicitly removes a variable from scope:

```gbn
$free($my_variable) 
```

### `expand_memory` — increasing the limit

Increases the maximum number of available slots:

```gbn
$expand_memory(512)
```

> ! This emits a warning on `stderr` indicating the change.

### `breakpoint` — pausing execution

Pauses execution and returns a memory summary:

```gbn
$breakpoint()
```

### Expression caching

Expressions that appear repeatedly (for example, inside a loop) are cached as an AST the first time they're parsed, avoiding unnecessary re-parsing on each cycle:

```gbn
var i: int = 0
while $i < 10000
    var x = ($i * 5) + (20 / 2)  -- the expression is cached
    $i += 1
end
```

### Post-execution garbage collector

When execution finishes, the engine automatically frees global symbols that were defined but never read (global variables, functions, classes, imported namespaces). `$free($var)` can also be used if needed.

### `--sm` — memory summary

When using the `--sm` flag, the interpreter prints the complete memory state at the end:

```
Total memory: hp:int=100 | name:str='Juan' | ...
```

---

## 19. Built-in functions

These functions are available without needing to import anything:

| Function | Description |
|---------|-------------|
| `$print(value)` | Prints a value |
| `$int(value)` | Converts to integer |
| `$float(value)` | Converts to float |
| `$str(value)` | Converts to string |
| `$bool(value)` | Converts to boolean |
| `$range(n)` | Generates a range from 0 to n-1 |
| `$len(collection)` | Returns the length of a collection |
| `$file_read(path)` | Reads an entire file as a string |
| `$file_lines(path)` | Reads a file as an array of lines |
| `$file_write(path, content)` | Writes (overwrites) a file |
| `$file_append(path, content)` | Appends content to the end of a file |
| `$file_exists(path)` | Returns `true` if the file exists |

---

## 20. Standard library (stdutils)

`stdutils.gbn` is automatically loaded at the start of every program. It provides:

### Version constant

```gbn
$print($GBN.VERSION) 
```

### Collection functions

| Function | Description |
|---------|-------------|
| `$contains(collection, element)` | `true` if the element is in the collection |
| `$index_of(collection, element)` | Index of the element, or `-1` if it doesn't exist |
| `$has_key(dict, key)` | `true` if the key exists in the dictionary |
| `$merge_dict(dest, source)` | Merges `source` into `dest` and returns the result |

### String functions

| Function | Description |
|---------|-------------|
| `$str_split(text, delimiter)` | Splits a string into an array |
| `$str_join(separator, items)` | Joins an array of strings into one |
| `$to_lower(text)` | Converts to lowercase |
| `$to_upper(text)` | Converts to uppercase |
| `$starts_with(text, prefix)` | `true` if the text starts with the prefix |
| `$ends_with(text, suffix)` | `true` if the text ends with the suffix |

### Vector classes

| Function | Description |
|---------|-------------|
| `$vec2(x, y)` | 2-value float vector |
| `$vec2i(x, y)` | 2-value integer vector |
| `$vec3(x, y, z)` | 3-value float vector |
| `$vec3i(x, y, z)` | 3-value integer vector |
| `$color(r, g, b, a)` | 4-value float vector, clamped between 0 and 1, with `a` defaulting to 1 if no value is assigned |

> You can access the vector's values at any time via `.x, .y, .z` or `.r, .g, .b, .a`

### Clamping values

The first argument of `$max()` or `$min()` is the value to clamp, the second is the limit. If the clamped value exceeds the limit, the limit's own value is returned automatically instead.

```gbn
var min_value: int = $min(25, 12) -- The lowest possible value is 12
var max_value: int = $max(72, 100) -- The highest possible value is 100
```

### User input

```gbn
var name: str[64] = $input("What's your name? ")
```

### Pause for input

```gbn
$pause() -- Code stops here
```

---

## 21. Compiling to an executable

`--c`/`--fc` build a standalone executable with PyInstaller. **Neither flag runs your script for you to see** — the only thing printed is either the path to the resulting executable, or a message explaining why compilation was skipped.

```bash
Gybin my_script.gbn --c
```

The interpreter has no separate "syntax-only" checking pass — it's a tree-walking interpreter, so "checking for errors" and "running the script" are technically the same operation. `--c` still needs to know whether the script errors, so it runs it once internally with all output (stdout/stderr) fully suppressed — nothing it prints or does is ever shown, and its effects don't leak into anything printed afterward. `--fc` skips even that: it never touches the script at all, and just compiles unconditionally.

| Flag | Runs the script? | Compiles on error? |
|------|-------------------|---------------------|
| `--c` | Yes, but fully silenced (only to check for errors) | No — prints `Compilation skipped...` and exits |
| `--fc` | Never | Yes, always |

### `--n`, `--ad`, `--i`

```bash
Gybin game.gbn --c --n MyGame --ad assets/config.json --i icon.ico
```

- `--n NAME` — custom name for the compiled executable (default: the script's own filename, without extension).
- `--ad PATH[=DEST]` — bundles an extra file or folder into the executable. Repeatable. `DEST` is the destination folder inside the bundle (default: `.`).
- `--i ICON_PATH` — icon for the executable (`.ico` on Windows, `.icns` on macOS).

### Automatic bundling of imports

Every file brought in with `@use` or `@from ... @as` — at any depth (transitive imports included), and of any supported extension — is discovered automatically and embedded into the executable. The compiled program is fully self-contained: it does not need the original `.gbn` files (or the ones they import) to run.

`stdutils.gbn` is likewise embedded inside the executable and is never copied next to it as an external file — this is intentional: since it loads automatically on every run, an external editable copy would be a code-injection risk for a compiled binary.

If PyInstaller isn't available, a bash wrapper is generated instead (a `.bat` file on Windows) that invokes the interpreter directly:

```bash
#!/usr/bin/env bash
exec Gybin "my_script.gbn" "$@"
```

> ! A script whose own filename contains `:` compiles fine as the entry point. But a file it *imports* whose own name contains `:` cannot be bundled — PyInstaller's `--add-data` uses `:` as its SOURCE/DEST separator — you'll get a clear warning at compile time if this happens, and that one file is skipped rather than the whole build failing.

---

## 22. Warnings and static analysis

When running with `--w`, the engine activates a post-execution analysis that reports:

- **Variables declared but never read**
- **Functions defined but never called**
- **Functions with an empty body**
- **Classes defined but never instantiated**
- **Classes with an empty body**
- **Enums defined but never used**
- **Multi-type variables with more than 3 distinct types used**
- **Suspicious assignments** (declared type different from the actual type of the value)
- **Possible memory leaks**: global containers with more than 256 elements that are never read

Warnings are printed to `stderr` in this format:

```
Warning: file.gbn:42: Variable 'x' is declared but never read
```

> Variables whose names start with `_` are ignored by the analyzer (the "intentionally unused" convention).

> You may get warnings for code you never wrote — these belong to unused code from imported libraries.

---

## 23. Rules and best practices

### The `$` operator

`$` is **mandatory** for:
- Reading a variable's value: `$hp`
- Calling a function: `$print(...)`, `$add(1, 2)`
- Instantiating a class: `$Player("John")`
- Assigning to an existing variable: `$hp = 50`
- Chained access: `$p.damage(30)`

`$` is **not** used for:
- The initial declaration (`var hp: int = 100`)
- Accessing object fields after the dot (`$p.hp`, not `$p.$hp`)
- Parameter names in a function signature

### Scope

Variables declared inside a block (function, loop, conditional) are local to that block. Redefining an outer variable inside an inner scope can cause conflicts:

```gbn
var global: int = 100

func test() -> NULL
    var global: int = 50  -- local redefinition
    $print($global)       -- error: scope ambiguity
end
```

It's recommended to use different names for local variables that coexist with global variables of the same name.

### Using `any`

`any` disables type checking. It's recommended to use it only when strictly necessary, such as for variables that store values of an unknown type at declaration time.

### Initializing collections

Always initialize arrays and dicts with `[]` or `{}` if you plan to operate on them right away. Using `NULL` as the initial value and then trying to add elements without first assigning a real collection will produce an error.

```gbn
-- Correct:
var items: array[Item] = []
$items.append($Item("Sword"))

-- Problematic if append is used before assigning:
var items: array[Item] = NULL
$items.append($Item("Sword"))  -- error
```

### Closing blocks with `end`

Every block (`func`, `class`, `if`, `while`, `for`, `try`, `match`) must be closed with `end`. An unclosed block produces a `SyntaxError`.

> ! While it's possible to write code outside of functions, it's recommended that most of the script be organized into functions.

### Indentation

Indentation is not required by the language: blocks are delimited purely by keywords (`end`, `elseif`, `else`, `case`, etc.), never by whitespace.

> ! It's still recommended to indent for readability and organization, however removing it can have a positive impact on performance in large projects.
