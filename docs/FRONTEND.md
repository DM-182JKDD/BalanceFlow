# Frontend

Interfaz React en JavaScript, sin TypeScript y sin Tailwind. Vite sirve el proyecto y `@vitejs/plugin-react` compila JSX.

## Dependencias

`frontend/package.json`:

- `react` y `react-dom` ^19.0.0
- `lucide-react` ^0.468.0
- `recharts` ^2.15.0
- desarrollo: `vite` ^6.0.0 y `@vitejs/plugin-react` ^4.3.4

## Arranque

`VITE_API_URL` define la base de la API. Si no existe, `services.js` usa `http://localhost:8000`. El ejemplo está en `frontend/.env.example`. Vite escucha en el puerto 5173 (`frontend/vite.config.js`).

## Estructura

Todo el producto visual está en `frontend/src/App.jsx`. No hay router de rutas: un estado `page` elige la vista.

| Clave | Vista | Qué hace |
|---|---|---|
| `dashboard` | Resumen | KPIs, gráfica por rango, ingresos por empresa y salud del grupo |
| `transactions` | Transacciones | Búsqueda local, filtro por empresa y tipo, alta, edición y baja |
| `consolidation` | Consolidación | Indicadores, descuadres, aduana y trazabilidad |
| `companies` | Empresas | Alta, edición y baja |
| `branches` | Sucursales | Alta, edición y baja |
| `uploads` | Importar | CSV/XLSX/XLS hacia una empresa |
| `reports` | Reportes | Descarga del Excel y conteos ya cargados |

`load()` pide en paralelo:

- `GET /api/empresas`
- `GET /api/sucursales`
- `GET /api/transacciones?limit=500`
- `GET /api/consolidacion/resumen`
- `GET /api/validacion`

Si empresas falla, la barra superior muestra desconexión. El resto de fallos deja esa sección vacía. Un aviso fijo desaparece a los 3,5 segundos.

## Formularios

El modal envía JSON con `POST` o `PATCH`:

- Empresa: `nombre`, `pais`, `moneda_local`, `activa`.
- Sucursal: `empresa_id`, `nombre`, `ciudad`, `activa`.
- Transacción: empresa, sucursal opcional, fecha, cuenta, descripción, monto, moneda, banco, categoría y, si es intercompany, la contraparte.

La carga de archivos usa `FormData` con `archivo`, `empresa_id` y `moneda_default`.

La gráfica de "Últimos 30 días" limita los movimientos a esa ventana. "Últimos 6 meses" agrupa seis meses. Los filtros de transacciones se aplican sobre los datos ya recibidos. La búsqueda también es local.

Los montos de la tabla usan la moneda original del movimiento. Los indicadores del consolidado se muestran en GTQ, que es lo que devuelve la API.

## Lo que la interfaz no hace

- No hay inicio de sesión. El perfil "Equipo financiero / Administrador" es texto fijo.
- "Contactar soporte" solo muestra un aviso con un correo; no envía un mensaje.
- El selector de moneda del resumen no cambia la moneda base.
- No hay paginación: se piden como máximo 500 transacciones.
- El prototipo Streamlit de `backend/dashboard/app.py` no es esta interfaz.
