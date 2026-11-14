# Casos de uso

La [matriz de permisos](requerimientos.md#matriz-de-permisos) define las ubicaciones accesibles para cada actor. Las referencias `RF` apuntan a los [requerimientos funcionales](requerimientos.md#requerimientos-funcionales).

| Caso | Actor | Requerimientos |
|---|---|---|
| CU-01. Iniciar sesión | Administrador u operador | RF-01 |
| CU-02. Preparar la operación | Administrador | RF-02, RF-03, RF-04 |
| CU-03. Registrar una entrada | Administrador u operador autorizado | RF-05 |
| CU-04. Registrar una salida | Administrador u operador autorizado | RF-06 |
| CU-05. Trasladar existencias | Administrador u operador autorizado en ambas ubicaciones | RF-07 |
| CU-06. Consultar stock e historial | Administrador u operador autorizado | RF-08, RF-09 |

## CU-01. Iniciar sesión

1. El usuario envía sus credenciales.
2. El sistema las valida y abre la sesión con su rol y alcance de acceso.

**Resultado alternativo.** Si las credenciales son inválidas, la sesión permanece cerrada.

## CU-02. Preparar la operación

1. El administrador registra las ubicaciones.
2. Registra un producto con su SKU, unidad de medida y categoría.
3. Configura las cuentas de los operadores y les asigna ubicaciones.

**Resultado.** Los operadores pueden consultar y operar dentro de su alcance. Si el SKU ya existe, el registro del producto se rechaza.

**Edición.** El administrador puede renombrar una ubicación sin perder sus movimientos ni saldos. Puede editar el producto. Si ya tiene movimientos, su unidad de medida se conserva para que el historial mantenga el significado de las cantidades.

## CU-03. Registrar una entrada

1. El actor selecciona producto y ubicación e indica la cantidad recibida y la fecha del movimiento. Puede añadir una referencia.
2. El sistema valida el acceso y la cantidad.
3. El sistema incrementa el saldo y registra la entrada con el actor de la sesión y la fecha y hora de registro.

**Resultado.** La cantidad aparece en el stock y la entrada en el historial. El administrador puede seguir este flujo y seleccionar **Saldo inicial**.

## CU-04. Registrar una salida

1. El actor selecciona producto y ubicación e indica la cantidad entregada.
2. El sistema valida el acceso e intenta descontar la cantidad solo si el saldo disponible la cubre en ese momento.
3. El sistema guarda la salida con una variación negativa en el historial y confirma el saldo actualizado en la misma transacción.

**Resultado alternativo.** Si la cantidad es inválida o el saldo es insuficiente, se conservan el saldo y el historial previos.

## CU-05. Trasladar existencias

1. El actor selecciona producto, origen, destino y cantidad.
2. El sistema valida que las ubicaciones sean distintas y que el actor pueda operar en ambas.
3. El sistema comprueba las existencias en origen. Guarda el movimiento y las dos variaciones de saldo en una sola transacción.
4. El actor puede consultar el mismo identificador de traslado en los historiales autorizados, con una cantidad negativa en origen y positiva en destino.

**Resultado alternativo.** Si falla la validación o la transacción, ambas ubicaciones conservan sus existencias previas.

## CU-06. Consultar stock e historial

1. El actor selecciona una ubicación autorizada y consulta el saldo del producto.
2. Abre el historial y puede acotarlo por fecha y tipo de movimiento.
3. Revisa los registros para explicar la variación de existencias.

**Resultado.** Cada consulta devuelve datos dentro del alcance del actor.

## Recorrido de aceptación

| Paso | Operación | Saldo en A | Saldo en B |
|---|---|---:|---:|
| 1 | Registrar 100 unidades en A | 100 | 0 |
| 2 | Trasladar 30 unidades de A a B | 70 | 30 |
| 3 | Retirar 10 unidades de B | 70 | 20 |

El historial de A muestra la entrada y el traslado. El de B muestra el mismo traslado y la salida. Una salida de 21 unidades desde B debe rechazarse y conservar el saldo de 20.
