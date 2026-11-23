# Backend

API de consolidación financiera. Se ejecuta desde `backend/` con Uvicorn.

## Stack

Declarado en `backend/requirements.txt`:

| Paquete | Versión declarada |
|---|---|
| fastapi | 0.165.0 |
| uvicorn | 0.54.0 |
| sqlalchemy | 2.1.9 |
| pydantic | 2.14.4 |
| pydantic-settings | 2.16.3 |
| pandas | 3.1.1 |
| numpy | 2.5.5 |
| openpyxl | 3.1.5 |
| python-multipart | 0.0.34 |
| requests | 2.34.2 |
| psycopg[binary] | 3.3.9 |

Pruebas, en `requirements-dev.txt`: pytest 8.4.2 y httpx 0.28.1. El intérprete usado en este entorno es Python 3.11.

## Módulos

- `main.py`: aplicación, CORS, salud y CRUD.
- `models/empresa.py`, `sucursal.py`, `transaccion.py`: tablas.
- `schemas/`: `EmpresaCreate/Update/Response`, `SucursalCreate/Update/Response`, `TransaccionCreate/Update/Response`.
- `routers/uploads.py`: `POST /api/uploads/excel`.
- `routers/consolidacion.py`: resumen, indicadores de una empresa e intercompany.
- `routers/trazabilidad.py`: drill-down por componente.
- `routers/validacion.py`: aduana sobre lo persistido.
- `routers/exportacion.py`: Excel y CSV.
- `services/ingesta.py`: lectura y normalización de CSV/Excel.
- `services/consolidacion.py`: tasas, eliminación de pares e indicadores.
- `services/validacion.py`: moneda, cuenta, signo, duplicados e intercompany.
- `services/exportacion.py`: libro Excel.
- `services/divisas.py`: convierte con la misma tabla de tasas. Ningún router lo importa; el motor usa `services.consolidacion`.
- `seed.py`: borra y vuelve a crear datos de demostración.
- `dashboard/app.py`: prototipo Streamlit. Llama rutas que la API no expone (`/api/consolidado`, `/api/empresas/{id}/upload`, `/api/empresas/{id}/auditar`). No forma parte de la aplicación React.

## Endpoints

| Método | Ruta | Éxito | Errores relevantes |
|---|---|---|---|
| GET | `/` | 200, estado y versión | |
| GET | `/health` | 200, `healthy` o `unhealthy` | No devuelve la URL de la base |
| POST | `/api/empresas` | 201 | 422 si el cuerpo no cumple el esquema |
| GET | `/api/empresas` | 200, lista | |
| GET | `/api/empresas/{id}` | 200 | 404 |
| PATCH | `/api/empresas/{id}` | 200 | 404, 422 |
| DELETE | `/api/empresas/{id}` | 204 | 404. Borra sucursales y transacciones por cascada ORM |
| POST | `/api/sucursales` | 201 | 400 si la empresa no existe |
| GET | `/api/sucursales?empresa_id=` | 200 | |
| GET/PATCH/DELETE | `/api/sucursales/{id}` | 200 / 200 / 204 | 404 |
| POST | `/api/transacciones` | 201. Calcula `monto_base` | 400 si empresa, sucursal o contraparte no cuadran |
| GET | `/api/transacciones?empresa_id=&sucursal_id=&limit=` | 200 | 400 si `limit` no está entre 1 y 1000. Tope por defecto 500 |
| GET/PATCH/DELETE | `/api/transacciones/{id}` | 200 / 200 / 204 | 404 |
| POST | `/api/uploads/excel` | 200, conteos y bloque `validacion` | 400, 413 (más de 10 MB), 422, 500 |
| GET | `/api/consolidacion/resumen` | 200 | 404 sin transacciones, 422 |
| GET | `/api/consolidacion/por-empresa/{id}` | 200 | 404, 422 |
| GET | `/api/consolidacion/intercompany` | 200 | 404 |
| GET | `/api/trazabilidad/{componente}?empresa_id=` | 200 | 400 si el componente no es `ingresos`, `gastos`, `activos` o `pasivos` |
| GET | `/api/validacion?empresa_id=` | 200, estado `LIMPIO` o `CON_ERRORES` | |
| GET | `/api/exportar/excel` | 200, archivo `.xlsx` | 404, 422 |
| GET | `/api/exportacion/csv` | 200, archivo `.csv` | 404, 422 |

No hay paginación por cursor ni ordenación en el servidor. El listado de transacciones aplica `limit` y los filtros de empresa y sucursal.

## Cálculo

Tasas fijas en `TASAS_CAMBIO` (GTQ, USD 7.85, EUR 8.55, MXN 0.45, CRC 0.015, HNL 0.32, NIO 0.21, PAB 7.85). Una moneda desconocida se convierte a 0 y no detiene el consolidado.

Un par intercompany se elimina si cada movimiento apunta a la otra empresa y el valor absoluto en GTQ difiere en 1 o menos. WACC fijo de 0.10. NOPAT = cuentas `4` menos valor absoluto de cuentas `5`. Capital invertido = cuentas `1` menos cuentas `2`, con mínimo 1.

## Configuración

`backend/.env.example` documenta `DEBUG`, `DATABASE_URL` y `ALLOWED_ORIGINS` (orígenes separados por coma). Por defecto el origen permitido es el frontend en el puerto 5173 y `DEBUG` es falso, así que SQLAlchemy no imprime las consultas.
