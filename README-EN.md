# GybinScript — User Manual

> **Version:** 1.3.0
> **File Extension:** `.gbn`
> **Interpreter:** `Core/Gybin.py`
> **Execution:** `python3 (Interpreter dir: Core/Gybin.py) (File dir: My_script.gbn)`

> ! You can also declare the interpreter on the first line of your code and run it like any other program. (Linux only) Example:

```gbn
#!/home/(user)/GybinScript/Core/Gybin.py -- Parser dir

$print("Hello!")
```

```bash
chmod +x My_script.gbn
./My_script.gbn
```

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Console Execution](#2-console-execution)
3. [Data Types](#3-data-types)
4. [Variables and Constants](#4-variables-and-constants)
5. [Comments](#5-comments)
6. [Operators](#6-operators)
7. [Functions](#7-functions)
8. [Classes](#8-classes)
9. [Inheritance](#9-inheritance)
10. [Enums](#10-enums)
11. [Arrays](#11-arrays)
12. [Dictionaries](#12-dictionaries)
13. [Control Structures](#13-control-Structures)
14. [Error Handling](#14-error-handling)
15. [Pointers](#15-pointers)
16. [Modules and Imports](#16-modules-and-imports)
17. [Memory Management](#17-memory-management)
18. [Built-in Functions](#18-built-in-functions)
19. [Standard Library (stdutils)](#19-standard-library-stdutils)
20. [Executable Compilation](#20-executable-compilation)
21. [Warnings and Static Analysis](#21-warnings-and-static-analysis)
22. [Rules and Best Practices](#22-rules-and-best-practices)

---

## 1. Introduction

GybinScript is a statically typed interpreted scripting language with controlled memory management. It is designed to be expressive and predictable: all variables must be declared with a type, blocks are closed with `end`, and the `$` symbol is the mandatory prefix for reading or modifying any variable or calling any function.

---

## 2. Console Execution

```bash
python3 Core/Gybin.py my_script.gbn [options]
```

### Available Options

| Flag   | Description                                                   |
| ------ | ------------------------------------------------------------- |
| `--sm` | Displays memory status after execution                        |
| `--pr` | Automatically prints all values returned by `return`          |
| `--t`  | Displays execution time                                       |
| `--tr` | Shows each executed line instead of normal output             |
| `--c`  | Compiles the script into an executable if there are no errors |
| `--fc` | Compiles the script even if there are errors                  |
| `--w`  | Enables warning messages (static analysis)                    |
| `--nc` | Suppresses all standard output (errors are still displayed)   |

### Example

```bash
python3 Core/Gybin.py game.gbn --sm --w --t
```

---

## 3. Data Types

GybinScript provides six primitive types and two collection types:

| Type         | Description                   | Example          |
| ------------ | ----------------------------- | ---------------- |
| `int`        | Integer                       | `20`             |
| `float`      | Decimal number                | `3.1416`         |
| `str[N]`     | String with maximum size N    | `"Carlos"`       |
| `bool`       | Boolean                       | `true` / `false` |
| `any`        | No type restriction           | —                |
| `NULL`       | Null value / absence of value | `NULL`           |
| `array[T,...]`   | Typed list of elements        | `[1, 2, 3]`      |
| `dict[V,...]` | Typed values dictionary    | `{"a": 1}`       |

**Automatic conversions:**

* An `int` assigned to a `float` is automatically converted to `float`.
* A `float` without a decimal part assigned to an `int` is automatically converted to `int`.
* A `float` containing decimals assigned to an `int` produces a type error.

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

## 4. Variables and Constants

### Variable Declaration

The basic syntax is `var name: type = value`. The `$` symbol is used to read or modify the variable after it has been declared.

```gbn
var hp: int = 100
$hp = 50
```

### Size in the Name (Shorthand)

You can specify the maximum size directly in the variable name instead of the type annotation:

```gbn
var buffer[128]: str = "hello"
```

### Multiple Types

A variable can accept more than one type by separating them with commas. It is recommended to use this feature sparingly:

```gbn
var data: int,str = 10
$data = "text"
```

### Constants

Constants are declared using `const` and cannot be reassigned:

```gbn
const MAX_HP: int = 200
```

Attempting to modify a constant produces a type error (`Immutable constant`).

### `#onready`

The `#onready` modifier declares a variable before the program begins execution, making it useful for early dependency initialization:

```gbn
#onready var config: str[64] = "default"
```

### `NULL` as an Empty Value

`NULL` represents the absence of a value. Objects and complex variables are declared with `NULL` when they do not yet have definitive content:

```gbn
var name: str[32] = NULL
var hp: int = NULL
```

> ! The interpreter ignores objects with a `NULL` value until a value is assigned to them. For arrays and dictionaries, it is better to initialize them with `[]` or `{}` instead of `NULL` if you plan to add elements immediately.

---

## 5. Comments

### Single-Line Comment

Starts with `--` and extends to the end of the line:

```gbn
var x: int = 5 -- this is a comment
```

### Block Comment

Delimited with `!*` at the beginning and `!*` at the end. It may span multiple lines:

```gbn
!* This is
   a multi-line comment !*
```

> Block comments are not nested: the second `!*` closes the block opened by the first one.

---

## 6. Operators

### Arithmetic

| Operator | Operation      |
| -------- | -------------- |
| `+`      | Addition       |
| `-`      | Subtraction    |
| `*`      | Multiplication |
| `/`      | Division       |
| `%`      | Modulus        |
| `**`     | Power          |

### Comparison

| Operator | Meaning                             |
| -------- | ----------------------------------- |
| `==`     | Equal                               |
| `!=`     | Not equal                           |
| `<`      | Less than                           |
| `<=`     | Less than or equal                  |
| `>`      | Greater than                        |
| `>=`     | Greater than or equal               |
| `is`     | Value equality (equivalent to `==`) |

### Logical

| Operator | Meaning     |
| -------- | ----------- |
| `and`    | Logical AND |
| `or`     | Logical OR  |
| `not`    | Negation    |

### Compound Assignment

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

The return type is mandatory. Use `NULL` if the function does not return anything:

```gbn
func greet(name: str[32]) -> NULL
    $print("Hello " + $name)
end
```

### Function with Return Value

```gbn
func add(a: int, b: int) -> int
    return $a + $b
end

var result: int = $add(10, 20)
$print($result)
```

### Calling Functions

All function calls must be prefixed with `$`:

```gbn
$greet("Carlos")
$print($multiply($result, 2))
```

### Main Function (`init`) and `run`

The `run` keyword executes the `init()` function defined in the global scope. This is the standard way to structure a program entry point:

```gbn
func init() -> NULL
    $print("Program start")
end

run
```

> The `init()` function inside a class is that class's constructor, and it does not conflict with the global `init()` because they are used in different contexts.

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

`self` refers to the current instance and is automatically passed as the first argument when a method is called. You do not need to pass it when instantiating:

```gbn
var p: any = $Player("John")
$print($p.name)
$print($p.hp)
```

### Methods

Methods are defined inside the class exactly like functions, receiving `self` as their first parameter:

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

var p: any = $Player()
$p.damage(30)
$print($p.hp)  -- 70
```

### Field Access

Fields are accessed using the dot operator (`.`) without `$`:

```gbn
$print($p.name)
$p.hp = 50
```

---

## 9. Inheritance

A class can extend another class using `extends`:

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

var e: any = $Enemy()
$print($e.hp)     -- 50
$print($e.damage) -- 10
```

> **Important:** If the parent class already defines an `init()` method, the child class must use `__init__()` instead to avoid a naming conflict. The child class inherits all fields and methods from the parent class.

---

## 10. Enums

Enums group named constants under a common type:

```gbnn
enum Direction = {UP, DOWN, LEFT, RIGHT}

var dir: int = Direction.UP
$print($dir)  -- 0
```

Values are assigned automatically starting from `0`. They are accessed using `EnumName.MEMBER`.

### Enums Inside Classes

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

var sword: any = $Item("Sword", $ItemType.WEAPON)
```

---

## 11. Arrays

### Declaration

```gbn
var numbers: array[int] = []
```

Use `[]` to initialize an empty array. Using `NULL` without assigning elements immediately will cause an error when attempting to add values.

### Array Methods

| Method              | Description                               |
| ------------------- | ----------------------------------------- |
| `.append(value)`    | Adds an element to the end                |
| `.remove(index)`    | Removes the element at the given position |
| `.size()`           | Returns the number of elements            |
| `.duplicate()`      | Returns a copy of the array               |
| `.push_back(value)` | Alias for `append`                        |

```gbn
$numbers.append(10)
$numbers.append(20)
$numbers.append(30)

$print($numbers)       -- [10, 20, 30]

$numbers[1] = 50
$print($numbers)       -- [10, 50, 30]
```

### Arrays with Maximum Size

```gbn
var list: array[int][10] = []
```

This limits the array to a maximum of 10 elements.

### Arrays of Objects

It is recommended to use `any` for arrays containing class instances:

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

### Basic Usage

```gbn
$inventory["Potion"] = 5
$inventory["Sword"] = 1
$print($inventory)  -- {"Potion": 5, "Sword": 1}
```

### Dictionaries of Objects

```gbn
var inventory: dict[any] = {}
$inventory["weapon"] = Item("Sword")
$print($inventory["weapon"].name)
```

### Dictionary Methods

| Method         | Description                              |
| -------------- | ---------------------------------------- |
| `.size()`      | Returns the number of entries            |
| `.remove(key)` | Removes the entry with the specified key |
| `.duplicate()` | Returns a copy of the dictionary         |

## 13. Control Structures

### `if / elseif / else` Conditional

```gbn
if $x > 10
    $print("greater")
elseif $x == 10
    $print("equal")
else
    $print("less")
end
```

### `while` Loop

```gbn
var i: int = 0
while $i < 10
    $print($i)
    $i += 1
end
```

### `for in` Loop

Iterates over arrays, ranges, or dictionaries:

```gbn
for item in $enemies
    $print($item.hp)
end

for n in $range(5)
    $print($n)
end
```

### Loop Control Keywords

| Keyword    | Behavior                                          |
| ---------- | ------------------------------------------------- |
| `break`    | Exits the current loop                            |
| `continue` | Skips to the next iteration                       |
| `loop`     | Restarts the current iteration from the beginning |
| `pass`     | Does nothing (empty block placeholder)            |

### `await`

Pauses execution until a condition becomes true (polling every 10ms):

```gbn
await $ready == true
```

---

## 14. Error Handling

```gbn
try
    -- code that may fail
catch
    -- code executed if an error occurs
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

The `$$` operator creates a pointer to an existing variable. When reading the pointer, the current value of the referenced variable is obtained:

```gbn
var hp: int = 100
var ref = $$hp

$print($ref)  -- Displays the value of hp through the pointer
```

Pointers allow indirect access and can reference complex paths (`$$object.field`, `$$array[0]`). They are useful for aliases and dynamic references.

---

## 16. Modules and Imports

### `@use` — Import a Module

Loads a `.gbn` file (or another supported file type) and exposes all its symbols in the current scope:

```gbn
@use "utils.gbn"
@use "helpers"        -- automatically detects the extension
```

Importing is idempotent: if a module has already been loaded, it will not be executed again.

### `@from` / `@as` — Import with Alias

Loads a module and exposes it as a named namespace:

```gbn
@from "utils.gbn" @as utils
$print($utils.my_function())
```

### Supported Formats

| Extension                                  | Behavior                                                     |
| ------------------------------------------ | ------------------------------------------------------------ |
| `.gbn`                                     | Executed and merged into the current scope                   |
| `.py`                                      | Loaded as a Python module; its public attributes are exposed |
| `.c`, `.cpp`, `.asm`, `.sh`, `.bash`, `.h` | Source code is exposed as a dictionary under `__source__`    |

### Automatic Module Search

If the path does not contain `/` and does not begin with `.`, the interpreter also searches inside the project's `libs/` directory.

---

## 17. Memory Management

The interpreter has a configurable limit of **1024 memory slots** by default.

### `free` — Release a Variable

Explicitly removes a variable from the current scope:

```gbn
$free($my_variable)
```

### `expand_memory` — Increase the Limit

Increases the maximum number of available memory slots:

```gbn
$expand_memory(512)
```

This emits a warning to `stderr` indicating the change.

### Expression Cache

Expressions that appear repeatedly (for example, inside a loop) are stored as cached ASTs the first time they are parsed, preventing unnecessary reparsing during each iteration:

```gbn
var i: int = 0
while $i < 10000
    var x = ($i * 5) + (20 / 2)  -- expression is cached
    $i += 1
end
```

### Post-Execution Garbage Collector

When execution finishes, the engine automatically releases global symbols that were defined but never read (functions, classes, imported namespaces). Plain global variables are not affected; it is the programmer's responsibility to free them with `free` if necessary.

### `--sm` — Memory Summary

When using the `--sm` flag, the interpreter prints the complete memory state after execution:

```text
Total memory: hp:int=100 | name:str='John' | ...
```

## 18. Built-in Functions

These functions are available without importing anything:

| Function                      | Description                          |
| ----------------------------- | ------------------------------------ |
| `$print(value)`               | Prints a value                       |
| `$int(value)`                 | Converts to integer                  |
| `$float(value)`               | Converts to float                    |
| `$str(value)`                 | Converts to string                   |
| `$bool(value)`                | Converts to boolean                  |
| `$range(n)`                   | Generates a range from 0 to n-1      |
| `$len(collection)`            | Returns the length of a collection   |
| `$file_read(path)`            | Reads an entire file as a string     |
| `$file_lines(path)`           | Reads a file as an array of lines    |
| `$file_write(path, content)`  | Writes (overwrites) a file           |
| `$file_append(path, content)` | Appends content to the end of a file |
| `$file_exists(path)`          | Returns `true` if the file exists    |

---

## 19. Standard Library (stdutils)

`stdutils.gbn` is automatically loaded at the start of every program. It provides:

### Version Constant

```gbn
$print($GBN.VERSION)
```

### Collection Functions

| Function                         | Description                                        |
| -------------------------------- | -------------------------------------------------- |
| `$contains(collection, element)` | `true` if the element exists in the collection     |
| `$index_of(collection, element)` | Index of the element, or `-1` if it does not exist |
| `$has_key(dict, key)`            | `true` if the key exists in the dictionary         |
| `$merge_dict(dest, source)`      | Merges `source` into `dest` and returns the result |

### String Functions

| Function                      | Description                                    |
| ----------------------------- | ---------------------------------------------- |
| `$str_split(text, delimiter)` | Splits a string into an array                  |
| `$str_join(separator, items)` | Joins an array of strings into a single string |
| `$to_lower(text)`             | Converts text to lowercase                     |
| `$to_upper(text)`             | Converts text to uppercase                     |
| `$starts_with(text, prefix)`  | `true` if the text starts with the prefix      |
| `$ends_with(text, suffix)`    | `true` if the text ends with the suffix        |

### User Input

```gbn
var name: str[64] = $input("What is your name? ")
```

---

## 20. Executable Compilation

With the `--c` flag, the interpreter attempts to generate a standalone executable using PyInstaller:

```bash
python3 Core/Gybin.py my_script.gbn --c
```

If PyInstaller is not available, a Bash wrapper is generated that invokes the interpreter directly:

```bash
#!/usr/bin/env bash
exec python3 "Core/Gybin.py" "my_script.gbn" "$@"
```

With `--fc`, compilation is forced even if the script contains execution errors.

---

## 21. Warnings and Static Analysis

When executed with `--w`, the engine enables a post-execution analysis that reports:

* **Variables declared but never read**
* **Functions defined but never called**
* **Functions with empty bodies**
* **Classes defined but never instantiated**
* **Classes with empty bodies**
* **Enums defined but never used**
* **Multi-type variables using more than 3 distinct types**
* **Suspicious assignments** (declared type differs from the actual value type)
* **Potential memory leaks**: global containers with more than 256 elements that are never read

Warnings are printed to `stderr` using the format:

```text
Warning: file.gbn:42: Variable 'x' is declared but never read
```

> Variables whose names begin with `_` are ignored by the analyzer (the convention for "intentionally unused").

> You may receive warnings about code you never wrote; these belong to unused code from imported libraries.

---

## 22. Rules and Best Practices

### The `$` Operator

`$` is **mandatory** for:

* Reading the value of a variable: `$hp`
* Calling a function: `$print(...)`, `$add(1, 2)`
* Instantiating a class: `$Player("John")`
* Assigning to an existing variable: `$hp = 50`
* Chained access: `$p.damage(30)`

`$` is **not** used for:

* The initial declaration (`var hp: int = 100`)
* Accessing object fields after a dot (`$p.hp`, not `$p.$hp`)
* Parameter names in function signatures

### Scope

Variables declared inside a block (function, loop, conditional) are local to that block. Redefining an outer variable inside an inner scope may cause conflicts:

```gbn
var global: int = 100

func test() -> NULL
    var global: int = 50  -- local redefinition
    $print($global)       -- error: scope ambiguity
end
```

It is recommended to use different names for local variables that coexist with global variables of the same name.

### Using `any`

`any` disables type checking. It is recommended to use it only when strictly necessary, such as for variables that store class instances or values whose type is unknown at declaration time.

### Collection Initialization

Always initialize arrays and dictionaries with `[]` or `{}` if you plan to operate on them immediately. Using `NULL` as an initial value and then attempting to add elements without first assigning a real collection will produce an error.

```gbn
-- Correct:
var items: array[any] = []
$items.append($Item("Sword"))

-- Problematic if append is used before assignment:
var items: array[any] = NULL
$items.append($Item("Sword"))  -- error
```

### Closing Blocks with `end`

Every block (`func`, `class`, `if`, `while`, `for`, `try`) must be closed with `end`. An unclosed block produces a `SyntaxError`.

> ! While you can write outside of functions, it is recommended that most of the script be organized within functions.
