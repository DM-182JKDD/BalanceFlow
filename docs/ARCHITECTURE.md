# Arquitectura

BalanceFlow es un solo repositorio con dos aplicaciones: una API FastAPI en `backend/` y una interfaz React en `frontend/`. No hay un bus de eventos ni una base compartida en el frontend. La interfaz lee y escribe únicamente por HTTP.

## Capas del backend

| Capa | Ubicación | Responsabilidad |
|---|---|---|
| Entrada HTTP | `backend/main.py` y `backend/routers/` | Rutas, códigos de estado y dependencia de sesión |
| Contratos | `backend/schemas/` | Validación de entrada y forma de la respuesta con Pydantic |
| Dominio | `backend/services/` | Ingesta, conversión, eliminación intercompany, indicadores, aduana y Excel |
| Persistencia | `backend/models/` y `backend/database/connection.py` | Tablas SQLAlchemy y sesión por request |
| Configuración | `backend/core/config.py` | Valores por defecto y variables de entorno |

No hay repositorio separado de los modelos: cada endpoint consulta SQLAlchemy directamente. `main.py` concentra el CRUD de empresas, sucursales y transacciones. Los routers cubren carga de archivos, consolidación, trazabilidad, validación y exportación.

## Capas del frontend

| Capa | Ubicación | Responsabilidad |
|---|---|---|
| Arranque | `frontend/src/main.jsx`, `frontend/index.html` | Monta React |
| Interfaz | `frontend/src/App.jsx` | Navegación interna, vistas y formularios |
| Estilos | `frontend/src/styles.css` | Presentación |
| HTTP | `frontend/src/services.js` | Única función `api()` y cabeceras JSON |

No hay enrutador de URLs, almacén global ni datos simulados. La vista activa vive en el estado `page`.

## Flujo de una consolidación

1. El frontend pide empresas, sucursales, transacciones, el resumen y la auditoría.
2. La API lee `transacciones`.
3. `consolidar_grupo` completa `monto_base` cuando falta, elimina pares intercompany y calcula NOPAT, ROIC, ROCE y EVA.
4. La respuesta vuelve al estado de React. Exportar Excel o CSV repite ese cálculo y devuelve un archivo.

## Lo que esta arquitectura no incluye

- Autenticación y roles. `SECRET_KEY` está reservado y ningún endpoint lo usa.
- Migraciones. Las tablas se crean con `Base.metadata.create_all` al arrancar.
- PostgreSQL. El motor previsto es SQLite local. `psycopg` está en dependencias, pero no hay código que lo configure más allá de aceptar otra `DATABASE_URL`.
