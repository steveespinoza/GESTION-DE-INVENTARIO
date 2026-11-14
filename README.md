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
| [Requerimientos](docs/requerimientos.md) | Alcance, matriz de permisos y criterios de aceptación. |
| [Casos de uso](docs/casos-de-uso.md) | Flujos de administración, registro de movimientos y consulta. |
| [Arquitectura](docs/arquitectura.md) | Componentes, modelo conceptual de datos, secuencia de un traslado y estrategia de pruebas. |

## Estado

La demo con React, Flask y PostgreSQL permite registrar entradas, saldos iniciales, salidas y traslados, y consultar el stock y el historial por ubicación. Desde **Administración** se pueden crear y editar productos y ubicaciones. Las cuentas y asignaciones aún se cargan con datos de demostración.

## Ejecutar la demo local

Requisitos de la demo verificada: Python 3.13, Node.js 20.19+ o 22.12+ y PostgreSQL 17. Crea una base vacía de desarrollo y usa su URL en `DATABASE_URL`.

Desde la raíz del repositorio, en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build

$env:DATABASE_URL = 'postgresql://usuario:contraseña@localhost:5432/inventario'
$env:SECRET_KEY = [guid]::NewGuid().ToString('N')
$env:COOKIE_SECURE = '0'
Set-Location backend
..\.venv\Scripts\python.exe -m flask --app inventory migrate
..\.venv\Scripts\python.exe -m flask --app inventory seed-demo
..\.venv\Scripts\python.exe -m flask --app inventory run
```

### Recorrido de inventario

Abre `http://127.0.0.1:5000` e inicia sesión como `admin-demo` con la contraseña que elegiste al cargar los datos. En una base nueva, usa el producto **Cable eléctrico** para recorrer los tres movimientos.

| Operación | Almacén A | Almacén B |
|---|---:|---:|
| Registrar una entrada de 100 m en A | 100 m | 0 m |
| Trasladar 30 m de A a B | 70 m | 30 m |
| Registrar una salida de 10 m en B | 70 m | 20 m |

Al consultar los historiales, el traslado tiene el mismo identificador en ambos almacenes. En A aparece como −30 m y en B como +30 m. Una salida de 21 m desde B debe rechazarse y conservar el saldo de 20 m. Con `operador-demo` solo puedes operar en B, por lo que el formulario no ofrece la opción de traslado.

![Stock de 20 metros en Almacén B con el traslado de entrada y la salida en el historial](docs/imagenes/traslado-demo.png)

Si ya tienes una base de la demo, ejecuta `flask --app inventory migrate` con su URL para habilitar los traslados y conservar los registros existentes.

### Preparar tu propio catálogo

Con la cuenta de administrador, abre **Administración**. Crea un producto con SKU, nombre, unidad y categoría, y agrega un almacén desde **Ubicaciones**. Vuelve a **Movimientos**, selecciona el nuevo almacén y registra una entrada del producto para consultar su saldo e historial.

Puedes cambiar el nombre de un almacén y editar los datos del producto desde sus listas. La unidad de medida se puede corregir hasta el primer movimiento del producto.

## Pruebas

Desde `backend`, define una URL para una base de pruebas y ejecuta:

```powershell
$env:TEST_DATABASE_URL = 'postgresql://usuario:contraseña@localhost:5432/inventario_test'
..\.venv\Scripts\python.exe -m pytest -q
```

La suite verifica permisos por ubicación, consistencia entre saldo e historial y descuentos concurrentes. En los traslados comprueba que el mismo movimiento aparezca en ambos historiales, que un fallo en destino revierta el descuento en origen y que dos traslados simultáneos en sentidos opuestos conserven los saldos esperados. Las pruebas de integración crean un esquema temporal por caso y lo eliminan al terminar.
