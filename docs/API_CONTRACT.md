# Contrato API

Base: `VITE_API_URL` o `http://localhost:8000`. Cuerpos JSON usan `Content-Type: application/json`. Salvo `POST /api/auth/login`, `/`, `/health` y la documentación, cada petición lleva `Authorization: Bearer`. CORS permite los orígenes de `ALLOWED_ORIGINS`, con credenciales, métodos `GET`, `POST`, `PATCH`, `DELETE` y `OPTIONS`.

Un token válido de cualquier rol puede leer. Crear, editar y borrar exige rol `admin`. `POST /api/soporte` lo puede enviar un lector. Sin token la API responde 401. Un lector que escribe recibe 403.

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

`GET /api/transacciones` responde un objeto, no una lista:

```json
{ "items": [], "total": 0, "offset": 0, "limit": 50 }
```

Filtros: `empresa_id`, `sucursal_id`, `q`, `es_intercompany` (`S` o `N`). Orden: `orden` (`fecha`, `monto` o `id`) y `direccion` (`asc` o `desc`). `limit` va de 1 a 200 y el valor por defecto es 50. `offset` no puede ser negativo.

`GET /api/transacciones/conteo` responde `{ "por_empresa": { "1": 12 } }`.

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

La ruta interna del archivo no se devuelve. Las filas que la aduana marca como `CRITICO` no se insertan: quedan en `filas_en_cuarentena`. Una contraparte que no existe se guarda como nula y su fila aparece en `contrapartes_no_reconocidas`. Si el nombre de sucursal coincide con una sucursal de esa empresa, se guarda `sucursal_id`.

Columnas reconocidas por alias: `fecha`, `cuenta`, `monto` (obligatorias), y opcionales `descripcion`, `moneda`, `sucursal`, `banco`, `categoria`, `es_intercompany`, `empresa_contraparte`.

## Consolidación

`GET /api/consolidacion/resumen?moneda_base=USD` devuelve `consolidado`, `por_empresa`, `intercompany`, `total_transacciones_originales` y `total_transacciones_limpias`. Sin transacciones responde 200 con un consolidado en cero. La misma consulta de moneda aplica a `por-empresa`, `intercompany`, `serie` y `desviaciones`.

`GET /api/consolidacion/serie?ventana=30` devuelve `moneda_base` y `puntos` (`mes`, `ingresos`, `gastos`). `ventana` va de 1 a 730 días.

`GET /api/consolidacion/desviaciones?dias=30` compara ese tramo con el tramo anterior y devuelve `explicaciones` y `total_cambios`. `dias` va de 1 a 365.

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
      "es_intercompany": "N",
      "archivo_origen": null,
      "fila_origen": null,
      "creada_en": ""
    }
  ],
  "intercompany_eliminadas": []
}
```

`GET /api/transacciones/{id}/auditoria` devuelve `transaccion_id`, `eliminada`, `transaccion` (null si ya se borró) y `eventos`. Cada evento trae `accion` (`creada`, `importada`, `editada`, `eliminada`), `creado_en`, `usuario` (`id`, `nombre`, `email` o null) y `detalle`. En un alta, `detalle.registro` es la foto del movimiento y `detalle.origen` trae `archivo` y `fila`. En una edición, `detalle.cambios` lista cada campo con `antes` y `despues`. En una baja, `detalle.registro` conserva la última foto. Un usuario de empresa solo consulta movimientos de la suya.

## Validación

`GET /api/validacion` devuelve `estado`, `total_registros`, `errores`, `alertas` y `resumen` (`criticos`, `advertencias`, `total_alertas`).

Tipos de error presentes en el servicio: `MONEDA_INVALIDA`, `CUENTA_HUERFANA`, `INGRESO_NEGATIVO`, `DUPLICADO`, `INTERCOMPANY_SIN_CONTRAPARTE`, `INTERCOMPANY_ASIMETRICO`. `GASTO_POSITIVO` es alerta.

## Exportación

- `GET /api/exportar/excel`: libro con hojas Consolidado, Por empresa, Eliminaciones, Descuadres y Movimientos. Sin movimientos responde 200 con el consolidado vacío.
- `GET /api/exportacion/csv`: transacciones que quedan después de eliminar pares intercompany.

## Sesión, parámetros y soporte

`POST /api/auth/login` con `{ "email", "password" }` (mínimo 8 caracteres) devuelve `access_token`, `token_type` y `usuario` (`id`, `email`, `nombre`, `rol`).

`POST /api/auth/usuarios` es solo para un administrador: `{ "email", "nombre", "password", "rol" }` con `rol` `admin` o `lector`. Si el correo ya existe responde 409.

`GET /api/configuracion` devuelve `moneda_base`, `wacc` y `tasas` (unidades de GTQ por cada moneda). `PATCH /api/configuracion` acepta `moneda_base`, `wacc` (entre 0 y 1) y `tasas`. La moneda base tiene que existir en las tasas.

`POST /api/soporte` con `{ "mensaje" }` (5 a 1000 caracteres) responde 201 `{ "id", "mensaje" }`.
