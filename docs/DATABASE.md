# Base de datos

Motor por defecto: SQLite en `backend/balanceflow.db` (`DATABASE_URL=sqlite:///./balanceflow.db`). No hay carpeta de migraciones ni Alembic. Al importar `main.py`, `Base.metadata.create_all` crea las tablas que falten y no altera columnas ya existentes.

`seed.py` borra todas las filas de transacciones, sucursales y empresas y las vuelve a insertar. Hay que detener Uvicorn antes de ejecutarlo.

## empresas

| Columna | Tipo | Regla |
|---|---|---|
| id | entero | clave primaria |
| nombre | texto 120 | obligatorio |
| pais | texto 60 | obligatorio |
| moneda_local | texto 3 | obligatorio |
| activa | booleano | por defecto verdadero |
| creada_en | fecha y hora | valor del servidor |

Relaciones: `sucursales` y `transacciones`, con borrado en cascada definido en el ORM.

## sucursales

| Columna | Tipo | Regla |
|---|---|---|
| id | entero | clave primaria |
| empresa_id | entero | clave foránea a `empresas.id`, indexada |
| nombre | texto 120 | obligatorio |
| ciudad | texto 80 | opcional |
| activa | booleano | por defecto verdadero |
| creada_en | fecha y hora | valor del servidor |

No hay relación declarada desde `Sucursal` hacia `Transaccion`. Borrar una sucursal con transacciones que la referencian depende de la clave foránea de SQLite. El modelo de transacción declara `ForeignKey("sucursales.id")` sin `ondelete`.

## transacciones

| Columna | Tipo | Regla |
|---|---|---|
| id | entero | clave primaria |
| empresa_id | entero | clave foránea a `empresas.id`, indexada |
| sucursal_id | entero | clave foránea a `sucursales.id`, opcional, indexada |
| fecha | fecha | obligatoria |
| cuenta | texto 20 | obligatoria, indexada |
| descripcion | texto 255 | opcional |
| monto | float | obligatorio, en la moneda original |
| moneda | texto 3 | obligatoria |
| monto_base | float | opcional en la tabla; la API lo calcula en GTQ al crear, editar o importar |
| banco | texto 80 | opcional |
| categoria | texto 80 | opcional |
| es_intercompany | texto 1 | `S` o `N`, por defecto `N` |
| empresa_contraparte_id | entero | opcional. No es clave foránea |
| archivo_origen | texto 255 | opcional |
| fila_origen | entero | opcional |
| creada_en | fecha y hora | valor del servidor |

`empresa_contraparte_id` no tiene restricción en la base. La API comprueba que la empresa exista al crear o editar por JSON. Una importación guarda el número leído del archivo sin esa comprobación.

Los importes son `Float`, no decimal. Eso es una limitación contable conocida y no hay una migración que la cambie.

## Datos de demostración

`seed.py` crea 6 empresas, 7 sucursales, movimientos de balance y de operación, tres pares intercompany con el espejo convertido a la moneda de la contraparte, y errores a propósito: duplicado, moneda `XYZ`, ingreso negativo, intercompany sin contraparte y cuenta `9999`.
