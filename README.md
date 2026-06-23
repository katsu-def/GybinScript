# GybinScript — User Manual

> [Read this manual in Spanish (README-ES.md)](./README-ES.md)

> **Version:** 1.4.0a  
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
16. [Modules and imports](#16-modules-and-imports)
17. [Memory management](#17-memory-management)
18. [Built-in functions](#18-built-in-functions)
19. [Standard library (stdutils)](#19-standard-library-stdutils)
20. [Compiling to an executable](#20-compiling-to-an-executable)
21. [Warnings and static analysis](#21-warnings-and-static-analysis)
22. [Rules and best practices](#22-rules-and-best-practices)

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
| `--c` | Compiles the script into an executable if there are no errors |
| `--fc` | Compiles the script even if there are errors |
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

The `$$` operator creates a pointer to an existing variable. Reading the pointer gives you the current value of the variable it points to:

```gbn
var hp: int = 100
var ref: any = $$hp

$print($ref)  -- Shows the value of hp through the pointer
```

Pointers allow indirect access and can point to complex paths (`$$object.field`, `$$array[0]`). They are useful for aliases and dynamic references.

---

## 16. Modules and imports

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

## 17. Memory management

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

## 18. Built-in functions

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

## 19. Standard library (stdutils)

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

### User input

```gbn
var name: str[64] = $input("What's your name? ")
```

### Pause for input

```gbn
$pause() -- Code stops here
```

---

## 20. Compiling to an executable

With the `--c` flag, the interpreter tries to generate a standalone executable using PyInstaller:

```bash
Gybin my_script.gbn --c
```

If PyInstaller isn't available, a bash wrapper is generated instead (a `.bat` file on Windows) that invokes the interpreter directly:

```bash
#!/usr/bin/env bash
exec Gybin "my_script.gbn" "$@"
```

A copy of `stdutils` will be created in the same directory where the file is compiled; other dependencies will be compiled normally if PyInstaller is available.

With `--fc`, compilation is forced even if the script has runtime errors.

---

## 21. Warnings and static analysis

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

## 22. Rules and best practices

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

Every block (`func`, `class`, `if`, `while`, `for`, `try`) must be closed with `end`. An unclosed block produces a `SyntaxError`.

> ! While it's possible to write code outside of functions, it's recommended that most of the script be organized into functions.
