# BalanceFlow

**Consolidación financiera multiempresa que se adapta a cómo trabaja cada empresa.**

BalanceFlow es un backend (API REST) que toma la información financiera de varias empresas de un mismo grupo, aunque estén en distintos países, monedas y formatos, y la convierte en un único número confiable para el grupo: sin sumas manuales, sin ventas internas contadas doble y con cada cifra rastreable hasta el registro que la originó.

> Proyecto desarrollado para **Build & Pitch** (track Accounting: consolidación multiempresa), UVG, 21 de noviembre de 2026.

---

## ¿Qué problema resuelve?

Un grupo con varias empresas ya presupuesta bien cada área por separado. Lo que falla es juntar todo:

| Problema | Cómo lo resuelve BalanceFlow |
|---|---|
| Consolidación manual, cada empresa con su formato | Importación y normalización de datos a un esquema único |
| Ventas entre empresas del grupo se cuentan doble | Cruce automático de operaciones intercompany y eliminación de pares |
| Varias monedas sin tasa común | Conversión a la moneda base del grupo, con tasas guardadas y editables |
| ROIC, ROCE y EVA copiados a mano | Cálculo automático desde los registros |
| Cifras que cambian sin explicación | Drill-down del consolidado y un rastro por movimiento: alta, edición, baja y archivo de origen |
| Errores que entran al número del grupo | Datos con errores sembrados para probar la detección de inconsistencias |

**Principio de diseño:** adaptarse a la empresa, no obligar a la empresa a adaptarse al software. BalanceFlow no reemplaza ERP, Excel ni procesos existentes: funciona como una capa de integración y automatización encima de ellos.

---

## Funcionalidades

- **Servicio multi-cliente:** el registro público crea un espacio vacío. Cada cliente configura su nombre, moneda, tasas, empresas y usuarios. Los datos de un espacio no se mezclan con los de otro.
- **Gestión multiempresa y multisucursal:** CRUD de empresas, sucursales y transacciones dentro del espacio.
- **Conversión de monedas** a la moneda base del grupo (GTQ al empezar). Monedas no reconocidas no rompen la consolidación.
- **Eliminación de intercompany:** empareja venta y compra espejo (en la moneda del grupo, con tolerancia de 1) y reporta los descuadres.
- **Indicadores financieros por empresa y por grupo:** NOPAT, capital invertido, ROIC, ROCE y EVA.
- **Trazabilidad:** el consolidado abre ingresos, gastos, activos y pasivos hasta cada movimiento. Cada transacción guarda quién la creó, importó, editó o eliminó.
- **Exportación** del consolidado a Excel y CSV.
- **Acceso:** administrador del espacio, lector de todo el espacio, o usuario limitado a una empresa.
- **Cuarentena** de filas críticas en la carga, sin insertarlas.
- **Carga de archivos** (Excel/CSV) mediante el router de `uploads`.
- **Interfaz React** con entrada, configuración, rastro de auditoría y navegación usable en pantallas angostas.
- **CORS configurado** para el frontend local.
- **Documentación interactiva** automática con Swagger en `/docs`.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| API | Python, FastAPI, Uvicorn |
| Validación | Pydantic |
| Persistencia | SQLAlchemy. PostgreSQL en local (`127.0.0.1:5433`). Las pruebas automáticas usan SQLite |
| Procesamiento | Pandas, OpenPyXL |
| Frontend | React, Vite y CSS propio |

---

## Estructura del proyecto

```
BalanceFlow/
├── backend/
│   ├── main.py                  # App FastAPI, CORS, sesión y CRUD
│   ├── seed.py                  # Datos del grupo Demostración
│   ├── .env.example             # SECRET_KEY, admin inicial y DATABASE_URL
│   ├── models/                  # Grupo, Empresa, Sucursal, Transaccion, Usuario, auditoría
│   ├── schemas/                 # Esquemas Pydantic
│   ├── core/                    # Configuración, token HMAC y alcance por grupo
│   ├── database/                # Conexión y arranque (grupo, tasas, admin)
│   ├── routers/                 # Auth, carga, consolidación, trazabilidad, exportación, soporte
│   └── services/                # Consolidación, parámetros y rastro de auditoría
└── frontend/                    # React, Vite y CSS. Sesión en sessionStorage
```

---

## Requisitos previos

- **Python 3.12 o superior** (recomendado 3.12 o 3.13 para máxima compatibilidad de librerías).
- **Git**.
- Windows, macOS o Linux. Los ejemplos usan PowerShell (Windows).

> En Windows, durante la instalación de Python marca **"Add python.exe to PATH"**.

---

## Instalación

### 1. Clonar el repositorio

```powershell
git clone https://github.com/DM-182JKDD/BalanceFlow.git
cd BalanceFlow\backend
```

### 2. Crear y activar el entorno virtual

**Windows (PowerShell):**
```powershell
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

Sabrás que está activo porque verás `(venv)` al inicio de la línea.

### 3. Instalar dependencias

```powershell
pip install fastapi uvicorn sqlalchemy pandas openpyxl python-multipart pydantic pydantic-settings
```

Con el archivo del repositorio:

```powershell
pip install -r requirements.txt
copy .env.example .env
```

En `.env` define `SECRET_KEY`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` y `DATABASE_URL`. El ejemplo usa SQLite. La prueba local de este equipo usa PostgreSQL en `127.0.0.1:5433` (`postgresql+psycopg://...`). El clúster de datos no se versiona.

### 4. Cargar datos de prueba

```powershell
python seed.py
```

Esto crea las tablas y puebla la base con datos ficticios. Resultado esperado:

```
Empresas: 6
Sucursales: 7
Transacciones: 72
```

> Detén el servidor antes de ejecutar el seed. Solo borra y recrea el grupo llamado **Demostración**. No toca los espacios creados por registro.

---

## Cómo correrlo

```powershell
uvicorn main:app --reload
```

| URL | Para qué |
|---|---|
| http://127.0.0.1:8000 | Estado del servicio |
| http://127.0.0.1:8000/docs | Documentación interactiva (Swagger), ideal para probar |
| http://127.0.0.1:8000/health | Verificación de salud y conexión a la base |

---

## Cómo se usa

### Flujo típico

1. **Entrar o crear un espacio** en http://localhost:5173. El registro deja el espacio vacío. El primer arranque de una base vacía crea el administrador de `.env`.
2. **Configurar** nombre, moneda, tasas y usuarios (administrador, lector o una sola empresa).
3. **Cargar datos** por la interfaz, la API o `seed.py` para el grupo de demostración.
4. **Consolidar:** `GET /api/consolidacion/resumen` convierte monedas, elimina intercompany y calcula indicadores.
5. **Auditar:** `GET /api/trazabilidad/{componente}` explica una cifra. `GET /api/transacciones/{id}/auditoria` muestra la historia de ese movimiento, también si ya se eliminó.
6. **Exportar:** `GET /api/exportacion/csv` descarga el consolidado limpio.

### Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/empresas` | Lista de empresas |
| POST | `/api/empresas` | Crear empresa |
| GET/PATCH/DELETE | `/api/empresas/{id}` | Consultar, actualizar, eliminar |
| GET/POST | `/api/sucursales` | Listar (filtro `empresa_id`) / crear |
| GET/POST | `/api/transacciones` | Listar paginado (`q`, `offset`, `limit`) / crear. Requiere token |
| GET | `/api/consolidacion/resumen` | Consolidado del grupo, por empresa e intercompany |
| GET | `/api/trazabilidad/{componente}` | Drill-down. `componente`: `ingresos`, `gastos`, `activos`, `pasivos`. Filtro opcional `empresa_id` |
| GET | `/api/exportar/excel` | Descarga Excel del consolidado |
| GET | `/api/exportacion/csv` | Descarga CSV del consolidado limpio |
| GET | `/api/validacion` | Aduana sobre las transacciones guardadas |
| PATCH | `/api/transacciones/{id}` | Actualizar una transacción |
| POST | `/api/auth/login` | Iniciar sesión |
| POST | `/api/auth/registro` | Crear un espacio vacío y su administrador |
| POST | `/api/auth/usuarios` | Alta de admin, lector o usuario de una empresa |
| GET | `/api/transacciones/{id}/auditoria` | Historia del movimiento |
| GET/PATCH | `/api/configuracion` | Nombre del espacio, moneda base, WACC y tasas |
| POST | `/api/soporte` | Registrar un mensaje de soporte |

### Ejemplos

```powershell
# Primero inicia sesión y usa el token en las demás llamadas
curl -X POST http://127.0.0.1:8000/api/auth/login -H "Content-Type: application/json" -d "{\"email\":\"admin@balanceflow.local\",\"password\":\"tu-clave\"}"

# Consolidado del grupo
curl -H "Authorization: Bearer TOKEN" http://127.0.0.1:8000/api/consolidacion/resumen

# De qué transacciones salen los ingresos de la empresa 1
curl "http://127.0.0.1:8000/api/trazabilidad/ingresos?empresa_id=1"

# Descargar el consolidado
curl -o consolidado.csv http://127.0.0.1:8000/api/exportacion/csv
```

---

## Cómo se calculan los indicadores

Fórmulas simplificadas para el prototipo, por empresa y a nivel grupo, en la moneda base configurada:

```
NOPAT              = Ingresos (cuentas 4xxx) − Gastos (cuentas 5xxx)
Capital invertido  = Activos (1xxx) − Pasivos (2xxx)
ROIC               = NOPAT / Capital invertido
ROCE               = EBIT / Capital empleado
EVA                = NOPAT − (Capital invertido × WACC)
```

- **WACC:** 10% al inicio. Se cambia en `PATCH /api/configuracion`.
- **Tasas de cambio** ficticias, definidas en `services/consolidacion.py` (`TASAS_CAMBIO`): USD 7.85, MXN 0.45, CRC 0.015, HNL 0.32, entre otras.
- **Intercompany:** dos transacciones forman un par si cada una apunta a la otra como contraparte y su monto en la moneda del grupo (valor absoluto) difiere en 1 o menos. Los pares se eliminan; lo que no cuadra se conserva y se reporta como descuadre.

---

## Datos de demostración

El seed genera un grupo ficticio: **6 empresas** (Guatemala, Costa Rica, México, Honduras, El Salvador, Panamá) en varias monedas, con transacciones de balance, operativas e intercompany. Incluye **errores sembrados a propósito**:

1. Transacción duplicada exacta.
2. Moneda inválida (`XYZ`).
3. Ingreso con signo invertido.
4. Intercompany sin contraparte.
5. Cuenta inexistente (`9999`).

No contiene ningún dato real.

---

## Solución de problemas

| Error | Causa y solución |
|---|---|
| `ImportError: cannot import name '...' from 'routers'` | Falta un archivo en `routers/` (`uploads`, `consolidacion`, `trazabilidad` o `exportacion`) |
| `ModuleNotFoundError` | El entorno virtual no está activo o faltan dependencias |
| `database is locked` | El servidor estaba corriendo mientras se ejecutaba `seed.py` |
| `python` abre la Microsoft Store | Python no está en el PATH; reinstálalo marcando "Add python.exe to PATH" |
| Error de ejecución de scripts en PowerShell | Ejecuta `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` |

---

## Despliegue

- **Demo rápida:** exponer el servidor local con un túnel (`cloudflared tunnel --url http://localhost:8000` o `ngrok http 8000`).
- **Hosting:** Render para el backend y Vercel para el frontend. Comando de inicio:
  ```
  uvicorn main:app --host 0.0.0.0 --port $PORT
  ```
  Recuerda agregar la URL del frontend a `ALLOWED_ORIGINS` (CORS). En planes gratuitos el disco es efímero, por lo que SQLite debe sembrarse al arrancar o migrarse a PostgreSQL.

---

## Hoja de ruta

- [x] Aduana en la carga: las filas críticas quedan en cuarentena y no se insertan.
- [x] Explicación de desviaciones en `GET /api/consolidacion/desviaciones` y en la consolidación.
- [x] Control de acceso: registro público, administrador, lector y usuario de una empresa.
- [x] Rastro de auditoría por transacción.
- [x] PostgreSQL para la prueba local. Las pruebas automáticas siguen en SQLite. No hay Alembic.
- [ ] Captura digital de documentos físicos (OCR).
- [ ] Integración con APIs bancarias y sistemas contables.
- [ ] Tasas de cambio oficiales por periodo.

---

## Equipo

Proyecto de Build & Pitch desarrollado por un equipo de dos personas: backend y motor financiero (Python / FastAPI) y frontend / experiencia de usuario (React).

## Licencia

Proyecto de hackathon con datos ficticios. Define la licencia antes de publicarlo de forma abierta.
