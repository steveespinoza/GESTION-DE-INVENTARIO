# Instalación local

## Requisitos

- Git, Python 3.13, Node.js 22.12 o posterior dentro de la rama 22 y PostgreSQL 17 en ejecución.
- PowerShell para los comandos de esta guía.

## Clonar e instalar dependencias

```powershell
git clone https://github.com/steveespinoza/GESTION-DE-INVENTARIO.git
Set-Location GESTION-DE-INVENTARIO

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
```

El build genera `frontend/dist`. Flask sirve ese directorio y la API desde el mismo origen, por lo que basta con arrancar Flask para abrir la aplicación.

## Preparar PostgreSQL

Conéctate a la base `postgres` con una cuenta que pueda crear bases y ejecuta estas sentencias en `psql` o en la herramienta de consultas de pgAdmin. En pgAdmin, ejecuta cada sentencia por separado.

```sql
CREATE DATABASE inventario;
CREATE DATABASE inventario_test;
```

Usa el usuario propietario de cada base o un rol con permisos para crear las tablas en `inventario` y los esquemas de prueba en `inventario_test`. Si ya tienes una base de la aplicación, puedes usarla y aplicar las migraciones pendientes.

## Arrancar la aplicación

Desde la raíz del repositorio, configura la conexión en la misma ventana de PowerShell. Sustituye los valores de ejemplo de la URL por los de tu PostgreSQL. Si la contraseña contiene caracteres reservados de URI, codifícala antes de incluirla en la URL.

```powershell
$env:DATABASE_URL = 'postgresql://usuario:clave@127.0.0.1:5432/inventario'
$env:SECRET_KEY = .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
$env:COOKIE_SECURE = '0'

Set-Location backend
..\.venv\Scripts\python.exe -m flask --app inventory migrate
..\.venv\Scripts\python.exe -m flask --app inventory seed-demo
..\.venv\Scripts\python.exe -m flask --app inventory run --host 127.0.0.1
```

El comando `seed-demo` pide una contraseña de al menos 12 caracteres y la asigna a las cuentas nuevas `admin-demo` y `operador-demo`. Si vuelves a ejecutarlo, las cuentas existentes conservan sus contraseñas. `COOKIE_SECURE=0` permite usar la cookie de sesión sobre HTTP en esta instalación local. Guarda la clave de sesión fuera del repositorio si quieres mantener las sesiones tras reiniciar Flask.

Abre [http://127.0.0.1:5000](http://127.0.0.1:5000) y sigue el [recorrido de inventario](../README.md#recorrido-de-inventario). Para detener Flask, pulsa Ctrl+C.

## Ejecutar las pruebas

Desde la carpeta `backend`, apunta la suite a la base separada de pruebas:

```powershell
$env:TEST_DATABASE_URL = 'postgresql://usuario:clave@127.0.0.1:5432/inventario_test'
..\.venv\Scripts\python.exe -m pytest -q -rs
```

Las pruebas de integración crean un esquema temporal por caso y lo eliminan al terminar. Si aparecen pruebas omitidas, comprueba que `TEST_DATABASE_URL` esté definida en la ventana donde ejecutas pytest.

### Prueba de navegador

Con el frontend ya compilado y `TEST_DATABASE_URL` apuntando a la base de pruebas, ejecuta desde `backend`:

```powershell
..\.venv\Scripts\python.exe -m pip install -r requirements-e2e.txt
..\.venv\Scripts\python.exe -m playwright install chromium
..\.venv\Scripts\python.exe -m pytest -q -rs e2e
```

La prueba abre Chromium, levanta Flask en un puerto local libre y carga datos ficticios en un esquema temporal. Comprueba los saldos de 70 m en A y 20 m en B, el mismo ID de traslado en ambos historiales y el rechazo de una salida de 21 m desde B.
