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
| `transactions` | Transacciones | Búsqueda, filtro y páginas en el servidor, alta, edición, baja y rastro de auditoría |
| `consolidation` | Consolidación | Indicadores, descuadres, desviaciones, aduana y trazabilidad completa |
| `companies` | Empresas | Alta, edición y baja |
| `branches` | Sucursales | Alta, edición y baja |
| `uploads` | Importar | CSV/XLSX/XLS hacia una empresa |
| `reports` | Reportes | Descarga del Excel y conteos ya cargados |
| `settings` | Configuración | Nombre del espacio, moneda, tasas y alta de usuarios. Solo administrador |

`load()` pide en paralelo:

- `GET /api/empresas`
- `GET /api/sucursales`
- `GET /api/transacciones?limit=8&orden=fecha&direccion=desc`
- `GET /api/consolidacion/resumen?moneda_base=`
- `GET /api/validacion`
- `GET /api/configuracion`
- `GET /api/consolidacion/serie`
- `GET /api/consolidacion/desviaciones?dias=30`
- `GET /api/transacciones/conteo`

La vista de transacciones pide su propia página (`limit=50`) con `q`, empresa e intercompany.

Si empresas falla, la barra superior muestra desconexión. El resto de fallos deja esa sección vacía. Un aviso fijo desaparece a los 3,5 segundos.

## Formularios

El modal envía JSON con `POST` o `PATCH`:

- Empresa: `nombre`, `pais`, `moneda_local`, `activa`.
- Sucursal: `empresa_id`, `nombre`, `ciudad`, `activa`.
- Transacción: empresa, sucursal opcional, fecha, cuenta, descripción, monto, moneda, banco, categoría y, si es intercompany, la contraparte.

La carga de archivos usa `FormData` con `archivo`, `empresa_id` y `moneda_default`.

La gráfica pide `serie` con ventana de 30 o 180 días. Los filtros de transacciones se envían al servidor. La búsqueda también.

Los montos de la tabla usan la moneda original del movimiento. Los indicadores usan la moneda base elegida. Un administrador que cambia el selector guarda esa moneda con `PATCH /api/configuracion`.

Sin sesión, la interfaz muestra entrar o crear cuenta. El perfil muestra el nombre y el rol, y permite cerrar sesión. "Contactar soporte" envía `POST /api/soporte`. En Transacciones y en el drill-down, **Rastrear** abre `GET /api/transacciones/{id}/auditoria`.

En pantallas angostas el menú lateral se oculta detrás de un botón y la barra inferior se desplaza para incluir Configuración cuando el rol la ve. Hay enlace para saltar al contenido, la sección activa se marca con `aria-current` y los diálogos anuncian su título. El prototipo Streamlit de `backend/dashboard/app.py` no es esta interfaz.
