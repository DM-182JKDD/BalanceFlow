# BalanceFlow frontend

Interfaz React para el API de BalanceFlow.

## Desarrollo

```bash
npm install
npm run dev
```

Configura `VITE_API_URL` si el API no está disponible en `http://localhost:8000`.
La aplicación consume `/api/empresas`, `/api/sucursales`, `/api/transacciones`, `/api/uploads/excel`, `/api/consolidacion/resumen`, `/api/validacion`, `/api/trazabilidad/{componente}` y `/api/exportar/excel`.

Copia `.env.example` a `.env` si la API no está en `http://localhost:8000`.
