# Requerimientos

Definí el alcance inicial para una empresa con varias ubicaciones de inventario. La aplicación controla cantidades y registra cómo cambian a lo largo del tiempo. La premisa es que cada movimiento refleja una operación física registrada correctamente.

## Matriz de permisos

| Acción | Administrador | Operador |
|---|---|---|
| Administrar usuarios y sus asignaciones | Sí | — |
| Administrar productos y ubicaciones | Sí | — |
| Consultar stock e historial | Todas las ubicaciones | Ubicaciones asignadas |
| Registrar entradas y salidas | Todas las ubicaciones | Ubicaciones asignadas |
| Registrar traslados | Entre ubicaciones de la instalación | Requiere acceso a origen y destino |

El administrador registra el saldo inicial como una entrada de tipo **Saldo inicial**. La fecha del movimiento es obligatoria. El sistema registra automáticamente la fecha y hora de registro. La referencia es opcional.

## Requerimientos funcionales

| ID | Requerimiento | Criterio de aceptación |
|---|---|---|
| RF-01 | Iniciar sesión. | Una cuenta con credenciales válidas puede iniciar sesión. Las credenciales inválidas no abren una sesión. |
| RF-02 | Administrar usuarios, roles y acceso a ubicaciones. | Un administrador lista, crea y edita cuentas. Si cambia un operador de A a B, las siguientes consultas y operaciones de esa sesión se autorizan en B y se rechazan en A. |
| RF-03 | Administrar el catálogo de productos. | El administrador lista, crea y edita productos con nombre, SKU, unidad de medida y categoría. Los SKU duplicados se rechazan. La unidad queda fija desde el primer movimiento. |
| RF-04 | Administrar ubicaciones de inventario. | El administrador lista, crea y renombra ubicaciones. El cambio de nombre conserva sus saldos e historial. |
| RF-05 | Registrar saldo inicial y entradas. | Registrar una entrada de 100 unidades incrementa el saldo en 100 y crea un movimiento en el historial. Una entrada de saldo inicial se puede identificar como tal. |
| RF-06 | Registrar salidas. | Con 10 unidades disponibles, retirar 8 deja 2. Una solicitud posterior de 3 se rechaza y conserva el saldo y el historial. |
| RF-07 | Trasladar stock entre ubicaciones. | Trasladar 30 unidades de A a B descuenta 30 de A y suma 30 en B. Un traslado sin saldo suficiente o sin permiso sobre uno de los extremos se rechaza y conserva ambos saldos. |
| RF-08 | Consultar stock por producto y ubicación. | Si un producto tiene 70 unidades en A y 20 en B, la consulta muestra el saldo correspondiente a cada ubicación autorizada. |
| RF-09 | Consultar historial de movimientos. | El historial muestra tipo, producto, cantidad, ubicación, actor, fecha y referencia según lo registrado. Puede filtrarse por fecha y tipo. |

## Reglas de integridad

- **RI-01.** La API comprueba la identidad, el rol y el alcance por ubicación. Un rechazo por permisos conserva los datos.
- **RI-02.** La cantidad de un movimiento debe ser positiva y finita y admite hasta tres decimales. Un traslado requiere dos ubicaciones distintas.
- **RI-03.** El saldo se valida al aplicar el descuento. Si dos salidas concurrentes solicitan 8 unidades sobre un saldo de 10, se confirma una y quedan 2.
- **RI-04.** Cada movimiento y sus cambios de saldo se confirman en una sola transacción. Si falla un paso del traslado, se conservan los saldos y el historial previos.
- **RI-05.** El saldo de un producto en una ubicación coincide con la suma de las variaciones registradas para esa combinación.

## Alcance posterior

Dejé como ampliaciones los pedidos y aprobaciones, compras y proveedores, FIFO y reportes económicos, exportaciones, jerarquías de categorías y administración maestra. Los ajustes, las reversiones, la conciliación y el autoajuste quedan fuera de esta versión por la premisa del inventario.
