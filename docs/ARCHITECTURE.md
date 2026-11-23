# Arquitectura

BalanceFlow es un solo repositorio con dos aplicaciones: una API FastAPI en `backend/` y una interfaz React en `frontend/`. No hay un bus de eventos ni una base compartida en el frontend. La interfaz lee y escribe únicamente por HTTP.

## Capas del backend

| Capa | Ubicación | Responsabilidad |
|---|---|---|
| Entrada HTTP | `backend/main.py` y `backend/routers/` | Rutas, códigos de estado y dependencia de sesión |
| Contratos | `backend/schemas/` | Validación de entrada y forma de la respuesta con Pydantic |
| Dominio | `backend/services/` | Ingesta, conversión, eliminación intercompany, indicadores, aduana, parámetros y auditoría |
| Persistencia | `backend/models/` y `backend/database/connection.py` | Tablas SQLAlchemy y sesión por request |
| Configuración | `backend/core/config.py` | Valores por defecto y variables de entorno |

No hay repositorio separado de los modelos: cada endpoint consulta SQLAlchemy directamente. `main.py` concentra el CRUD de empresas, sucursales y transacciones, y el rastro de cada movimiento. `core/acceso.py` limita las consultas al grupo y, si el rol es `empresa`, a esa empresa. Los routers cubren acceso, carga, consolidación, trazabilidad, validación, exportación, configuración y soporte.

## Capas del frontend

| Capa | Ubicación | Responsabilidad |
|---|---|---|
| Arranque | `frontend/src/main.jsx`, `frontend/index.html` | Monta React |
| Interfaz | `frontend/src/App.jsx` | Navegación interna, vistas y formularios |
| Estilos | `frontend/src/styles.css` | Presentación |
| HTTP | `frontend/src/services.js` | `api()`, cabecera `Authorization` y sesión en `sessionStorage` |

No hay enrutador de URLs, almacén global ni datos simulados. La vista activa vive en el estado `page`.

## Flujo de una consolidación

1. El frontend pide empresas, sucursales, transacciones, el resumen y la auditoría.
2. La API lee `transacciones`.
3. `consolidar_grupo` vuelve a calcular `monto_base` con las tasas guardadas y la moneda pedida, elimina pares intercompany y calcula NOPAT, ROIC, ROCE y EVA.
4. La respuesta vuelve al estado de React. Exportar Excel o CSV repite ese cálculo y devuelve un archivo.

## Lo que esta arquitectura no incluye

- Migraciones versionadas. Las tablas nuevas se crean con `Base.metadata.create_all`. El arranque agrega `grupo_id` y recompone tasas y parámetros cuando la base es anterior al servicio.
- Tasas oficiales por periodo y límite de peticiones.
- La prueba local puede usar PostgreSQL con `DATABASE_URL=postgresql+psycopg://...`. Las pruebas automáticas siguen en un SQLite temporal.
