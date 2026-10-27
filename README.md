# GybinScript — User Manual

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/katsu-def/GybinScript)

> [Read this manual in Spanish (README-ES.md)](./README-ES.md)

> **Version:** 1.7.1  
> **File extension:** `.gbn`  
> **Interpreter:** `Core/Gybin` \ `/usr/bin/Gybin`
> **Invocation:** `Gybin (File path: My_script.gbn)`

> You can also declare the interpreter on the first line of your code and run it like any other program (Linux only). Example: 

```gbn
#!/usr/bin/Gybin -- parser path

$print("Hello!") 
```

```bash
chmod +x Mi_script.gbn
./Mi_script.gbn
```

> Run setup-linux to configure the Gybin launcher in '/usr/bin'
> Run setup-termux to configure the language in a Termux environment

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Running from the Console](#2-running-from-the-console)
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
13. [Control Flow](#13-control-flow)
14. [Error Handling](#14-error-handling)
15. [Pointers](#15-pointers)
16. [Events](#16-events)
17. [Modules and Imports](#17-modules-and-imports)
18. [Memory Management](#18-memory-management)
19. [Built-in Functions](#19-built-in-functions)
20. [Standard Library (stdutils)](#20-standard-library-stdutils)
21. [Compiling to an Executable](#21-compiling-to-an-executable)
22. [Warnings and Static Analysis](#22-warnings-and-static-analysis)
23. [Rules and Best Practices](#23-rules-and-best-practices)

---

## 1. Introduction

GybinScript is a statically typed, interpreted scripting language with controlled memory management. It is designed to be expressive and predictable: all variables must be declared with a type, blocks are closed with `end`, and `$` is the required prefix for reading or modifying any variable or calling any function.

---

## 2. Running from the Console

```bash
Gybin my_script.gbn [options]
```

### Available Options

| Flag | Description |
|------|-------------|
| `--sm` | Shows memory status when execution finishes |
| `--pr` | Automatically prints all values returned by `return` |
| `--t` | Shows execution time |
| `--tr` | Shows each executed line instead of normal output |
| `--c` | Compiles the script into an executable — see [§21](#21-compiling-to-an-executable). **Does not** run the script |
| `--fc` | Compiles the script unconditionally, even if it has errors — see [§21](#21-compiling-to-an-executable) |
| `--n NAME` | Custom name for the compiled executable (only with `--c`/`--fc`) |
| `--ad PATH[=DESTINATION]` | Bundles an extra file/folder into the executable; can be repeated (only with `--c`/`--fc`) |
| `--i ICON_PATH` | Icon for the compiled executable (only with `--c`/`--fc`) |
| `--w` | Enables warning messages (static analysis) |
| `--nc` | Suppresses all standard output (errors are still displayed) |
| `--nch` | Disables caching for this run: `#onready` functions always execute and `$preload` always reads from disk — see [§7](#7-functions) and [§18](#18-memory-management) |

### Example

```bash
Gybin juego.gbn --sm --w --t
```

---

## 3. Data Types

GybinScript has six primitive types and two collection types:

| Type | Description | Example |
|------|-------------|---------|
| `int[B]` | Integer with a maximum bit width of B | `20` |
| `float[B]` | Floating-point number with a maximum bit width of B | `3.1416` |
| `str[N]` | String with a maximum length of N characters | `"Carlos"` |
| `bool` | Boolean | `true` / `false` |
| `any` | Unrestricted type | — |
| `NULL` | Null value / absence of a value | `NULL` |
| `array[T,...]` | Typed list of elements | `[1, 2, 3]` |
| `dict[V,...]` | Typed dictionary of values | `{"a": 1}` |
| `ptr` | Pointer/reference to another variable, constant, function, class, or event; can be constrained with `ptr[target_types][data_types]` (see [§15](#15-pointers)) | `$$hp` |

**Automatic coercions:**
- An `int` assigned to a `float` is automatically converted to `float`.
- A `float` without a fractional part assigned to an `int` is converted to `int`.
- A `float` with a fractional part assigned to an `int` raises a type error.

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

Both numeric types use 64 bits by default. Instead of introducing separate type names for smaller widths, the same `[N]` size syntax already used by `str` is reused to choose a narrower width:

```gbn
var integer_value: int[16] = 1000       -- signed 16-bit int: -32768..32767
var decimal_value: float[32] = 3.14    -- 32-bit float (IEEE-754 single precision)
var other_value: float [32] = 2.71      -- a space before the bracket is also accepted
```

| Type | Valid widths |
|------|-----------------|
| `int[B]` | 8, 16, 32, 64 |
| `float[B]` | 16, 32, 64 |

A value that does not fit the declared width causes an immediate error, with a suggestion for a width that would fit it:

```gbn
var small: int[8] = 500  -- error: does not fit in a signed 8-bit int (range -128..127). Use int[16] or higher.
```

**Coercion between `int` and `float` requires matching widths.** An implicit int <-> float conversion (see “Automatic coercions” above) only occurs when both sides have the *same* declared bit width — or when neither specifies one (both default to 64):

```gbn
var float_value: float = 3.14
var integer_value: int[32] = $float_value   -- Error: coercion requires equal widths (64 vs 32)

var float32_value: float[32] = 3.14
var integer32_value: int[32] = $float_value32  -- OK: both are 32-bit
```

This also applies to constants and function parameters/return types:

```gbn
func sum(a: int[16], b: int[16]) -> int[16]
    return a + b
end
```

The element types of `array`/`dict` never track a specific bit width — `array[int]` accepts `int` values of mixed widths because a container has no per-element width annotation of its own. Writing `array[int[16]]` is rejected as ambiguous (it is unclear which elements it would apply to); use a plain `array[int]` instead.

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

The basic syntax is `var name: type = value`. The `$` prefix is used to read or modify the variable after declaring it.

```gbn
var hp: int = 100
$hp = 50
```

### Size in the Name (Shorthand)

You can specify the maximum size directly in the variable name instead of in the type annotation:

```gbn
var buffer[128]: str = "hola"
```

### Multiple Types

A variable can accept more than one type by separating them with commas. Use this feature sparingly:

```gbn
var dato: int,str = 10
$dato = "texto"
```

### Constants

Constants are declared with `const` and cannot be reassigned:

```gbn
const MAX_HP: int = 200
```

Attempting to modify a constant raises a type error (`Immutable constant`).

### `#onready`

The `#onready` modifier declares a variable before the program starts running, which is useful for early dependency initialization:

```gbn
#onready var config: str[64] = "default"
```

It also prevents the same value from being reassigned when used.

> `#onready` can also be placed before a function, where it caches its results instead — see [Cached Functions](#cached-functions-onready-func).

### `#reserved`

`#reserved` declares private script elements, meaning they cannot be used outside the script in which they were declared:

```gbn
#reserved var critico: bool = false
```

### `#public`

`#public` is the readability counterpart to `#reserved`. It changes nothing — variables, functions, and classes are already public by default — and exists only to make that intent explicit in the code:

```gbn
#public var vida: int = 100
```

### `#inmutable`

`#inmutable` behaves like `const` for direct assignment — `$name = value` raises the same error as a constant — but unlike a true `const`, its value **can** be changed indirectly through a [pointer](#15-pointers):

```gbn
#inmutable var x: int = 5
$x = 10              -- error: 'x' is #inmutable

var p: ptr = $$x
$p.value = 99         -- OK — x is now 99
```

A true `const` remains completely locked even through a pointer; `#inmutable` is the version that allows this one deliberate escape hatch.
Its value may also be changed only while its current value is `NULL`, allowing dependency values to be loaded into constants without triggering a constant-reassignment error. 

### `NULL` as an Empty Value

`NULL` represents the absence of a value. Objects and complex variables are declared as `NULL` when their contents have not yet been determined:

```gbn
var name: str[32] = NULL
var hp: int = NULL
```

> ! The interpreter ignores objects whose value is `NULL` until a value is assigned. For arrays and dictionaries, initialize with `[]` or `{}` instead of `NULL` if you plan to add elements immediately.

---

## 5. Comments

### Line Comment

Starts with `--` and continues to the end of the line:

```gbn
var x: int = 5 -- this is a comment
```

### Block Comment

Starts with `!*` and ends with `!*`. It can span multiple lines:

```gbn
!* This is a comment
   spanning multiple lines !*
```

> Block comments cannot be nested: the second `!*` closes the block opened by the first.

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
|----------|-------------|
| `==` | equal |
| `!=` | Not equal |
| `<` | Less than |
| `<=` | Less than or equal to |
| `>` | Greater than |
| `>=` | Greater than or equal to |

### Logical Operators

| Operator | Meaning |
|----------|-------------|
| `and` | Logical AND |
| `or` | Logical OR |
| `not` | Negation |
| `is`| Data comparison |

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

The return type is required. Use `NULL` if the function does not return anything:

```gbn
func greet(name: str[32]) -> NULL
    $print("Hello " + $name)
end
```

### Function with a Return Value

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

> ! The same width-matching rule applies to arguments: callers passing a variable declared with a different explicit width than the parameter must convert it explicitly first.

### Cached Functions (`#onready func`)

Placing `#onready` before a function caches its results: the first call with a given set of arguments executes the body, and later calls with exactly the same arguments return the cached result without executing it again.

```gbn
#onready func square(n: int) -> int
    $print("calculating...")
    return $n * $n
end

$print($square(4))   -- calculating... / 16
$print($square(4))   -- 16 (from cache)
$print($square(5))   -- calculating... / 25
```

- Each distinct argument set has its own cached result.
- For a class method, each instance has its own cache.
- A cached call does not repeat the function’s side effects (printing, writing files, etc.), so this is best suited to functions that return the same result for the same arguments.
- Run with `--nch` to disable caching entirely for that run.

### Rest Parameters (`!`)

A parameter whose name begins with `!` collects the arguments it receives into an array:

```gbn
func sumar(!valores[10]: int) -> int
    var total: int = 0
    for n in $valores
        $total += $n
    end
    return $total
end

$print($sumar(1, 2, 3, 4))   -- 10
$print($sumar())             -- 0
```

- `[10]` (optional) defines how many values it can contain, and `: int` (optional) defines each value’s type — the same rules as `array[int][10]`.
- A function can have only one `!` parameter, and it must be the last one. Earlier parameters receive their arguments first, and the `!` parameter collects the rest:

```gbn
func reporte(titulo: str, !lineas: str) -> NULL
    $print($titulo)
    for linea in $lineas
        $print(" - " + $linea)
    end
end

$reporte("Log", "started", "loaded", "listo")
```

### Named Parameters (`?`)

A parameter marked with `?` is supplied by name when calling the function, written as `$name=value`:

```gbn
func set_modulate(?r: float, ?g: float, ?b: float, a: float) -> color
    return $color($r, $g, $b, $a)
end

var c: color = $set_modulate(1.0, $r=0.6, $g=0.3, $b=0.9)
```

- The `$` before the name is required.
- Only parameters marked with `?` can be passed by name; using a name that does not match any parameter is an error.
- A `?` parameter that is not supplied remains `NULL`.
- Class constructors work the same way: if `init` declares `?hp: int`, then `$Player($hp=50)` supplies it.

### Named Rest Parameters (`?!`)

Combining both markers creates a named parameter that collects an array. Unlike a plain `!`, a function can declare multiple `?!` parameters, since each is supplied by name with its own array:

```gbn
func grupos(?!a: int, ?!b: int) -> NULL
    $print($a)   -- [1, 2, 3]
    $print($b)   -- [4, 5]
end

$grupos($a=[1, 2, 3], $b=[4, 5])
```

A plain `!` parameter cannot be combined with `?!` parameters in the same function.

### Main Function (`init`) and `run`

The `run` keyword executes the `init()` function defined in the global scope. This is the standard way to structure a program’s entry point:

```gbn
func init() -> NULL
    $print("Program started")
end

run
```

> The `init()` function inside a class is that class’s constructor. It does not conflict with the global `init()` because they are used in different contexts.

---

## 8. Classes

### Declaration

```gbn
class NombreClase
    var field: tipo = NULL

    func init(self, param: tipo) -> NULL
        $self.field = $param
    end

end
```

`self` refers to the current instance and is automatically passed as the first argument when a method is called. You do not need to pass it when instantiating:

```gbn
var p: any = $Player("Juan")
$print($p.name)
$print($p.hp)
```

### Methods

Methods are defined inside a class just like functions, with `self` as the first parameter:

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

Access fields with a dot (`.`), without `$`:

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

Values are assigned automatically starting at `0`. Access them using `EnumName.MEMBER`.

### `.null`, Iteration, and `in`

Every enum has an implicit `.null` member — a sentinel meaning “nothing from this enumeration has been stored yet.” It is separate from the enum’s own members and is never counted as one of them:

```gbn
enum Direction = {UP, DOWN, LEFT, RIGHT}

var current: Direction = Direction.null
$print($current)  -- distinct from the value of any declared member
```

An enum can be iterated directly with `for ... in` and supports the membership operator `in` — both traverse only declared members, never `.null`:

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

var espada: Item = $Item("Sword", $ItemType.WEAPON)
```

---

## 11. Arrays

### Declaration

```gbn
var numbers: array[int] = []
```

Use `[]` to initialize an empty array. Using `NULL` and then trying to add elements without first assigning an array will cause an error.

### Array Methods

| Method | Description |
|--------|-------------|
| `.append(value)` | Adds an element to the end |
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

### Arrays with a Maximum Size

```gbn
var list: array[int][10] = []
```

This limits the array to a maximum of 10 elements.

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

## 13. Control Flow

### `if / elseif / else` Conditional

```gbn
if $x > 10
    $print("greater")
elseif $x == 10
    $print("equal")
else
    $print("less than")
end
```

`elif` is also accepted as a shorter form of `elseif`.

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

Compares a subject against several possible values. Each case starts with `case value1, value2` (multiple comma-separated labels are allowed). Only the first matching case is executed (or `else`, if present); cases do not fall through.

```gbn
match $dia
    case 1
        $print("Monday")
    case 2, 3
        $print("Tuesday or Wednesday")
    else
        $print("Another day")
end
```

Case labels can be any evaluable expression: literals, variables, enum members (`Color.RED`), or even array/dictionary literals (`[1, 2, 3]`, `{"a": 1}`). If nothing matches and there is no `else`, nothing happens — no error is raised.

### Loop Control Keywords

| Keyword | Comportamiento |
|---------|----------------|
| `break` | Exits the current loop |
| `continue` | Skips to the next iteration |
| `loop` | Subtractionrts the current iteration from the beginning |
| `pass` | Does nothing (empty-block placeholder) |

`loop` is easy to confuse with `continue` because they may look similar in a simple `while` loop, but they are not the same: `continue` advances to the *next* iteration (the next item in a `for`, or checks the `while` condition again), whereas `loop` reruns the *same* iteration from the beginning, with its state exactly as it was — the same `for` item, without checking the `while` condition again — until it finishes normally.

```gbn
var intentos: int = 0
for item in [10, 20]
    $intentos += 1
    $print(f"testing {item}")
    if item == 10 and $intentos < 2
        loop  -- restarts with item still at 10, not 20
    end
end
-- prints: testing 10 / testing 10 / testing 20
```

### `await`

Pauses execution until a condition becomes true (polling every 10 ms):

```gbn
await $ready == true
```

---

## 14. Error Handling

```gbn
try
    -- code that may fail
catch
    -- code that runs if an error occurs
end
```

`except` is also accepted as an alias for `catch`:

```gbn
try
    var x: int = $int("no_es_numero")
except
    $print("A conversion error occurred")
end
```

Without a specified type, `catch`/`except` handles all errors. An empty `catch`/`except` body is valid: it silences the error and does nothing else.

### Catching Specific Error Types

Write one or more error types after `catch`/`except` to handle only those types. Each type is written as a pointer (`$$Type`), and multiple types are comma-separated. Any other error continues to propagate normally:

```gbn
try
    var y: any = $no_declarada
except $$NameError
    $print("undeclared variable")
end

try
    -- code that may fail
except $$SyntaxError, $$ValueError
    $print("syntax or value problem")
end
```

Catching a general type also catches the more specific types it groups: `$$LookupError`, for example, handles both `IndexError` and `KeyError`.

### Storing the Error (`-> name`)

Add `-> name` at the end of the header to store the error in a variable. It contains a string with the error type, where it occurred, and the message:

```gbn
try
    var y: any = $no_declarada
catch -> e
    $print($e)   -- NameError: game.gbn:3:3: Variable not declared: no_declarada
end
```

This can be combined with error types:

```gbn
except $$ValueError, $$TypeError -> e
```

### Error Types

Every error displays its type at the start of the message instead of a generic `Error:`:

```
NameError: game.gbn:12:3: Variable not declared: x
```

| Type | Se produce cuando |
|------|-------------------|
| `NameError` | A variable, function, or class has not been declared |
| `TypeError` | A value has the wrong type, or an operation is not valid for it |
| `ValueError` | A value is not acceptable |
| `SyntaxError` | The code is malformed (for example, a block without `end`) |
| `IndexError` | An array index is out of range |
| `KeyError` | A dictionary key does not exist |
| `LookupError` | Groups `IndexError` and `KeyError` |
| `GybinError` | Groups the three language-specific errors listed below |
| `EventError` | An [event](#16-events) is used incorrectly — for example, connecting something that is not a function reference. It is also handled by `$$TypeError` |
| `PointerError` | A [pointer](#15-pointers) is used incorrectly or does not match its `ptr[...]` annotation. It is also handled by `$$TypeError` |
| `BitWidthError` | A value does not fit in an `int[N]`/`float[N]`, or a coercion mixes different widths (see [§3](#3-data-types)). It is also handled by `$$ValueError` |

```gbn
try
    var small: int[8] = 500
except $$BitWidthError -> e
    $print($e)
end

try
    $player_is_dead.connect(5)
except $$GybinError -> e
    $print("event, pointer, or bit-width problem: " + $e)
end
```

---

## 15. Pointers

The `$$` operator creates a pointer to an existing variable, constant, function, class, or event (e.g. `$$hp`, `$$Damage`, `$$self.hp`, `$$arr[0]`, `$$player_is_dead`). It is typed with `ptr` — the only annotation that can hold a pointer value:

```gbn
var hp: int = 100
var ref: ptr = $$hp
```

> ! Reading a pointer variable directly (`$print(ref)`) prints the pointer itself, not the value it points to — use `.value` or `.get()` to read through it.

### Pointer Methods and Properties

A pointer never stores a copy of its target — it resolves the target again each time one of these members is used:

| Member | Description |
|---------|-------------|
| `.value` | Gets the current value of the referenced variable/constant. It can also be assigned (`$ref.value = 75`) to write through the pointer |
| `.get()` | Same as `.value`, as a method call |
| `.set(value)` | Same as assigning `.value`, as a method call |
| `.call(args...)` | Invokes the referenced function/class, forwarding the supplied arguments |
| `.name` | The name of the referenced memory slot |
| `.is_callable` | `true` if the pointer refers to a function or class, `false` for a variable/constant |
| `.is_mutable` | `true` only for a variable that is neither `#reserved` nor a constant |
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

- Only variables can be changed through a pointer. Constants are always immutable, and functions/classes cannot be assigned a value — `.set()`/`.value = ...` raises an error in either case.
- A variable declared with `#reserved` can never be mutated through a pointer, even by code that has a reference to it.
- Writing through a pointer (`.set()`/`.value = ...`) accepts any value type; a mismatch with the target’s declared type produces a warning (with `--w`) rather than a strict type error.
- Referencing a function or class by its bare name (without `$$`) is a script error — `$$name` is the only way to obtain a reference without invoking it.

Pointers allow indirect access and can target complex paths (`$$object.field`, `$$array[0]`). They are useful for aliases, dynamic references, and passing references to functions (for example, when connecting handlers to an [event](#16-events)).

### Typed Pointers: `ptr[target][data]`

A plain `ptr` accepts a pointer to anything. Two optional bracket groups can constrain it:

- **First bracket — what it can point to:** `var`, `const`, `event`, `func`, `class` (separate multiple options with commas).
- **Second bracket — the data type it must contain:** `int`, `str`, a class name, etc. (separate multiple options with commas).

An empty bracket pair, or one containing `any`, means that part is unrestricted.

```gbn
var p1: ptr[func] = $$greet                -- functions only
var p2: ptr[var,const][int,float] = $$hp      -- a variable or constant containing an int or float
var p3: ptr[var][Fighter] = $$hero           -- a variable containing a Fighter instance
var p4: ptr[event] = $$player_is_dead         -- events only
var p5: ptr[] = $$hp                           -- same as a plain ptr
var p6: ptr[any][any] = $$hp                   -- same as a plain ptr
```

For classes, the second bracket pair indicates which class or classes are accepted: the named class or any class that extends it.

```gbn
class Fighter
    var hp: int = 10
end

class Warrior extends Fighter
    var armor: int = 5
end

class Enemy
    var atk: int = 5
end

var a: ptr[class][Fighter] = $$Warrior          -- OK: Warrior extends Fighter
var b: ptr[class][Fighter,Enemy] = $$Enemy      -- OK
var c: ptr[class][Fighter] = $$Enemy            -- PointerError
```

A pointer that does not match its annotation raises a `PointerError` (see [§14](#14-error-handling)).

### Pointers to Raw Addresses

A `ptr` can also be constructed from a raw integer address instead of `$$target`:

```gbn
var memory: ptr = 0x7fff5fbff80c
```

> ! This does **not** dereference actual process memory — doing so safely from an interpreter that walks a syntax tree is not possible (there is no way to know whether a given address is valid, and attempting it could crash the process or read memory that does not belong to you). Instead, you get an opaque handle that carries the address purely as an identity:

```gbn
$print($memory.ref)          -- the address itself
$print($memory.name)         -- "0x7fff5fbff80c"
$print($memory.is_callable)  -- false
$print($memory.is_mutable)   -- false
$print($memory.size)         -- native pointer size (8 bytes)

$print($memory.value)        -- error: nothing to dereference
$memory.value = 5             -- error: nowhere to write to
$memory.call()                -- error: nothing to call
```

Same object, same member interface as a normal pointer — `.value`, `.set()`, and `.call()` simply have nothing to act on, and report that clearly instead of guessing.

---

## 16. Events

An `event` declares a lightweight signal: a name plus a list of parameters:

```gbn
event player_is_dead(entity: str)
```

Type annotations on parameters are documentation only — an event has no body against which to validate them.

### Methods

Every event exposes the following members, all used with the `$` prefix like any other call:

| Member | Description |
|---------|-------------|
| `.connect(handler)` | Registers a function to run every time the event is emitted. `handler` must be a pointer to a function created with `$$function_name`; a bare name or a pointer to anything else (a variable, class, event, etc.) raises an `EventError` |
| `.disconnect(handler)` | Removes that handler from the event. Does nothing if it was not connected |
| `.reconnect(handler)` | Disconnects and reconnects the handler so it is connected exactly once — useful for preventing it from running twice on each `.emit()` |
| `.emit(args...)` | Calls each connected handler in connection order, forwarding the supplied arguments. The number of arguments must match the number of parameters declared by the event |
| `.last_connection` | Property (no parentheses): a pointer to the most recently connected handler, or `NULL` if none are connected |

```gbn
event player_is_dead(entity: str)

func on_player_dead(entity: str) -> NULL
    $print(entity + " died")
end

$player_is_dead.connect($$on_player_dead)

if $vida <= 0
    $player_is_dead.emit("Zombie")
end
```

Multiple handlers can be connected to the same event; all are executed, in connection order, when `.emit(...)` is called.

`.disconnect(...)` accepts any pointer to the same function, so you do not need to save the one used to connect it:

```gbn
$player_is_dead.disconnect($$on_player_dead)
```

```gbn
$player_is_dead.connect($$on_player_dead)
$player_is_dead.connect($$on_player_dead)     -- conectado dos veces: se ejecuta dos veces por emit
$player_is_dead.reconnect($$on_player_dead)   -- ahora está conectado exactamente una vez

$print($player_is_dead.last_connection.name)  -- on_player_dead
```

### Events as Conditions

An event can be used directly as a condition: it is `false` until it is emitted for the first time, and `true` thereafter.

```gbn
event level_loaded(name: str)

func init() -> NULL
    if $level_loaded
        $print("not printed yet")
    end

    $level_loaded.emit("Forest")

    if $level_loaded
        $print("printed: the event has already been emitted")
    end
end
```

---

## 17. Modules and Imports

### `@use` — Importing a Module

Loads a `.gbn` file (or another supported format) and exposes all its symbols in the current scope:

```gbn
@use "utils.gbn"
@use "helpers"        -- detects the extension automatically
```

Importing is idempotent: if a module has already been loaded, it is not executed again.

### Importing Multiple Modules at Once

```gbn
@use math, random, sys
```

Each module is loaded independently, exactly as if it had its own `@use` line. `@as` is not allowed in an `@use` statement containing multiple modules — one alias cannot represent several different modules — import them one per line if each needs its own name:

```gbn
@use math @as mate
@use random @as rand
```

### `@from` / `@as` — Importing with an Alias

Loads a module and exposes it as a named namespace:

```gbn
@from "utils.gbn" @as utils
$print($utils.mi_funcion())
```

`@use path @as alias` (a single module) does exactly the same thing — the same functionality is available through either keyword.

### Selective Imports (`@from ... @use`)

Loading an entire module just to use one or two functions wastes memory on everything else it defines and can fill `--w` output with warnings about symbols the importer never requested. `@from module @use $$symbol` loads only the named symbols instead of executing the whole module and importing everything it exposes:

```gbn
@from math @use $$_sqrt
$print($_sqrt(4.0))
```

Multiple symbols from the same module, separated by commas:

```gbn
@from math @use $$_PI, $$_E, $$_sqrt
```

Add `@as` to group the selected symbols under a single namespace instead of placing them directly in the current scope — this is allowed here (unlike the multiple-module `@use` case above) because everything still comes from a single module:

```gbn
@from sys @use $$_format_time, $$_miliseconds @as os
$print($os._format_time())
```

`#reserved` symbols still cannot be imported this way, selectively or otherwise.

### Supported Formats

| Extension | Behavior |
|-----------|----------------|
| `.gbn` | Executed and integrated into the current scope |
| `.py` | Loaded as a Python module; its public attributes are exposed |
| `.c`, `.cpp`, `.asm`, `.sh`, `.bash`, `.h` | Source code is exposed as a dictionary under `__source__` |

### Automatic Module Search

If the path contains no `/` and does not start with `.`, the interpreter also searches the project’s `libs/` folder.

---

## 18. Memory Management

The interpreter has a configurable default limit of **1024 memory slots**.

### `free` — Freeing a Memory Slot

Explicitly removes a variable from the scope:

```gbn
$free($$mi_dato) 
```

`free` accepts one or more pointers of any type (variables, constants, functions, classes, events), separated by commas:

```gbn
$free($$primero, $$segundo, $$tercero)
```

### `expand_memory` — Increasing the Limit

Increases the maximum number of available slots:

```gbn
$expand_memory(512)
```

> ! This emits a warning to `stderr` indicating the change.

### `breakpoint` — Pausing Execution

Pauses execution and returns a memory summary:

```gbn
$breakpoint()
```

### Expression Cache

Expressions that appear repeatedly (for example, inside a loop) are cached as an AST the first time they are parsed, avoiding unnecessary reparsing on each cycle:

```gbn
var i: int = 0
while $i < 10000
    var x = ($i * 5) + (20 / 2)  -- the expression is cached
    $i += 1
end
```

### Cache and `--nch`

Two features cache results to save work on repeated use:

- **`#onready func`** caches a function result for each distinct set of arguments (see [§7](#7-functions)).
- **`$preload(path)`** reads a file once and caches its contents (see [§19](#19-built-in-functions)).

Run with `--nch` to disable both for that run: cached functions always execute their bodies, and `$preload` always reads from disk.

```bash
Gybin mi_script.gbn --nch
```

### Post-Execution Garbage Collector

When execution ends, the engine automatically frees global symbols that were defined but never read (global variables, functions, classes, imported namespaces). `$free($var)` can also be used when needed.

### `--sm` — Memory Summary

When the `--sm` flag is used, the interpreter prints the full memory state at the end:

```
Total memory: hp:int=100 | name:str='Juan' | ...
```

---

## 19. Built-in Functions

These functions are available without importing anything:

| Function | Description |
|---------|-------------|
| `$print(value)` | Prints a value |
| `$reprint(value)` | Like `$print`, but overwrites the current line instead of starting a new one — see below |
| `$int(value)` | Converts to an integer |
| `$float(value)` | Converts to a float |
| `$str(value)` | Converts to a string |
| `$bool(value)` | Converts to a boolean |
| `$range(n)` | Generates a range from 0 to n-1 |
| `$len(coleccion)` | Returns the length of a collection |
| `$file_read(path)` | Reads an entire file as a string |
| `$file_lines(path)` | Reads a file as an array of lines |
| `$file_write(path, content)` | Writes (overwrites) a file |
| `$file_append(path, content)` | Appends content to a file |
| `$file_exists(path)` | Returns `true` if the file exists |
| `$preload(path)` | Reads a file like `$file_read`, but caches its contents — see below |
| `$eval()` | Executes expressions provided as strings |
| `$exit()` | Immediately terminates the program |

### Named Arguments for `$print`

`$print` accepts `sep`, `end`, and `flush` as named arguments:

```gbn
$print("a", "b", sep="-", end="")   -- a-b, no trailing newline
$print("c")
```

### `$preload` — Reading a File Once

`$preload(path)` returns the full contents of a file as a string, just like `$file_read(path)`. The difference is that it caches the result for that path: later calls with the same path return the cached contents immediately without accessing the disk again, even if the file has changed in the meantime.

```gbn
var config: str = $preload("config.txt")   -- reads the file
var again: str = $preload("config.txt") -- returns the cached contents
```

Run with `--nch` to make each `$preload` read from disk.

### `$reprint` — Updating a Line in Place

Status/progress output often needs to overwrite the same terminal line instead of moving to a new line on every call. `$reprint` does this without having to manually write `\r` and an ANSI clearing sequence:

```gbn
$reprint("cargando 10%")
$reprint("cargando 100%")
$reprint("ready!", end="\n")   -- pass end="\n" to close the line and return to normal $print behavior
$print("afterward")
```

By default, it does not add a newline (so the next call continues overwriting the same line) and flushes immediately. With `end="\n"`, it behaves exactly like `$print`, so it is safe to use generally.

---

## 20. Standard Library (`stdutils`)

`stdutils.gbn` is loaded automatically at the start of every program. It provides:

### Version Constant

```gbn
$print($GBN.VERSION) 
```

### Collection Functions

| Function | Description |
|---------|-------------|
| `$contains(collection, element)` | `true` if the element is in the collection |
| `$index_of(collection, element)` | Index of the element, or `-1` if it does not exist |
| `$has_key(dict, key)` | `true` if the key exists in the dictionary |
| `$merge_dict(dest, origen)` | Merges `origen` into `dest` and returns the result |
| `$flatten(colecciones)` | Merges one or more collections into a single collection |
| `$unique(coleccion)` | Removes duplicate elements |
| `$reverse(coleccion)` | Returns the elements of a collection in reverse order |

### String Functions

| Function | Description |
|---------|-------------|
| `$str_split(text, delimiter)` | Splits a string into an array |
| `$str_join(separator, items)` | Joins an array of strings into one |
| `$to_lower(texto)` | Converts to lowercase |
| `$to_upper(texto)` | Converts to uppercase |
| `$starts_with(texto, prefijo)` | `true` if the text starts with the prefix |
| `$ends_with(texto, sufijo)` | `true` if the text ends with the suffix |
| `$repeat(texto, rango)` | Repeats a string `n` times |
| `$trim(texto)` | Trims whitespace from a string |
| `$replace(texto, viejo, nuevo)` | Replaces occurrences in a string with another string |

### Vector Types

| Function | Description |
|---------|-------------|
| `$vec2(x, y)` | 2D vector of floating-point values |
| `$vec2i(x, y)` | 2D vector of integer values |
| `$vec3(x, y, z)` | 3D vector of floating-point values |
| `$vec3i(x, y, z)` | 3D vector of integer values |
| `$color(r, g, b, a)` | 4D vector of floating-point values, ranging from 0 to 1; `a` defaults to 1 if no value is assigned |

> You can access vector values at any time through `.x, .y, .z` or `.r, .g, .b, .a`
> All vectors provide the `.zero()` function

The `$color()` vector accepts an optional named `$preset=` argument to select a named color from an enum instead of providing arguments for every RGBA channel

| Color | Equivalencia |
|-------|--------------|
| `$Color.YELLOW` | `$color(1.0, 1.0, 0.0, 1.0)` |
| `$Color.BLUE` | `$color(0.0, 0.0, 1.0, 1.0)` |
| `$Color.RED` | `$color(1.0, 0.0, 0.0, 1.0)` |
| `$Color.GREEN` | `$color(0.0, 1.0, 0.0, 1.0)` |
| `$Color.VIOLET` | `$color(0.93333334, 0.50980395, 0.93333334, 1.0)` |
| `$Color.PURPLE` | `$color(0.627451, 0.1254902, 0.9411765, 1.0)` |
| `$Color.MAGENTA` | `$color(1.0, 0.0, 1.0, 1.0)` |
| `$Color.PINk` | `$color(1.0, 0.7529412, 0.79607844, 1.0)` |
| `$Color.SKYBLUE` | `$color(0.5294118, 0.80784315, 0.92156863, 1.0)` |
| `$Color.BLACK` | `$color(0.0, 0.0, 0.0, 1.0)` |
| `$Color.WHITE` | `$color(1.0, 1.0, 1.0, 1.0)` |
| `$Color.GRAY` | `$color(0.74509805, 0.74509805, 0.74509805, 1.0)` |
| `$Color.ORANGE` | `$color(1.0, 0.64705884, 0.0, 1.0)` |
| `$Color.LIME` | `$color(0.0, 1.0, 0.0, 1.0)` |

### Data

| Function | Description |
|---------|-------------|
| `$is_array(value)` | `true` if it is a collection |
| `$is_dict(value)` | `true` if it is a dictionary |
| `$is_ptr(value)` | `true` if it is a pointer |
| `$type(value)` | Returns the class of the argument’s data type |
| `$type_of(value)` | Like `$type`, but returns an enum value to make comparisons easier |

The `Type` enum contains data types used by `$type_of` for comparisons:

| Type | Equivalent value |
|------|--------------|
| `$Type.STRING` | 0 |
| `$Type.INT` | 1 |
| `$Type.FLOAT` | 2 |
| `$Type.BOOL` | 3 |
| `$Type.POINTER` | 4 |
| `$Type.OBJECT` | 5 |
| `$Type.null` | -1 (the default for any enum) |

### Clamping Values

The first argument of `$max()` or `$min()` is the value to clamp, and the second is the limit. If the value exceeds the limit, the limit is returned automatically

```gbn
var min_value: int = $min(25, 12) -- The minimum possible value is 12
var max_value: int = $max(72, 100) -- The maximum possible value is 100
```

### User Input

```gbn
var name: str[64] = $input("What is your name? ")
```

### Input Pause

```gbn
$pause() -- Execution pauses here
```

---

## 21. Compiling to an Executable

`--c`/`--fc` generate a standalone executable with PyInstaller. **Neither flag runs your script for you to see its output** — the only output is the resulting executable’s path or a message explaining why compilation was skipped.

```bash
Gybin mi_script.gbn --c
```

The interpreter has no separate “syntax-check only” mode — it directly walks the syntax tree, so “checking for errors” and “running the script” are technically the same operation. `--c` still needs to know whether the script fails, so it runs it internally once with all output (stdout/stderr) completely silenced — nothing it prints or does is shown, and its effects do not leak into anything printed afterward. `--fc` skips even that: it never touches the script and compiles unconditionally.

| Flag | Does it run the script? | Does it compile if there is an error? |
|------|----------------------|--------------------------|
| `--c` | Completely silenced (error checking only) | No — prints `Compilation skipped...` and exits |
| `--fc` | Never | Yes, always |

### `--n`, `--ad`, `--i`

```bash
Gybin juego.gbn --c --n MiJuego --ad assets/config.json --i icono.ico
```

- `--n NAME` — custom name for the compiled executable (default: the script’s filename without its extension).
- `--ad PATH[=DESTINATION]` — bundles an extra file or folder into the executable. Can be repeated. `DESTINO` is the destination folder inside the bundle (default: `.`).
- `--i ICON_PATH` — icon for the executable (`.ico` on Windows, `.icns` on macOS).

### Automatic Import Bundling

Every file brought in with `@use` or `@from ... @as` — at any depth (including transitive imports) and with any supported extension — is detected automatically and embedded in the executable. The compiled program is fully self-contained: it does not need the original `.gbn` files to run.

`stdutils.gbn` is also embedded in the executable and is never copied alongside it as an external file. This is intentional: since it loads automatically on every run, an editable external copy would pose a code-injection risk for a compiled binary.

If PyInstaller is unavailable, a Bash wrapper (`.bat` on Windows) is generated to invoke the interpreter directly:

```bash
#!/usr/bin/env bash
exec Gybin "mi_script.gbn" "$@"
```

> ! A script whose own filename contains `:` can still be compiled as the entry point. However, a file *imported* by that script whose filename contains `:` cannot be bundled — PyInstaller’s `--add-data` uses `:` as the SOURCE/DEST separator. You will receive a clear warning during compilation, and only that file will be skipped instead of failing the entire build.

---

## 22. Warnings and Static Analysis

When run with `--w`, the engine performs post-execution analysis and reports:

- **Variables declared but never read**
- **Functions defined but never called**
- **Functions with an empty body**
- **Classes defined but never instantiated**
- **Classes with an empty body**
- **Enums defined but never used**
- **Multi-type variables used with more than 3 distinct types**
- **Suspicious assignments** (declared type differs from the value’s actual type)
- **Possible memory leaks**: global containers with more than 256 elements that are never read

Warnings are printed to `stderr` in the following format:

```
Warning: file.gbn:42: Variable 'x' is declared but never read
```

> Variables whose names start with `_` are ignored by the analyzer (the convention for “intentionally unused”).

> You may receive warnings about code you never wrote; these may refer to unused code in imported libraries. 

---

## 23. Rules and Best Practices

### The `$` Operator

`$` is **required** to:
- Read a variable’s value: `$hp`
- Call a function: `$print(...)`, `$add(1, 2)`
- Instantiate a class: `$Player("Juan")`
- Assign to an existing variable: `$hp = 50`
- Chain access: `$p.damage(30)`

`$` is **not** used for:
- The initial declaration (`var hp: int = 100`)
- Accessing object fields after the dot (`$p.hp`, no `$p.$hp`)
- Parameter names in function signatures

### Scope

Variables declared inside a block (function, loop, conditional) are local to that block. Redefining an outer variable inside an inner scope can cause conflicts:

```gbn
var global: int = 100

func test() -> NULL
    var global: int = 50  -- local redefinition
    $print($global)       -- error: scope ambiguity
end
```

Use different names for local variables that coexist with global variables of the same name.

### Using `any`

`any` disables type checking. Use it only when strictly necessary, such as for variables that store values whose types are unknown at declaration time.

### Initializing Collections

Always initialize arrays and dictionaries with `[]` or `{}` if you plan to operate on them immediately. Using `NULL` as the initial value and then trying to add elements before assigning a real collection will cause an error.

```gbn
-- Correct:
var items: array[Item] = []
$items.append($Item("Sword"))

-- Problematic if append is used before assigning a collection:
var items: array[Item] = NULL
$items.append($Item("Sword"))  -- error
```

### Closing Blocks with `end`

Every block (`func`, `class`, `if`, `while`, `for`, `try`, `match`) must be closed with `end`. An unclosed block raises a `SyntaxError`.

> ! Although code can be written outside functions, it is recommended that most of the script be organized into functions.

### Indentation

> ! Indentation is not required by the language. It is still recommended for readability and organization; however, removing it may improve performance in large projects.
