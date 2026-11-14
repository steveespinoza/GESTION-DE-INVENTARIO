# Gestión de Inventario

Kardex para empresas que necesitan saber cuánto stock tienen en cada ubicación y qué movimientos explican ese saldo. El proyecto parte de un flujo común que puede adaptarse a cada operación.

## Primera versión

- Acceso para administradores y operadores, con permisos por ubicación.
- Catálogo de productos con SKU, unidad de medida y categoría.
- Registro de saldo inicial, entradas, salidas y traslados.
- Consulta de stock actual e historial por ubicación.

La primera versión parte de que el saldo del sistema coincide con el inventario físico. Los movimientos representan operaciones reales y las salidas requieren saldo suficiente.

## Documentación

| Documento | Contenido |
|---|---|
| [Instalación local](docs/instalacion-local.md) | Dependencias, PostgreSQL, migraciones y arranque. |
| [Requerimientos](docs/requerimientos.md) | Alcance, matriz de permisos y criterios de aceptación. |
| [Casos de uso](docs/casos-de-uso.md) | Flujos de administración, registro de movimientos y consulta. |
| [Arquitectura](docs/arquitectura.md) | Componentes, modelo conceptual de datos, secuencia de un traslado y estrategia de pruebas. |

## Estado

La demo con React, Flask y PostgreSQL permite registrar entradas, saldos iniciales, salidas y traslados, y consultar el stock y el historial por ubicación. Desde **Administración** se pueden crear y editar productos, ubicaciones y usuarios.

## Probar la aplicación

Sigue la [guía de instalación local](docs/instalacion-local.md) para levantar Flask y PostgreSQL y cargar los datos ficticios.

### Recorrido de inventario

Abre `http://127.0.0.1:5000` e inicia sesión como `admin-demo` con la contraseña que elegiste al cargar los datos. En una base nueva, usa el producto **Cable eléctrico** para recorrer los tres movimientos.

| Operación | Almacén A | Almacén B |
|---|---:|---:|
| Registrar una entrada de 100 m en A | 100 m | 0 m |
| Trasladar 30 m de A a B | 70 m | 30 m |
| Registrar una salida de 10 m en B | 70 m | 20 m |

Al consultar los historiales, el traslado tiene el mismo identificador en ambos almacenes. En A aparece como −30 m y en B como +30 m. Una salida de 21 m desde B debe rechazarse y conservar el saldo de 20 m. Con `operador-demo` solo puedes operar en B, por lo que el formulario no ofrece la opción de traslado.

![Stock de 20 metros en Almacén B con el traslado de entrada y la salida en el historial](docs/imagenes/traslado-demo.png)

### Preparar tu propio catálogo

Con la cuenta de administrador, abre **Administración**. Crea un producto con SKU, nombre, unidad y categoría, y agrega un almacén desde **Ubicaciones**. Vuelve a **Movimientos**, selecciona el nuevo almacén y registra una entrada del producto para consultar su saldo e historial.

Puedes cambiar el nombre de un almacén y editar los datos del producto desde sus listas. La unidad de medida se puede corregir hasta el primer movimiento del producto.

### Asignar acceso a un almacén

En **Administración → Usuarios**, crea un operador con una contraseña de al menos 12 caracteres y marca **Almacén A**. Inicia sesión con esa cuenta en otra ventana y registra una entrada. Desde la cuenta de administrador, edita el operador, desmarca A y marca B. Al volver a la ventana del operador, la lista de ubicaciones se actualiza. Las siguientes consultas y movimientos ya usan la nueva asignación, incluso con la sesión abierta.

El rol administrador da acceso a todas las ubicaciones. Las asignaciones individuales se aplican al rol operador.

## Pruebas

[GitHub Actions](https://github.com/steveespinoza/GESTION-DE-INVENTARIO/actions/workflows/ci.yml) compila React y ejecuta las pruebas de Flask con PostgreSQL 17 en los PR hacia `main` y en los cambios que llegan a esa rama. La base de CI se crea para cada ejecución.

La suite comprueba permisos por ubicación, consistencia entre saldo e historial, descuentos concurrentes y el efecto de un fallo durante un traslado. Para ejecutarla en tu equipo, consulta [Ejecutar las pruebas](docs/instalacion-local.md#ejecutar-las-pruebas).
