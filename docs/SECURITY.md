# Seguridad

No hay usuarios, contraseñas ni autorización. Cualquier cliente que alcance la API puede leer, crear, editar, borrar y exportar todo el grupo. El perfil de la interfaz no representa un permiso.

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
| Secretos de JWT en el código | El valor por defecto ya no es una clave usable. Sigue sin haber autenticación, así que no firma nada |
| Base SQLite y `__pycache__` versionados en `main` | Dejan de rastrearse en esta rama |
| Sin autenticación ni control de acceso por recurso | Pendiente. No se inventó un login porque la interfaz no tiene ese flujo |
| `empresa_contraparte_id` sin clave foránea y sin validar en la importación | Pendiente en la importación |
| Importes en `Float` | Pendiente. Cambiarlo exige una migración que este esquema no tiene |
| Sin límite de tasa de peticiones | Pendiente |
| El servicio de validación no impide insertar filas con errores | Comportamiento actual, visible en la respuesta. La cuarentena sigue fuera de alcance |
| `dashboard/app.py` apunta a endpoints inexistentes | Sigue siendo un prototipo desconectado. La interfaz real es React |
| Tasas y WACC fijos en código | Dato de demostración, no un secreto |

No hay consultas construidas por concatenar texto del usuario. Los filtros usan el ORM. Aun así, la API no distingue a un usuario de otro: el control de acceso ausente es el riesgo principal.
