# Contrato API

Base: `VITE_API_URL` o `http://localhost:8000`. Cuerpos JSON usan `Content-Type: application/json`. No hay token ni cookie de sesión. CORS permite los orígenes de `ALLOWED_ORIGINS`, con credenciales, métodos `GET`, `POST`, `PATCH`, `DELETE` y `OPTIONS`.

Los errores de validación de Pydantic responden 422 con `detail` como lista. `services.js` junta los campos `msg`. Los errores de negocio usan `detail` como texto. Un 204 no tiene cuerpo.

## Empresas

Crear y actualizar:

```json
{ "nombre": "Norte", "pais": "Guatemala", "moneda_local": "GTQ", "activa": true }
```

`moneda_local` tiene longitud 3. Respuesta: esos campos más `id` y `creada_en`.

## Sucursales

```json
{ "empresa_id": 1, "nombre": "Central", "ciudad": "Guatemala", "activa": true }
```

Actualizar no cambia `empresa_id`. Respuesta: esos campos más `id` y `creada_en`.

## Transacciones

Crear:

```json
{
  "empresa_id": 1,
  "sucursal_id": 1,
  "fecha": "2026-11-01",
  "cuenta": "4100",
  "descripcion": "Venta",
  "monto": 100,
  "moneda": "USD",
  "banco": null,
  "categoria": "Ventas",
  "es_intercompany": "S",
  "empresa_contraparte_id": 2
}
```

`es_intercompany` solo acepta `S` o `N`. `monto_base` lo calcula el servidor y se ignora si el cliente lo envía. La sucursal, cuando viene, debe pertenecer a la empresa. La contraparte debe ser otra empresa existente.

Actualizar acepta cualquier subconjunto de esos campos, excepto `monto_base`, `archivo_origen` y `fila_origen`.

## Carga

`POST /api/uploads/excel` como `multipart/form-data`:

| Campo | Tipo | Regla |
|---|---|---|
| `archivo` | archivo | `.csv`, `.xlsx`, `.xls`, máximo 10 MB |
| `empresa_id` | entero | debe existir |
| `moneda_default` | texto | 3 caracteres; `GTQ` si falta |

Respuesta 200:

```json
{
  "status": "success",
  "archivo": "movimientos.csv",
  "empresa_id": 1,
  "filas_leidas": 3,
  "filas_validas": 3,
  "filas_descartadas": 0,
  "transacciones_insertadas": 3,
  "errores_insercion": [],
  "columnas_detectadas": ["fecha", "cuenta", "monto"],
  "validacion": { "estado": "LIMPIO", "errores": [], "alertas": [], "resumen": {} }
}
```

La ruta interna del archivo no se devuelve. Las filas válidas se insertan aunque la aduana marque errores: `validacion` informa, no bloquea.

Columnas reconocidas por alias: `fecha`, `cuenta`, `monto` (obligatorias), y opcionales `descripcion`, `moneda`, `sucursal`, `banco`, `categoria`, `es_intercompany`, `empresa_contraparte`. La columna de sucursal se detecta y no se persiste: la transacción queda sin `sucursal_id`.

## Consolidación

`GET /api/consolidacion/resumen` devuelve `consolidado`, `por_empresa`, `intercompany`, `total_transacciones_originales` y `total_transacciones_limpias`.

`consolidado` incluye `moneda_base`, `empresas_incluidas`, `total_ingresos`, `total_gastos`, `total_nopat`, `total_capital_invertido`, `roic_grupo` y `eva_grupo`.

Cada empresa incluye `ingresos`, `gastos`, `nopat`, `capital_invertido`, `roic`, `roce`, `eva` y `wacc`.

`intercompany.resumen` cuenta `eliminadas` y `descuadres`. Cada descuadre trae `tipo`, `mensaje` y `datos`.

## Trazabilidad

`GET /api/trazabilidad/ingresos?empresa_id=1`

```json
{
  "componente": "ingresos",
  "empresa_id": 1,
  "total_registros": 1,
  "total_gtq": 100.0,
  "registros": [
    {
      "id": 1,
      "empresa_id": 1,
      "fecha": "2026-11-01",
      "cuenta": "4100",
      "descripcion": "Venta",
      "monto_original": 100,
      "moneda": "GTQ",
      "tasa_aplicada": 1.0,
      "monto_gtq": 100,
      "es_intercompany": "N"
    }
  ],
  "intercompany_eliminadas": []
}
```

## Validación

`GET /api/validacion` devuelve `estado`, `total_registros`, `errores`, `alertas` y `resumen` (`criticos`, `advertencias`, `total_alertas`).

Tipos de error presentes en el servicio: `MONEDA_INVALIDA`, `CUENTA_HUERFANA`, `INGRESO_NEGATIVO`, `DUPLICADO`, `INTERCOMPANY_SIN_CONTRAPARTE`, `INTERCOMPANY_ASIMETRICO`. `GASTO_POSITIVO` es alerta.

## Exportación

- `GET /api/exportar/excel`: libro con hojas Consolidado, Por empresa, Eliminaciones, Descuadres y Movimientos.
- `GET /api/exportacion/csv`: transacciones que quedan después de eliminar pares intercompany.
