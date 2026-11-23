# Base de datos

La prueba local usa PostgreSQL en `127.0.0.1:5433`, base `balanceflow`, con `DATABASE_URL=postgresql+psycopg://...` en `backend/.env`. El clúster vive en `backend/.pgdata` y no se versiona. SQLite sigue siendo el motor de las pruebas automáticas. No hay carpeta de migraciones ni Alembic. Al importar `main.py`, `Base.metadata.create_all` crea las tablas que falten y no altera columnas ya existentes.

`seed.py` solo borra y vuelve a crear el grupo llamado Demostración. Hay que detener Uvicorn antes de ejecutarlo. Al arrancar, `database/bootstrap.py` asigna un grupo a filas antiguas sin `grupo_id`, siembra tasas y crea el administrador de `.env` si la base no tiene usuarios.

## grupos

| Columna | Tipo | Regla |
|---|---|---|
| id | entero | clave primaria |
| nombre | texto 120 | obligatorio |
| creado_en | fecha y hora | valor del servidor |

## empresas

| Columna | Tipo | Regla |
|---|---|---|
| id | entero | clave primaria |
| grupo_id | entero | clave foránea a `grupos.id`, indexada |
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

El modelo declara `ForeignKey("sucursales.id", ondelete="SET NULL")`. Una base ya creada no adopta esa cláusula sola. Al borrar, la API pone `sucursal_id` en nulo y `PRAGMA foreign_keys=ON` queda activo en cada conexión SQLite.

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
| monto_base | float | caché en la moneda del grupo. El consolidado lo vuelve a calcular |
| banco | texto 80 | opcional |
| categoria | texto 80 | opcional |
| es_intercompany | texto 1 | `S` o `N`, por defecto `N` |
| empresa_contraparte_id | entero | opcional. No es clave foránea |
| archivo_origen | texto 255 | opcional |
| fila_origen | entero | opcional |
| creada_en | fecha y hora | valor del servidor |

`empresa_contraparte_id` no tiene restricción en la base. La API comprueba que la empresa exista al crear o editar por JSON. Una importación anula el número si esa empresa no existe.

Los importes son `Float`. El cálculo de negocio redondea a centavos antes de operar. No hay una migración que cambie el tipo de columna.

## usuarios, tasas, parámetros, tickets y auditoría

`usuarios`: `email` único, `nombre`, `password_hash`, `rol` (`admin`, `lector` o `empresa`), `grupo_id`, `empresa_id` (solo si el rol es `empresa`) y `activo`.

`tasas_cambio`: clave `(grupo_id, moneda)` y `tasa_gtq`.

`parametros`: clave `(grupo_id, clave)` y `valor`. Las claves usadas son `moneda_base` y `wacc`.

`tickets_soporte`: `usuario_id`, `mensaje` (hasta 1000) y `creado_en`.

`eventos_auditoria`: `grupo_id`, `transaccion_id` (sin clave foránea, para conservar el hecho si el movimiento se borra), `empresa_id`, `accion` (`creada`, `importada`, `editada`, `eliminada`), `usuario_id` opcional, `detalle` en JSON y `creado_en`.

El arranque crea las tasas y los parámetros del grupo si faltan, el primer administrador si no hay usuarios, y un hecho de alta para los movimientos que todavía no tenían rastro.

## Datos de demostración

`seed.py` crea 6 empresas, 7 sucursales, movimientos de balance y de operación, tres pares intercompany con el espejo convertido a la moneda de la contraparte, y errores a propósito: duplicado, moneda `XYZ`, ingreso negativo, intercompany sin contraparte y cuenta `9999`.
