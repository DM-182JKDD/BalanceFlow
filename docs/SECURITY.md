# Seguridad

Cada cliente tiene su propio espacio (`grupos`). El registro público crea ese espacio vacío y un administrador. No ve las empresas de otro cliente. Dentro del espacio, un lector consulta todo y el rol `empresa` solo la empresa asignada. Crear, editar y borrar exige rol `admin`. Las contraseñas usan PBKDF2 y el token HMAC viaja en `Authorization: Bearer`.

## Controles que sí existen

- Esquemas Pydantic con longitudes, tipos y el patrón `S`/`N` en intercompany.
- La sucursal de una transacción debe pertenecer a la empresa indicada.
- La contraparte de una transacción creada o editada por JSON debe existir y ser distinta.
- CORS limitado a los orígenes configurados. El comodín `*` ya no es el valor por defecto y no se combina con credenciales.
- `/health` responde si la base contesta y no incluye `DATABASE_URL`.
- La carga rechaza extensiones distintas de `.csv`, `.xlsx` y `.xls`, rechaza archivos de más de 10 MB y guarda solo un nombre saneado (basename, sin rutas).
- La ruta del archivo guardado no sale en la respuesta.
- Los errores 500 de la carga no devuelven la excepción interna. Quedan en el log `balanceflow.uploads`.
- `monto_base` lo calcula el servidor. El cliente no puede fijarlo en el alta ni en la edición JSON.
- `DEBUG` por defecto es falso, así que el motor no vuelca SQL.
- `.gitignore` excluye `.env`, la base SQLite local, `node_modules` y cachés de Python.

## Hallazgos de la auditoría y estado

| Hallazgo | Estado |
|---|---|
| `routers/exportacion.py` tenía marcadores de conflicto y la API no importaba | Corregido. Conviven Excel y CSV |
| `/health` devolvía la cadena de conexión | Corregido |
| CORS `*` con `allow_credentials` | Corregido. Orígenes explícitos |
| Nombre de archivo de carga usable como ruta | Corregido |
| Excepciones internas devueltas al cliente en la carga | Corregido en los 500 |
| `monto_base` aceptado del cliente | Corregido en JSON. La importación lo calcula |
| Secretos de JWT en el código | `SECRET_KEY` firma el token. El valor por defecto no debe usarse fuera de local |
| Base SQLite y `__pycache__` versionados en `main` | Dejan de rastrearse en esta rama |
| Sin autenticación ni control de acceso por recurso | Corregido. Registro, roles `admin`, `lector` y `empresa`, y escritura reservada al administrador |
| `empresa_contraparte_id` sin clave foránea y sin validar en la importación | La importación anula una contraparte inexistente y la lista. Sigue sin clave foránea |
| Importes en `Float` | El cálculo redondea a centavos con `Decimal`. La columna sigue siendo `Float` |
| Sin límite de tasa de peticiones | Pendiente |
| El servicio de validación no impide insertar filas con errores | Las filas `CRITICO` quedan en cuarentena y no se insertan |
| `dashboard/app.py` apunta a endpoints inexistentes | El prototipo ahora entra por `/api/auth/login` y lee el resumen real |
| Tasas y WACC fijos en código | Semilla inicial. Se leen y se cambian en `tasas_cambio` y `parametros` |

No hay consultas construidas por concatenar texto del usuario. Los filtros usan el ORM. El token no se renueva solo: al expirar, o ante un 401, la interfaz borra la sesión.
