# GybinScript — Manual de Uso

> **Versión:** 1.4.0  
> **Extensión de archivos:** `.gbn`  
> **Intérprete:** `Core/Gybin` \ `/usr/bin/Gybin`
> **Ejecución:** `Gybin (Dirección de archivo: Mi_script.gbn)`

> ! Tambien puedes declarar el interprete en la primera linea de tu código y ejecutarlo como cualquier programa. (Solo en linux) Ej: 

```gbn
#!/usr/bin/Gybin -- Dirección del parser

$print("Hola!") 
```

```bash
chmod +x Mi_script.gbn
./Mi_script.gbn
```

> Ejecute setup-linux para configurar el lanzador de Gybin en '/usr/bin'

---

## Índice

1. [Introducción](#1-introducción)
2. [Ejecución desde consola](#2-ejecución-desde-consola)
3. [Tipos de datos](#3-tipos-de-datos)
4. [Variables y constantes](#4-variables-y-constantes)
5. [Comentarios](#5-comentarios)
6. [Operadores](#6-operadores)
7. [Funciones](#7-funciones)
8. [Clases](#8-clases)
9. [Herencia](#9-herencia)
10. [Enums](#10-enums)
11. [Arrays](#11-arrays)
12. [Diccionarios](#12-diccionarios)
13. [Estructuras de control](#13-estructuras-de-control)
14. [Manejo de errores](#14-manejo-de-errores)
15. [Punteros](#15-punteros)
16. [Módulos e importaciones](#16-módulos-e-importaciones)
17. [Gestión de memoria](#17-gestión-de-memoria)
18. [Funciones nativas (built-ins)](#18-funciones-nativas-built-ins)
19. [Biblioteca estándar (stdutils)](#19-biblioteca-estándar-stdutils)
20. [Compilación a ejecutable](#20-compilación-a-ejecutable)
21. [Advertencias y análisis estático](#21-advertencias-y-análisis-estático)
22. [Reglas y buenas prácticas](#22-reglas-y-buenas-prácticas)

---

## 1. Introducción

GybinScript es un lenguaje de scripting de tipado estático e interpretado, con gestión de memoria controlada. Está diseñado para ser expresivo y predecible: todas las variables deben declararse con tipo, los bloques se cierran con `end`, y el signo `$` es el prefijo obligatorio para leer o modificar cualquier variable o llamar a cualquier función.

---

## 2. Ejecución desde consola

```bash
Gybin mi_script.gbn [opciones]
```

### Opciones disponibles

| Flag | Descripción |
|------|-------------|
| `--sm` | Muestra el estado de memoria al finalizar la ejecución |
| `--pr` | Imprime automáticamente todos los valores devueltos por `return` |
| `--t` | Muestra el tiempo de ejecución |
| `--tr` | Muestra cada línea ejecutada en lugar de la salida normal |
| `--c` | Compila el script a un ejecutable si no hay errores |
| `--fc` | Compila el script aunque haya errores |
| `--w` | Activa los mensajes de advertencia (análisis estático) |
| `--nc` | Suprime toda salida estándar (los errores siguen mostrándose) |

### Ejemplo

```bash
Gybin juego.gbn --sm --w --t
```

---

## 3. Tipos de datos

GybinScript tiene seis tipos primitivos y dos tipos de colección:

| Tipo | Descripción | Ejemplo |
|------|-------------|---------|
| `int` | Entero | `20` |
| `float` | Decimal | `3.1416` |
| `str[N]` | Cadena con tamaño máximo N | `"Carlos"` |
| `bool` | Booleano | `true` / `false` |
| `any` | Sin restricción de tipo | — |
| `NULL` | Valor nulo / ausencia de valor | `NULL` |
| `array[T,...]` | Lista tipada de elementos | `[1, 2, 3]` |
| `dict[V,...]` | Diccionario tipado de valores | `{"a": 1}` |

**Coerciones automáticas:**
- Un `int` asignado a un `float` se convierte automáticamente a `float`.
- Un `float` sin parte decimal asignado a un `int` se convierte a `int`.
- Un `float` con decimales asignado a un `int` produce un error de tipo.

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

## 4. Variables y constantes

### Declaración de variables

La sintaxis básica es `var nombre: tipo = valor`. El signo `$` se usa para leer o modificar la variable después de declararla.

```gbn
var hp: int = 100
$hp = 50
```

### Tamaño en el nombre (shorthand)

Puedes especificar el tamaño máximo directamente en el nombre de la variable en lugar de en la anotación:

```gbn
var buffer[128]: str = "hola"
```

### Tipos múltiples

Una variable puede aceptar más de un tipo separando con comas. Se recomienda usarlos con moderación:

```gbn
var dato: int,str = 10
$dato = "texto"
```

### Constantes

Las constantes se declaran con `const` y no pueden ser reasignadas:

```gbn
const MAX_HP: int = 200
```

Intentar modificar una constante produce un error de tipo (`Immutable constant`).

### `#onready`

El modificador `#onready` declara una variable antes de que el programa comience a ejecutarse, útil para inicialización anticipada de dependencias:

```gbn
#onready var config: str[64] = "default"
```

### `NULL` como valor vacío

`NULL` representa la ausencia de valor. Los objetos y variables complejas se declaran con `NULL` cuando aún no tienen contenido definitivo:

```gbn
var name: str[32] = NULL
var hp: int = NULL
```

> ! El intérprete ignora objetos con valor `NULL` hasta que se les asigna uno. En arrays y dicts, es mejor inicializar con `[]` o `{}` en lugar de `NULL` si planeas agregar elementos de inmediato.

---

## 5. Comentarios

### Comentario de línea

Comienza con `--` y se extiende hasta el final de la línea:

```gbn
var x: int = 5 -- esto es un comentario
```

### Comentario de bloque

Se delimita con `!*` al inicio y `!*` al cierre. Puede abarcar múltiples líneas:

```gbn
!* Este es un comentario
   de varias líneas !*
```

> Los comentarios de bloque no anidados: el segundo `!*` cierra el bloque abierto por el primero.

---

## 6. Operadores

### Aritméticos

| Operador | Operación |
|----------|-----------|
| `+` | Suma |
| `-` | Resta |
| `*` | Multiplicación |
| `/` | División |
| `%` | Módulo |
| `**` | Potencia |

### Comparación

| Operador | Significado |
|----------|-------------|
| `==` | Igual |
| `!=` | Distinto |
| `<` | Menor que |
| `<=` | Menor o igual |
| `>` | Mayor que |
| `>=` | Mayor o igual |
| `is` | Igual por valor (equivalente a `==`) |

### Lógicos

| Operador | Significado |
|----------|-------------|
| `and` | Y lógico |
| `or` | O lógico |
| `not` | Negación |

### Asignación compuesta

```gbn
$x += 5
$x -= 2
$x *= 3
$x /= 4
```

---

## 7. Funciones

### Declaración

```gbn
func nombre(param1: tipo, param2: tipo) -> tipo_retorno
    -- cuerpo
end
```

El tipo de retorno es obligatorio. Usa `NULL` si la función no retorna nada:

```gbn
func saludar(nombre: str[32]) -> NULL
    $print("Hola " + $nombre)
end
```

### Función con retorno

```gbn
func add(a: int, b: int) -> int
    return $a + $b
end

var result: int = $add(10, 20)
$print($result)
```

### Llamada a funciones

Todas las llamadas deben ir precedidas de `$`:

```gbn
$saludar("Carlos")
$print($multiply($result, 2))
```

### Función principal (`init`) y `run`

La palabra clave `run` ejecuta la función `init()` definida en el ámbito global. Esta es la forma estándar de estructurar el punto de entrada de un programa:

```gbn
func init() -> NULL
    $print("Inicio del programa")
end

run
```

> La función `init()` dentro de una clase es el constructor de esa clase, y no choca con la `init()` global porque se usan en contextos distintos.

---

## 8. Clases

### Declaración

```gbn
class NombreClase
    var campo: tipo = NULL

    func init(self, param: tipo) -> NULL
        $self.campo = $param
    end

end
```

`self` hace referencia a la instancia actual y se pasa automáticamente como primer argumento cuando se llama a un método. No necesitas pasarlo al instanciar:

```gbn
var p: any = $Player("Juan")
$print($p.name)
$print($p.hp)
```

### Métodos

Los métodos se definen dentro de la clase igual que funciones, recibiendo `self` como primer parámetro:

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

### Acceso a campos

Se accede con punto (`.`) sin `$`:

```gbn
$print($p.name)
$p.hp = 50
```

---

## 9. Herencia

Una clase puede extender otra con `extends`:

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

>  **Importante:** Si la clase padre ya tiene un método `init()`, la clase hija debe usar `__init__()` en su lugar para evitar conflicto de nombres. La clase hija hereda todos los campos y métodos de la clase padre.

---

## 10. Enums

Los enums agrupan constantes con nombre bajo un tipo común:

```gbn
enum Direction = {UP, DOWN, LEFT, RIGHT}

var dir: int = Direction.UP
$print($dir)  -- 0
```

Los valores se asignan automáticamente a partir de `0`. Se accede a ellos con `NombreEnum.MIEMBRO`.

### Enums en clases

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

var espada: any = $Item("Sword", $ItemType.WEAPON)
```

---

## 11. Arrays

### Declaración

```gbn
var numbers: array[int] = []
```

Usa `[]` para inicializar un array vacío. Usar `NULL` sin asignar elementos inmediatamente causará un error al intentar añadir.

### Métodos de array

| Método | Descripción |
|--------|-------------|
| `.append(valor)` | Añade un elemento al final |
| `.remove(indice)` | Elimina el elemento en la posición dada |
| `.size()` | Retorna el número de elementos |
| `.duplicate()` | Retorna una copia del array |
| `.push_back(valor)` | Alias de `append` |

```gbn
$numbers.append(10)
$numbers.append(20)
$numbers.append(30)

$print($numbers)       -- [10, 20, 30]

$numbers[1] = 50
$print($numbers)       -- [10, 50, 30]
```

### Arrays con tamaño máximo

```gbn
var lista: array[int][10] = []
```

Esto limita el array a un máximo de 10 elementos.

### Arrays de objetos

Se recomienda usar `any` para arrays que contienen instancias de clase:

```gbn
var enemies: array[any] = []
$enemies.append($Enemy(10))
$print($enemies[2].hp)
```

---

## 12. Diccionarios

### Declaración

```gbn
var inventory: dict[int] = {}
```

### Uso básico

```gbn
$inventory["Potion"] = 5
$inventory["Sword"] = 1
$print($inventory)  -- {"Potion": 5, "Sword": 1}
```

### Diccionarios de objetos

```gbn
var inventory: dict[any] = {}
$inventory["weapon"] = Item("Sword")
$print($inventory["weapon"].name)
```

### Métodos de diccionario

| Método | Descripción |
|--------|-------------|
| `.size()` | Retorna el número de entradas |
| `.remove(clave)` | Elimina la entrada con esa clave |
| `.duplicate()` | Retorna una copia del diccionario |

---

## 13. Estructuras de control

### Condicional `if / elseif / else`

```gbn
if $x > 10
    $print("mayor")
elseif $x == 10
    $print("igual")
else
    $print("menor")
end
```

### Bucle `while`

```gbn
var i: int = 0
while $i < 10
    $print($i)
    $i += 1
end
```

### Bucle `for in`

Itera sobre arrays, rangos o diccionarios:

```gbn
for item in $enemies
    $print($item.hp)
end

for n in $range(5)
    $print($n)
end
```

### Palabras clave de control de bucles

| Keyword | Comportamiento |
|---------|----------------|
| `break` | Sale del bucle actual |
| `continue` | Salta a la siguiente iteración |
| `loop` | Reinicia la iteración actual desde el principio |
| `pass` | No hace nada (marcador de bloque vacío) |

### `await`

Pausa la ejecución hasta que una condición sea verdadera (polling cada 10ms):

```gbn
await $ready == true
```

---

## 14. Manejo de errores

```gbn
try
    -- código que puede fallar
catch
    -- código que se ejecuta si hay un error
end
```

También se acepta `except` como alias de `catch`:

```gbn
try
    var x: int = $int("no_es_numero")
except
    $print("Ocurrió un error de conversión")
end
```

---

## 15. Punteros

El operador `$$` crea un puntero a una variable existente. Al leer el puntero, se obtiene el valor actual de la variable apuntada:

```gbn
var hp: int = 100
var ref: any = $$hp

$print($ref)  -- Muestra el valor de hp a través del puntero
```

Los punteros permiten acceso indirecto y pueden apuntar a rutas complejas (`$$objeto.campo`, `$$array[0]`). Son útiles para alias y referencias dinámicas.

---

## 16. Módulos e importaciones

### `@use` — importar un módulo

Carga un archivo `.gbn` (u otro soportado) y expone todos sus símbolos en el ámbito actual:

```gbn
@use "utils.gbn"
@use "helpers"        -- detecta la extensión automáticamente
```

La importación es idempotente: si un módulo ya fue cargado, no se vuelve a ejecutar.

### `@from` / `@as` — importar con alias

Carga un módulo y lo expone como un namespace con nombre:

```gbn
@from "utils.gbn" @as utils
$print($utils.mi_funcion())
```

### Formatos soportados

| Extensión | Comportamiento |
|-----------|----------------|
| `.gbn` | Se ejecuta e integra al ámbito actual |
| `.py` | Se carga como módulo Python; sus atributos públicos se exponen |
| `.c`, `.cpp`, `.asm`, `.sh`, `.bash`, `.h` | El código fuente se expone como diccionario bajo `__source__` |

### Búsqueda automática de módulos

Si el path no contiene `/` y no empieza con `.`, el intérprete también busca en la carpeta `libs/` del proyecto.

---

## 17. Gestión de memoria

El intérprete tiene un límite configurable de **1024 slots** de memoria por defecto.

### `free` — liberar una variable

Elimina explícitamente una variable del ámbito:

```gbn
$free($mi_variable) 
```

### `expand_memory` — ampliar el límite

Aumenta el número máximo de slots disponibles:

```gbn
$expand_memory(512)
```

> ! Esto emite una advertencia en `stderr` indicando el cambio.

### `breakpoint` — pausar ejecución

Pausa la ejecución y da un resumen de la memoria:

```gbn
$breakpoint()
```

### Caché de expresiones

Las expresiones que aparecen repetidamente (por ejemplo, dentro de un bucle) se almacenan en caché como AST la primera vez que se parsean, evitando reparseos innecesarios en cada ciclo:

```gbn
var i: int = 0
while $i < 10000
    var x = ($i * 5) + (20 / 2)  -- la expresión se cachea
    $i += 1
end
```

### Garbage collector post-ejecución

Al terminar la ejecución, el motor libera automáticamente símbolos globales que fueron definidos pero nunca leídos (variables globales, funciones, clases, namespaces importados). También puede usarse `$free($var)` si es necesario.

### `--sm` — resumen de memoria

Al usar la flag `--sm`, el intérprete imprime el estado completo de la memoria al terminar:

```
Total memory: hp:int=100 | name:str='Juan' | ...
```

---

## 18. Funciones nativas (built-ins)

Estas funciones están disponibles sin necesidad de importar nada:

| Función | Descripción |
|---------|-------------|
| `$print(valor)` | Imprime un valor |
| `$int(valor)` | Convierte a entero |
| `$float(valor)` | Convierte a flotante |
| `$str(valor)` | Convierte a string |
| `$bool(valor)` | Convierte a booleano |
| `$range(n)` | Genera un rango de 0 a n-1 |
| `$len(coleccion)` | Retorna la longitud de una colección |
| `$file_read(ruta)` | Lee un archivo completo como string |
| `$file_lines(ruta)` | Lee un archivo como array de líneas |
| `$file_write(ruta, contenido)` | Escribe (sobreescribe) un archivo |
| `$file_append(ruta, contenido)` | Añade contenido al final de un archivo |
| `$file_exists(ruta)` | Retorna `true` si el archivo existe |

---

## 19. Biblioteca estándar (stdutils)

`stdutils.gbn` se carga automáticamente al inicio de cada programa. Proporciona:

### Constante de versión

```gbn
$print($GBN.VERSION) 
```

### Funciones de colecciones

| Función | Descripción |
|---------|-------------|
| `$contains(coleccion, elemento)` | `true` si el elemento está en la colección |
| `$index_of(coleccion, elemento)` | Índice del elemento, o `-1` si no existe |
| `$has_key(dict, clave)` | `true` si la clave existe en el diccionario |
| `$merge_dict(dest, origen)` | Fusiona `origen` en `dest` y retorna el resultado |

### Funciones de cadenas

| Función | Descripción |
|---------|-------------|
| `$str_split(texto, delimitador)` | Divide una cadena en un array |
| `$str_join(separador, items)` | Une un array de strings en uno solo |
| `$to_lower(texto)` | Convierte a minúsculas |
| `$to_upper(texto)` | Convierte a mayúsculas |
| `$starts_with(texto, prefijo)` | `true` si el texto empieza con el prefijo |
| `$ends_with(texto, sufijo)` | `true` si el texto termina con el sufijo |

### Entrada del usuario

```gbn
var nombre: str[64] = $input("¿Cómo te llamas? ")
```

---

## 20. Compilación a ejecutable

Con la flag `--c`, el intérprete intenta generar un ejecutable standalone usando PyInstaller:

```bash
Gybin mi_script.gbn --c
```

Si PyInstaller no está disponible, se genera un wrapper bash que invoca el intérprete directamente:

```bash
#!/usr/bin/env bash
exec Gybin "mi_script.gbn" "$@"
```

Con `--fc`, la compilación se fuerza incluso si el script tiene errores de ejecución.

---

## 21. Advertencias y análisis estático

Al ejecutar con `--w`, el motor activa un análisis post-ejecución que reporta:

- **Variables declaradas pero nunca leídas**
- **Funciones definidas pero nunca llamadas**
- **Funciones con cuerpo vacío**
- **Clases definidas pero nunca instanciadas**
- **Clases con cuerpo vacío**
- **Enums definidos pero nunca usados**
- **Variables multi-tipo con más de 3 tipos distintos usados**
- **Asignaciones sospechosas** (tipo declarado distinto al tipo real del valor)
- **Posibles memory leaks**: contenedores globales con más de 256 elementos nunca leídos

Las advertencias se imprimen en `stderr` con el formato:

```
Warning: archivo.gbn:42: Variable 'x' is declared but never read
```

> Las variables cuyos nombres empiezan con `_` son ignoradas por el analizador (convención de "intencionalmente no usado").

> Puede que recibas advertencias de código que nunca escribiste, pertenecen a código sin usar de librerías importadas 

---

## 22. Reglas y buenas prácticas

### El operador `$`

`$` es **obligatorio** para:
- Leer el valor de una variable: `$hp`
- Llamar a una función: `$print(...)`, `$add(1, 2)`
- Instanciar una clase: `$Player("Juan")`
- Asignar a una variable existente: `$hp = 50`
- Acceso encadenado: `$p.damage(30)`

`$` **no** se usa en:
- La declaración inicial (`var hp: int = 100`)
- El acceso a campos de objeto tras el punto (`$p.hp`, no `$p.$hp`)
- Los nombres de parámetros en la firma de funciones

### Scope

Las variables declaradas dentro de un bloque (función, bucle, condicional) son locales a ese bloque. Redefinir en un ámbito interior una variable del exterior puede causar conflictos:

```gbn
var global: int = 100

func test() -> NULL
    var global: int = 50  -- redefinición local
    $print($global)       -- error: ambigüedad de scope
end
```

Se recomienda usar nombres distintos para variables locales que coexisten con variables globales del mismo nombre.

### Uso de `any`

`any` desactiva la verificación de tipo. Se recomienda usarlo únicamente cuando sea estrictamente necesario, como en variables que almacenan valores de tipo desconocido en tiempo de declaración.

### Inicialización de colecciones

Siempre inicializa arrays y dicts con `[]` o `{}` si planeas operar sobre ellos inmediatamente. Usar `NULL` como valor inicial y luego intentar añadir elementos sin asignar primero una colección real producirá un error.

```gbn
-- Correcto:
var items: array[any] = []
$items.append($Item("Sword"))

-- Problemático si se usa append antes de asignar:
var items: array[any] = NULL
$items.append($Item("Sword"))  -- error
```

### Cierre de bloques con `end`

Todo bloque (`func`, `class`, `if`, `while`, `for`, `try`) debe cerrarse con `end`. Un bloque sin cerrar produce un `SyntaxError`.

> ! Si bien se puede escribir fuera de funciones, se recomienda que la mayor parte del script se organice en funciones.
