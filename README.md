# GybinScript — User Manual 

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/katsu-def/GybinScript)

> [Read this manual in Spanish (README-ES.md)](./README-ES.md)

> **Version:** 1.6  
> **File extension:** `.gbn`  
> **Interpreter:** `Core/Gybin` \ `/usr/bin/Gybin`
> **Execution:** `Gybin (File path: My_script.gbn)`

> ! You can also declare the interpreter on the first line of your code and execute it like any program (Linux only). Ex: 

```gbn
#!/usr/bin/Gybin -- Parser path

$print("Hello!") 
```

```bash
chmod +x My_script.gbn
./My_script.gbn
```

> Run setup-linux to configure the Gybin launcher in '/usr/bin'
> Run setup-termux to set up the language in a Termux environment

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
13. [Control Structures](#13-control-structures)
14. [Error Handling](#14-error-handling)
15. [Pointers](#15-pointers)
16. [Events](#16-events)
17. [Modules and Imports](#17-modules-and-imports)
18. [Memory Management](#18-memory-management)
19. [Native Functions (built-ins)](#19-native-functions-built-ins)
20. [Standard Library (stdutils)](#20-standard-library-stdutils)
21. [Compilation to Executable](#21-compilation-to-executable)
22. [Warnings and Static Analysis](#22-warnings-and-static-analysis)
23. [Rules and Best Practices](#23-rules-and-best-practices)

---

## 1. Introduction

GybinScript is a statically typed and interpreted scripting language with controlled memory management. It is designed to be expressive and predictable: all variables must be declared with a type, blocks are closed with `end`, and the `$` sign is the mandatory prefix to read or modify any variable, or call any function.

---

## 2. Console Execution

```bash
Gybin my_script.gbn [options]
```

### Available Options

| Flag | Description |
|------|-------------|
| `--sm` | Displays memory status upon completing execution |
| `--pr` | Automatically prints all values returned by `return` |
| `--t` | Displays execution time |
| `--tr` | Displays each executed line instead of normal output |
| `--c` | Compiles the script to an executable — see [§21](#21-compilation-to-executable). Does **not** execute the script |
| `--fc` | Unconditionally compiles the script, even if it has errors — see [§21](#21-compilation-to-executable) |
| `--n NAME` | Custom name for the compiled executable (only with `--c`/`--fc`) |
| `--ad PATH[=DEST]` | Packages an extra file/folder into the executable; can be repeated (only with `--c`/`--fc`) |
| `--i ICON_PATH` | Icon for the compiled executable (only with `--c`/`--fc`) |
| `--w` | Enables warning messages (static analysis) |
| `--nc` | Suppresses all standard output (errors are still displayed) |

### Example

```bash
Gybin game.gbn --sm --w --t
```

---

## 3. Data Types

GybinScript features six primitive types and two collection types:

| Type | Description | Example |
|------|-------------|---------|
| `int` | Integer | `20` |
| `float` | Decimal | `3.1416` |
| `str[N]` | String with a maximum length N | `"Carlos"` |
| `bool` | Boolean | `true` / `false` |
| `any` | No type restriction | — |
| `NULL` | Null value / absence of value | `NULL` |
| `array[T,...]` | Typed list of elements | `[1, 2, 3]` |
| `dict[V,...]` | Typed dictionary of values | `{"a": 1}` |
| `ptr` | Pointer/reference to another variable, constant, function, or class (see [§15](#15-pointers)) | `$$hp` |

**Automatic Coercions:**
- An `int` assigned to a `float` is automatically converted to `float`.
- A `float` without a decimal part assigned to an `int` is converted to `int`.
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

### Bit Width for `int` / `float`

Both numeric types use 64 bits by default. Instead of introducing separate type names for smaller bit widths, the same `[N]` size syntax used by `str` is reused to select a narrower width:

```gbn
var integer: int[16] = 1000       -- Signed 16-bit int: -32768..32767
var decimal: float[32] = 3.14    -- 32-bit float (IEEE-754 single precision)
var other: float [32] = 2.71      -- A space before the bracket is also accepted
```

| Type | Valid Widths |
|------|--------------|
| `int[N]` | 8, 16, 32, 64 |
| `float[N]` | 16, 32, 64 |

A value that does not fit into the declared width results in an immediate error, along with a suggestion for a width that would contain it:

```gbn
var small: int[8] = 500  -- error: does not fit in a signed 8-bit int (range -128..127). Use int[16] or larger.
```

**Coercion between `int` and `float` requires bit widths to match.** Implicit int <-> float conversions (see "Automatic Coercions" above) only occur when both sides have the *same* declared bit width — or when neither specifies one (both default to 64):

```gbn
var float_val: float = 3.14
var int_val: int[32] = $float_val   -- Error: coercion requires equal widths (64 vs 32)

var float32_val: float[32] = 3.14
var int32_val: int[32] = $float32_val  -- OK: both are 32 bits
```

This applies equally to constants as well as function parameters and return types:

```gbn
func sum(a: int[16], b: int[16]) -> int[16]
    return a + b
end
```

Element types of `array`/`dict` never track a specific bit width — `array[int]` accepts `int` values of any width mixed together, since a container does not have its own per-element type annotation. Writing `array[int[16]]` is rejected as ambiguous (it is unclear to which elements it would apply); use a plain `array[int]` instead.

### f-strings

String literals prefixed with `f` support `{expression}` interpolation, including format specifiers and conversions:

```gbn
var name: str = "Ana"
$print(f"Hello {$name}!")
$print(f"{3.14159:.2f}")   -- 3.14
```

---

## 4. Variables and Constants

### Variable Declaration

The basic syntax is `var name: type = value`. The `$` sign is used to read or modify the variable after declaring it.

```gbn
var hp: int = 100
$hp = 50
```

### Size in Name (Shorthand)

You can specify the maximum size directly in the variable name instead of the type annotation:

```gbn
var buffer[128]: str = "hello"
```

### Multiple Types

A variable can accept more than one type by separating them with commas. Use sparingly:

```gbn
var data: int,str = 10
$data = "text"
```

### Constants

Constants are declared with `const` and cannot be reassigned:

```gbn
const MAX_HP: int = 200
```

Attempting to modify a constant produces a type error (`Immutable constant`).

### `#onready`

The `#onready` modifier declares a variable before the program starts executing, useful for early dependency initialization:

```gbn
#onready var config: str[64] = "default"
```

When used, reassignments of the same value are also prevented.

### `#reserved`

`#reserved` is used to declare script elements private, meaning they cannot be used outside the script where they were declared:

```gbn
#reserved var critical: bool = false
```

### `#public`

`#public` is the counterpart to `#reserved` regarding readability. It changes nothing functionally — a variable, function, or class is already public by default — existing solely to declare that intent explicitly in code:

```gbn
#public var health: int = 100
```

### `#inmutable`

`#inmutable` behaves like `const` for direct assignment — `$name = value` throws the same error as a constant — but unlike a true `const`, its value **can** be changed indirectly via a [pointer](#15-pointers):

```gbn
#inmutable var x: int = 5
$x = 10              -- error: 'x' is #inmutable

var p: ptr = $$x
$p.value = 99         -- OK — x is now 99
```

A true `const` remains completely locked down even through a pointer; `#inmutable` is the version that allows that single deliberate loophole.

### `NULL` as Empty Value

`NULL` represents the absence of a value. Objects and complex variables are declared with `NULL` when they do not yet hold definitive content:

```gbn
var name: str[32] = NULL
var hp: int = NULL
```

> ! The interpreter ignores objects with a `NULL` value until assigned one. In arrays and dicts, it is better to initialize with `[]` or `{}` instead of `NULL` if you plan to append elements immediately.

---

## 5. Comments

### Single-line Comment

Starts with `--` and extends to the end of the line:

```gbn
var x: int = 5 -- this is a comment
```

### Block Comment

Delimited by `!*` at the start and `!*` at the end. Can span multiple lines:

```gbn
!* This is a multi-line
   comment !*
```

> Block comments do not nest: the second `!*` closes the block opened by the first.

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
| `**` | Exponentiation |

### Comparison

| Operator | Meaning |
|----------|---------|
| `==` | Equal |
| `!=` | Not equal |
| `<` | Less than |
| `<=` | Less than or equal to |
| `>` | Greater than |
| `>=` | Greater than or equal to |
| `is` | Equal by value (equivalent to `==`) |

### Logical

| Operator | Meaning |
|----------|---------|
| `and` | Logical AND |
| `or` | Logical OR |
| `not` | Negation |

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

The return type is mandatory. Use `NULL` if the function returns nothing:

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

All calls must be prefixed with `$`:

```gbn
$greet("Carlos")
$print($multiply($result, 2))
```

### Explicit Bit Widths in Parameters and Return Types

`int[N]`/`float[N]` (see [§3](#3-data-types)) also work in function signatures:

```gbn
func sum(a: int[16], b: int[16]) -> int[16]
    return $a + $b
end
```

> ! The same width-matching rule applies to arguments: callers passing a variable declared with a different explicit bit width than the parameter must convert it explicitly first.

### Main Function (`init`) and `run`

The `run` keyword executes the `init()` function defined in the global scope. This is the standard way to structure a program's entry point:

```gbn
func init() -> NULL
    $print("Program started")
end

run
```

> The `init()` function inside a class serves as that class's constructor and does not collide with global `init()` because they are used in different contexts.

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

`self` refers to the current instance and is automatically passed as the first argument when a method is invoked. You do not pass it when instantiating:

```gbn
var p: any = $Player("Juan")
$print($p.name)
$print($p.hp)
```

### Methods

Methods are defined inside the class just like functions, accepting `self` as their first parameter:

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

### Field Access

Fields are accessed using a dot (`.`) without `$`:

```gbn
$print($p.name)
$p.hp = 50
```

---

## 9. Inheritance

A class can extend another using `extends`:

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

> ! If the parent class already defines an `init()` method, the child class must use `__init__()` instead to prevent name collisions. The child class inherits all fields and methods from the parent class.

---

## 10. Enums

Enums group named constants under a common type:

```gbn
enum Direction = {UP, DOWN, LEFT, RIGHT}

var dir: int = Direction.UP
$print($dir)  -- 0
```

Values are automatically assigned starting from `0`. They are accessed using `EnumName.MEMBER`.

### `.null`, Iteration, and `in`

Every enum has an implicit `.null` member — a sentinel signifying "nothing from this enumeration has been saved yet." It is separate from declared enum members and never counted among them:

```gbn
enum Direction = {UP, DOWN, LEFT, RIGHT}

var current: Direction = Direction.null
$print($current)  -- distinct from the value of any declared member
```

An enum is directly iterable using `for ... in` and supports the `in` membership operator — both iterate strictly over declared members, never `.null`:

```gbn
for d in $Direction
    $print(d)          -- UP, DOWN, LEFT, RIGHT — never .null
end

if Direction.UP in $Direction
    $print("UP is a member")
end
```

### Enums in Classes

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

Use `[]` to initialize an empty array. Using `NULL` without assigning elements immediately will cause an error when trying to append.

### Array Methods

| Method | Description |
|--------|-------------|
| `.append(value)` | Appends an element to the end |
| `.remove(index)` | Removes the element at the given index |
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

### Arrays with Maximum Size

```gbn
var list: array[int][10] = []
```

This caps the array at a maximum of 10 elements.

### Arrays of Objects

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

| Method | Description |
|--------|-------------|
| `.size()` | Returns the number of entries |
| `.remove(key)` | Removes the entry with that key |
| `.duplicate()` | Returns a copy of the dictionary |

---

## 13. Control Structures

### Conditional `if / elseif / else`

```gbn
if $x > 10
    $print("greater")
elseif $x == 10
    $print("equal")
else
    $print("smaller")
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

### `match` Conditional

Compares a subject against several potential values. Each case opens with `case value1, value2` (multiple comma-separated labels are permitted). Only the first matching case executes (or `else`, if present); there is no fallthrough between cases.

```gbn
match $day
    case 1
        $print("Monday")
    case 2, 3
        $print("Tuesday or Wednesday")
    else
        $print("Other day")
end
```

Case labels can be any evaluable expression: literals, variables, enum members (`Color.RED`), or even array/dict literals (`[1, 2, 3]`, `{"a": 1}`). If nothing matches and there is no `else`, nothing happens — no error is raised.

### Loop Control Keywords

| Keyword | Behavior |
|---------|----------|
| `break` | Exits the current loop |
| `continue` | Skips to the next iteration |
| `loop` | Restarts the current iteration from the beginning |
| `pass` | Does nothing (empty block placeholder) |

`loop` is easily confused with `continue` because in a simple `while` loop they look similar, but they are not identical: `continue` advances to the *next* iteration (the next item of a `for`, or rechecks a `while` condition), whereas `loop` re-executes the *same* iteration from the start, with its state left exactly as it was — the same item in `for`, without rechecking the `while` condition — until it finishes normally.

```gbn
var attempts: int = 0
for item in [10, 20]
    $attempts += 1
    $print(f"trying {item}")
    if item == 10 and $attempts < 2
        loop  -- restarts with item still at 10, not 20
    end
end
-- prints: trying 10 / trying 10 / trying 20
```

### `await`

Pauses execution until a condition becomes true (polls every 10ms):

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

The `$$` operator creates a pointer to an existing variable, constant, function, or class (e.g., `$$hp`, `$$Damage`, `$$self.hp`, `$$arr[0]`). It is typed using `ptr` — the only type annotation that can hold a pointer value:

```gbn
var hp: int = 100
var ref: ptr = $$hp
```

> ! Reading a pointer variable directly (`$print(ref)`) prints the pointer itself, not the value it references — use `.value` or `.get()` to read through it.

### Pointer Methods and Properties

A pointer never carries a copy of what it points to — it resolves the target fresh every time one of these is accessed:

| Member | Description |
|--------|-------------|
| `.value` | Gets the current value of the referenced variable/constant. Can also be assigned (`$ref.value = 75`) to write through the pointer |
| `.get()` | Same as `.value`, as a method call |
| `.set(value)` | Same as assigning `.value`, as a method call |
| `.call(args...)` | Invokes the referenced function/class, forwarding given arguments |
| `.name` | The name of the referenced memory space |
| `.is_callable` | `true` if the pointer references a function or class, `false` for a variable/constant |
| `.is_mutable` | `true` only for a non-`#reserved` and non-constant variable |
| `.size` | Approximate size in bytes of the referenced value |
| `.ref` | The actual memory address (identity) of the referenced value |

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

- Only variables can be modified through a pointer. Constants are always immutable, and functions/classes cannot be assigned values — `.set()`/`.value = ...` throws an error in either case.
- A variable declared with `#reserved` can never be mutated through a pointer, even by code holding a reference to it.
- Writing through a pointer (`.set()`/`.value = ...`) accepts any value type; a mismatch against the target's declared type triggers a warning (with `--w`) instead of a strict type error.
- Referencing a function or class purely by name (without `$$`) is a script error — `$$name` is the sole way to obtain a reference to one without invoking it.

Pointers enable indirect access and can target complex paths (`$$object.field`, `$$array[0]`). They are useful for aliasing, dynamic references, and passing function references (for instance, when attaching handlers to an [event](#16-events)).

### Raw Address Pointers

A `ptr` can also be constructed from a raw integer address instead of `$$target`:

```gbn
var memory: ptr = 0x7fff5fbff80c
```

> ! This does **not** dereference actual process memory — doing so safely from an AST-walking interpreter is impossible (there is no way to know if a given address is even valid, and attempting to do so risks crashing the process or reading unowned memory). What you obtain instead is an opaque handle storing the address as pure identity:

```gbn
$print($memory.ref)          -- the address itself
$print($memory.name)         -- "0x7fff5fbff80c"
$print($memory.is_callable)  -- false
$print($memory.is_mutable)   -- false
$print($memory.size)         -- native pointer size (8 bytes)

$print($memory.value)        -- error: nothing to dereference
$memory.value = 5             -- error: nowhere to write
$memory.call()                -- error: nothing to call
```

Same object, same member surface as a standard pointer — `.value`, `.set()`, and `.call()` simply have nothing to act on, and state so clearly rather than guessing.

---

## 16. Events

An `event` declares a lightweight signal: a name plus a parameter list:

```gbn
event player_is_dead(entity: str)
```

Type annotations on parameters serve strictly as documentation — an event has no body against which to validate them.

### `.connect(handler)` and `.emit(...)`

Every event exposes two methods, both called using the `$` prefix like any other call:

| Method | Description |
|--------|-------------|
| `.connect(handler)` | Registers a function to execute whenever the event fires. `handler` must be a function reference created using `$$function_name` — passing just the function name causes an error |
| `.emit(args...)` | Calls each connected handler in the order they were attached, forwarding provided arguments. Argument count must match the parameter count declared by the event |

```gbn
event player_is_dead(entity: str)

func on_player_dead(entity: str) -> NULL
    $print(entity + " died")
end

$player_is_dead.connect($$on_player_dead)

if $health <= 0
    $player_is_dead.emit("Zombie")
end
```

Multiple handlers can be connected to the same event; all will execute in the order attached when `.emit(...)` is called.

---

## 17. Modules and Imports

### `@use` — Importing a Module

Loads a `.gbn` file (or other supported format) and exposes all its symbols in the current scope:

```gbn
@use "utils.gbn"
@use "helpers"        -- detects extension automatically
```

Importing is idempotent: if a module was already loaded, it is not re-executed.

### Importing Multiple Modules at Once

```gbn
@use math, random, sys
```

Each loads independently, exactly as if on its own `@use` line. `@as` is not allowed on `@use` with multiple modules — a single alias cannot represent multiple distinct modules — import them one per line if each requires its own name:

```gbn
@use math @as math_lib
@use random @as rand_lib
```

### `@from` / `@as` — Importing with Aliases

Loads a module and exposes it under a named namespace:

```gbn
@from "utils.gbn" @as utils
$print($utils.my_function())
```

`@use path @as alias` (single module) accomplishes the exact same thing — identical functionality reached via either keyword.

### Selective Imports (`@from ... @use`)

Loading an entire module to use only one or two functions wastes memory on everything else defined within it, and can fill `--w` output with warnings about symbols the importer never requested. `@from module @use $$symbol` loads only named symbols instead of executing the whole module and pulling in everything it exposes:

```gbn
@from math @use $$_sqrt
$print($_sqrt(4.0))
```

Multiple symbols from the same module, separated by commas:

```gbn
@from math @use $$_PI, $$_E, $$_sqrt
```

Add `@as` to group selected symbols under a single namespace rather than dumping them directly into current scope — permitted here (unlike multi-module `@use` above) because everything still originates from a single module:

```gbn
@from sys @use $$_format_time, $$_miliseconds @as os
$print($os._format_time())
```

`#reserved` symbols still cannot be imported this way, selectively or otherwise.

### Supported Formats

| Extension | Behavior |
|-----------|----------|
| `.gbn` | Executed and integrated into the current scope |
| `.py` | Loaded as a Python module; public attributes exposed |
| `.c`, `.cpp`, `.asm`, `.sh`, `.bash`, `.h` | Source code exposed as a dictionary under `__source__` |

### Automatic Module Search

If the path contains no `/` and does not start with `.`, the interpreter also searches in the project's `libs/` directory.

---

## 18. Memory Management

The interpreter features a configurable default limit of **1024 memory slots**.

### `free` — Freeing a Variable

Explicitly removes a variable from scope:

```gbn
$free($my_variable) 
```

### `expand_memory` — Expanding the Limit

Increases the maximum number of available slots:

```gbn
$expand_memory(512)
```

> ! This outputs a warning to `stderr` indicating the change.

### `breakpoint` — Pausing Execution

Pauses execution and returns a memory summary:

```gbn
$breakpoint()
```

### Expression Caching

Expressions appearing repeatedly (e.g., inside a loop) are cached as AST upon first parse, avoiding redundant re-parsing during each iteration:

```gbn
var i: int = 0
while $i < 10000
    var x = ($i * 5) + (20 / 2)  -- expression is cached
    $i += 1
end
```

### Post-execution Garbage Collector

Upon program completion, the engine automatically frees global symbols defined but never read (global variables, functions, classes, imported namespaces). `$free($var)` can also be used manually if needed.

### `--sm` — Memory Summary

When using the `--sm` flag, the interpreter prints full memory status on termination:

```
Total memory: hp:int=100 | name:str='Juan' | ...
```

---

## 19. Native Functions (built-ins)

These functions are available without importing anything:

| Function | Description |
|----------|-------------|
| `$print(value)` | Prints a value |
| `$reprint(value)` | Like `$print`, but overwrites the current line instead of starting a new one — see below |
| `$int(value)` | Converts to integer |
| `$float(value)` | Converts to float |
| `$str(value)` | Converts to string |
| `$bool(value)` | Converts to boolean |
| `$range(n)` | Generates a range from 0 to n-1 |
| `$len(collection)` | Returns collection length |
| `$file_read(path)` | Reads an entire file as a string |
| `$file_lines(path)` | Reads a file as an array of lines |
| `$file_write(path, content)` | Writes (overwrites) a file |
| `$file_append(path, content)` | Appends content to the end of a file |
| `$file_exists(path)` | Returns `true` if the file exists |

### Named Arguments in `$print`

`$print` accepts `sep`, `end`, and `flush` by name:

```gbn
$print("a", "b", sep="-", end="")   -- a-b, no trailing newline
$print("c")
```

### `$reprint` — Updating a Line in Place

Status and progress outputs typically need to overwrite the same terminal line rather than pushing down a new line on every call. `$reprint` achieves this without requiring manual `
` and ANSI clear sequence handling:

```gbn
$reprint("loading 10%")
$reprint("loading 100%")
$reprint("done!", end="
")   -- pass end="
" to close the line and return to normal $print
$print("after")
```

By default, it adds no trailing newline (so subsequent calls overwrite) and flushes immediately. Passing `end="
"` makes it behave identically to `$print`.

---

## 20. Standard Library (stdutils)

`stdutils.gbn` is automatically loaded at startup for every program. It provides:

### Version Constant

```gbn
$print($GBN.VERSION) 
```

### Collection Functions

| Function | Description |
|---------|-------------|
| `$contains(collection, element)` | `true` if element exists in collection |
| `$index_of(collection, element)` | Index of element, or `-1` if missing |
| `$has_key(dict, key)` | `true` if key exists in dictionary |
| `$merge_dict(dest, source)` | Merges `source` into `dest` and returns result |

### String Functions

| Function | Description |
|---------|-------------|
| `$str_split(text, delimiter)` | Splits string into an array |
| `$str_join(separator, items)` | Joins an array of strings into one |
| `$to_lower(text)` | Converts string to lowercase |
| `$to_upper(text)` | Converts string to uppercase |
| `$starts_with(text, prefix)` | `true` if text starts with prefix |
| `$ends_with(text, suffix)` | `true` if text ends with suffix |

### Vector Classes

| Function | Description |
|---------|-------------|
| `$vec2(x, y)` | Vector of 2 float values |
| `$vec2i(x, y)` | Vector of 2 int values |
| `$vec3(x, y, z)` | Vector of 3 float values |
| `$vec3i(x, y, z)` | Vector of 3 int values |
| `$color(r, g, b, a)` | Vector of 4 float values (0 to 1 range), where `a` defaults to 1 if unassigned |

> You can access vector components at any time via `.x, .y, .z` or `.r, .g, .b, .a`.

### Value Clamping

The first argument of `$max()` or `$min()` is the target value, and the second is the boundary. If the target exceeds the boundary limit, the boundary value is automatically returned:

```gbn
var min_val: int = $min(25, 12) -- Minimum possible value is 12
var max_val: int = $max(72, 100) -- Maximum possible value is 100
```

### User Input

```gbn
var name: str[64] = $input("What is your name? ")
```

### Pause for Input

```gbn
$pause() -- Code execution stops here until key press
```

---

## 21. Compilation to Executable

`--c`/`--fc` generate a standalone executable using PyInstaller. **Neither flag executes your script for display** — the only output printed is the path of the resulting executable or a message explaining why compilation was skipped.

```bash
Gybin my_script.gbn --c
```

The interpreter lacks a dedicated "syntax-check only" mode — it is an AST-walking engine, meaning error checking and script execution are technically the same operation. `--c` still verifies script validity, running it once internally with all output (stdout/stderr) completely muted — none of its output or side effects leak. `--fc` skips even that: it never touches script execution and compiles unconditionally.

| Flag | Executes Script? | Compiles on Error? |
|------|-------------------|--------------------|
| `--c` | Completely muted (error checking only) | No - prints `Compilation skipped...` and exits |
| `--fc` | Never | Yes, always |

### `--n`, `--ad`, `--i`

```bash
Gybin game.gbn --c --n MyGame --ad assets/config.json --i icon.ico
```

- `--n NAME` — custom name for compiled executable (defaults to script filename without extension).
- `--ad PATH[=DEST]` — packages an extra file/folder into executable. Can be repeated. `DEST` is target destination folder inside package (defaults to `.`).
- `--i ICON_PATH` — executable icon (`.ico` on Windows, `.icns` on macOS).

### Automatic Import Packaging

Every file imported via `@use` or `@from ... @as` — at any depth level (including transitive imports) and of any supported extension — is automatically detected and embedded in the binary. The compiled program becomes completely self-contained, requiring no original `.gbn` files to run.

`stdutils.gbn` is also embedded directly inside the binary and is never copied alongside as an external file — this is intentional: as it auto-loads on every execution, an editable external copy would pose a code injection security risk for a compiled binary.

If PyInstaller is unavailable, a bash wrapper (`.bat` on Windows) is generated instead:

```bash
#!/usr/bin/env bash
exec Gybin "my_script.gbn" "$@"
```

> ! A script whose own filename contains `:` compiles fine as an entry point. However, imported files containing `:` in their filename cannot be bundled, as PyInstaller's `--add-data` uses `:` as a SOURCE/DEST separator. You will receive a clear warning during compilation if this occurs, and only that file will be skipped rather than failing the entire compilation process.

---

## 22. Warnings and Static Analysis

When executing with `--w`, the engine activates post-execution static analysis reporting:

- **Declared variables that are never read**
- **Defined functions that are never called**
- **Functions with empty bodies**
- **Defined classes that are never instantiated**
- **Classes with empty bodies**
- **Defined enums that are never used**
- **Multi-type variables with more than 3 distinct types assigned**
- **Suspicious assignments** (declared type differs from actual value type)
- **Potential memory leaks**: global containers holding over 256 unread elements

Warnings output to `stderr` following this format:

```
Warning: file.gbn:42: Variable 'x' is declared but never read
```

> Variables prefixed with `_` are ignored by the static analyzer (by convention representing intentionally unused items).

> Warnings may occasionally flag code you did not write if it belongs to unused routines within imported libraries.

---

## 23. Rules and Best Practices

### The `$` Operator

`$` is **mandatory** for:
- Reading variable values: `$hp`
- Calling functions: `$print(...)`, `$add(1, 2)`
- Instantiating classes: `$Player("Juan")`
- Assigning to an existing variable: `$hp = 50`
- Chained member calls: `$p.damage(30)`

`$` is **not** used in:
- Initial declarations (`var hp: int = 100`)
- Accessing object fields following a dot (`$p.hp`, not `$p.$hp`)
- Parameter names in function signatures

### Scope

Variables declared inside a block (function, loop, conditional) are local to that block. Shadowing an outer variable inside an inner scope can cause ambiguity conflicts:

```gbn
var global_val: int = 100

func test() -> NULL
    var global_val: int = 50  -- local redefinition
    $print($global_val)       -- error: scope ambiguity
end
```

It is recommended to use distinct names for local variables coexisting with global variables of similar purpose.

### Use of `any`

`any` disables type checking. Use it strictly when necessary, such as for variables receiving values of unknown type at declaration time.

### Collection Initialization

Always initialize arrays and dicts with `[]` or `{}` if you intend to manipulate them immediately. Using `NULL` initially and attempting to append items without first instantiating a container produces an error.

```gbn
-- Correct:
var items: array[Item] = []
$items.append($Item("Sword"))

-- Problematic if appending before assignment:
var items: array[Item] = NULL
$items.append($Item("Sword"))  -- error
```

### Closing Blocks with `end`

Every block structure (`func`, `class`, `if`, `while`, `for`, `try`, `match`) must terminate with `end`. Unclosed blocks raise a `SyntaxError`.

> ! While writing code outside functions is supported, organizing most of your script logic into functions is strongly recommended.

### Indentation

> ! Indentation is not strictly required by the parser; however, keeping consistent indentation is recommended for readability. Furthermore, stripping indentation can marginally benefit performance in large scale codebases.
