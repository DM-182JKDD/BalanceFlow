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

Pruebas, en `requirements-dev.txt`: pytest 8.4.2 y httpx 0.28.1. En este entorno el intérprete es Python 3.13, porque `numpy` 2.5.5 no publica rueda para 3.11.

## Módulos

- `main.py`: aplicación, CORS, sesión, salud y CRUD.
- `models/`: empresas, sucursales, transacciones, usuarios, tasas, parámetros y tickets.
- `schemas/`: `EmpresaCreate/Update/Response`, `SucursalCreate/Update/Response`, `TransaccionCreate/Update/Response`.
- `routers/uploads.py`: `POST /api/uploads/excel`.
- `routers/auth.py`, `configuracion.py`, `soporte.py`: login, usuarios, tasas y tickets.
- `routers/consolidacion.py`: resumen, indicadores, intercompany, serie y desviaciones.
- `routers/trazabilidad.py`: drill-down por componente.
- `routers/validacion.py`: aduana sobre lo persistido.
- `routers/exportacion.py`: Excel y CSV.
- `services/ingesta.py`: lectura y normalización de CSV/Excel.
- `services/consolidacion.py`: tasas, eliminación de pares e indicadores.
- `services/validacion.py`: moneda, cuenta, signo, duplicados e intercompany.
- `services/exportacion.py`: libro Excel.
- `services/divisas.py`: convierte con la misma tabla de tasas. Ningún router lo importa; el motor usa `services.consolidacion`.
- `seed.py`: borra y vuelve a crear datos de demostración.
- `dashboard/app.py`: prototipo Streamlit que entra con `POST /api/auth/login`, lee empresas y el resumen, y sube con `POST /api/uploads/excel`. No forma parte de la aplicación React y Streamlit no está en `requirements.txt`.

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
| GET | `/api/transacciones` | 200, `{items,total,offset,limit}` | 400 si `limit` no está entre 1 y 200 o `offset` es negativo. Defecto 50 |
| GET | `/api/transacciones/conteo` | 200, conteo por empresa | |
| GET/PATCH/DELETE | `/api/transacciones/{id}` | 200 / 200 / 204 | 404 |
| GET | `/api/transacciones/{id}/auditoria` | 200. Hechos de alta, edición y baja, también si el movimiento ya se eliminó | 404 si no está en el grupo o en la empresa del usuario |
| POST | `/api/uploads/excel` | 200, conteos, cuarentena y `validacion` | 400, 413 (más de 10 MB), 422, 500 |
| GET | `/api/consolidacion/resumen` | 200, también sin transacciones | 422 |
| GET | `/api/consolidacion/por-empresa/{id}` | 200, también sin movimientos | 422 |
| GET | `/api/consolidacion/intercompany` | 200 | |
| GET | `/api/consolidacion/serie?ventana=` | 200 | 400 si la ventana sale de 1 a 730 |
| GET | `/api/consolidacion/desviaciones?dias=` | 200 | 400 si los días salen de 1 a 365 |
| GET | `/api/trazabilidad/{componente}?empresa_id=` | 200 | 400 si el componente no es `ingresos`, `gastos`, `activos` o `pasivos` |
| GET | `/api/validacion?empresa_id=` | 200, estado `LIMPIO` o `CON_ERRORES` | |
| GET | `/api/exportar/excel` | 200, archivo `.xlsx` | |
| GET | `/api/exportacion/csv` | 200, archivo `.csv` | |
| POST | `/api/auth/login` | 200, token y usuario | 401 |
| POST | `/api/auth/usuarios` | 201 | 403, 409, 422 |
| GET/PATCH | `/api/configuracion` | 200 | 422 |
| POST | `/api/soporte` | 201 | 401, 422 |

El listado pagina con `offset` y `limit`, filtra por texto, empresa, sucursal e intercompany, y ordena por fecha, monto o id. Borrar una sucursal pone `sucursal_id` en nulo en sus transacciones y después borra la sucursal.

## Cálculo

La primera semilla de tasas está en `TASAS_CAMBIO` (GTQ, USD 7.85, EUR 8.55, MXN 0.45, CRC 0.015, HNL 0.32, NIO 0.21, PAB 7.85), expresada en GTQ por unidad. El consolidado usa las tasas guardadas y vuelve a convertir cada monto original a la moneda pedida. Una moneda desconocida se convierte a 0 y no detiene el consolidado.

Un par intercompany se elimina si cada movimiento apunta a la otra empresa y el valor absoluto en la moneda del grupo difiere en 1 o menos. El WACC inicial es 0.10 y se puede cambiar. NOPAT = cuentas `4` menos valor absoluto de cuentas `5`. Capital invertido = cuentas `1` menos cuentas `2`, con mínimo 1. Los importes del cálculo se redondean a centavos.

## Configuración

`backend/.env.example` documenta `DEBUG`, `DATABASE_URL`, `ALLOWED_ORIGINS`, `SECRET_KEY`, `ADMIN_EMAIL` y `ADMIN_PASSWORD`. El primer arranque crea el administrador con esas variables. Si falta la contraseña, imprime una al azar una sola vez. Por defecto el origen permitido es el frontend en el puerto 5173 y `DEBUG` es falso.
