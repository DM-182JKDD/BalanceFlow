# BalanceFlow frontend

Interfaz React para el API de BalanceFlow.

## Desarrollo

```bash
npm install
npm run dev
```

Configura `VITE_API_URL` si el API no está disponible en `http://localhost:8000`.
La aplicación consume las rutas `/api/empresas`, `/api/sucursales`, `/api/transacciones`, `/api/uploads/excel` y `/api/consolidacion/resumen`.

La descarga de reportes requiere que el backend exponga `/api/exportar/excel`.
