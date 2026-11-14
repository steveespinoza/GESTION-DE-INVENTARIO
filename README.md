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

La demo con React, Flask y PostgreSQL permite registrar entradas, saldos iniciales y salidas, y consultar el stock y el historial por ubicación. El catálogo y las cuentas se cargan con datos de demostración. Los traslados y las pantallas de administración están pendientes.

![Entrada de 100 metros registrada en el almacén A, con stock e historial actualizados](docs/imagenes/entrada-demo.png)

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

Abre `http://127.0.0.1:5000` e inicia sesión como `admin-demo` con la contraseña que elegiste al cargar los datos. Selecciona **Almacén A** y **Cable eléctrico**. Registra una entrada de 100 m y luego una salida de 30 m. El saldo debe quedar en 70 m y el historial debe mostrar ambos movimientos. Una salida de 71 m debe rechazarse y conservar ese saldo. Con `operador-demo` puedes comprobar que solo aparece el almacén B.

Si ya tienes la base de la demo de entradas, ejecuta `flask --app inventory migrate` con su URL para añadir las salidas y conservar los registros existentes.

## Pruebas

Desde `backend`, define una URL para una base de pruebas y ejecuta:

```powershell
$env:TEST_DATABASE_URL = 'postgresql://usuario:contraseña@localhost:5432/inventario_test'
..\.venv\Scripts\python.exe -m pytest -q
```

La suite verifica permisos por ubicación, validación de cantidades y consistencia entre saldo e historial. También comprueba que solo una de dos salidas simultáneas de 8 unidades se confirme cuando hay 10 disponibles, y que un fallo al guardar el movimiento revierta el descuento. Las pruebas de integración crean un esquema temporal por caso y lo eliminan al terminar.
