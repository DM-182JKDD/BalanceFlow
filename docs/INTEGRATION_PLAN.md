# Plan de integración

Hay un solo repositorio Git, no dos. `origin/develop` es un commit inicial con árbol vacío y sin ancestro común con `main`. La rama de trabajo es `feature/fullstack-integration`, creada desde `main`, que es la única línea que contiene la aplicación. No se hizo merge hacia `develop` ni hacia `main`.

## Qué ya coincidía

El frontend ya llamaba empresas, sucursales, transacciones, `POST /api/uploads/excel` y `GET /api/consolidacion/resumen`. Esos contratos existían. No había datos simulados en React: si la API no respondía, las vistas quedaban vacías o en error.

## Incompatibilidades que había que resolver

| Frente | Problema | Decisión |
|---|---|---|
| Exportación | El router no compilaba por un conflicto. Una versión era `/api/exportar/excel` y la otra `/api/exportacion/csv`. El frontend pide Excel | Se conservan las dos rutas |
| Edición de transacciones | El modal hacía `PATCH` y la API no tenía esa ruta | Se agregó `PATCH /api/transacciones/{id}` |
| `monto_base` | Solo se recalculaba si todas las filas venían vacías. El alta no lo guardaba | Se completa cada fila vacía y se persiste al crear, editar e importar |
| Pares del seed | El espejo repetía el importe en otra moneda, así que no cuadraba en GTQ | El seed convierte el espejo a la moneda de la contraparte |
| Aduana | `services/validacion.py` no tenía ruta y la interfaz no podía mostrarla | `GET /api/validacion` y el bloque `validacion` de la carga |
| Trazabilidad | El endpoint existía y ninguna vista lo usaba | La consolidación consulta `ingresos`, `gastos`, `activos` y `pasivos` |
| Filtros y rango | El botón de filtros no filtraba y el rango de 30 días no cambiaba la gráfica | Filtro local por empresa y tipo; la gráfica respeta el rango |
| Moneda en la tabla | Se formateaba `monto_base` con la moneda original | La tabla muestra `monto` y `moneda` |
| CORS y salud | Orígenes abiertos y URL de la base en `/health` | Orígenes explícitos y respuesta sin cadena de conexión |
| Vite | No había `vite.config.js` y las dependencias eran `latest` | Configuración de React y versiones con rango |
| JSON del consolidado | Pandas deja `NaN` en campos nulos y la respuesta no es JSON | El motor convierte `NaN` y fechas a valores serializables |

## Orden aplicado

1. Dejar el backend importable y con los dos formatos de exportación.
2. Completar el contrato que el modal ya usaba (`PATCH`, referencias y `monto_base`).
3. Exponer validación y trazabilidad, que ya tenían servicio.
4. Ajustar la interfaz a esas respuestas, sin vistas nuevas de autenticación.
5. Cubrir con pruebas el consolidado, la aduana y el CRUD que usa la interfaz.

## Pendiente, a propósito

- Autenticación y roles. La hoja de ruta del proyecto los menciona y no hay flujo de acceso en la interfaz. Agregar uno sería una función nueva, no una conexión.
- Cuarentena que rechace filas inválidas antes de insertarlas. Hoy se insertan y se informan.
- Asociar la sucursal detectada en un archivo con `sucursal_id`.
- Paginación en servidor más allá de `limit`.
- Reescribir el dashboard Streamlit. Sus rutas no existen y no es el cliente integrado.
- PostgreSQL y migraciones.
- Tasas oficiales por periodo.

## Cómo ejecutarlo

Backend, desde `backend/`:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
py seed.py
py -m uvicorn main:app --reload
```

Frontend, desde `frontend/`:

```powershell
copy .env.example .env
npm install
npm run dev
```

La interfaz queda en `http://localhost:5173` y la API en `http://127.0.0.1:8000`. Swagger sigue en `/docs`.

Pruebas y compilación:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
cd ..\frontend
npm run build
```
