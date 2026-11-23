"""
Router de uploads: recibe archivos Excel/CSV, los normaliza con services.ingesta
e inserta las transacciones en la base de datos.
"""
import logging
import os
import re
from datetime import datetime

from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, Request

from core.acceso import empresa_del_grupo, grupo_id
from sqlalchemy.orm import Session

from database.connection import get_db
from models import Empresa, Sucursal, Transaccion
from services.consolidacion import convertir_a_moneda_base
from services.auditoria import registrar_evento
from services.parametros import contexto
from services.ingesta import procesar_archivo, ErrorIngesta
from services.validacion import validar_transacciones

logger = logging.getLogger("balanceflow.uploads")

router = APIRouter(prefix="/api/uploads", tags=["Uploads"])

# Carpeta donde se guardan los archivos subidos
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Extensiones permitidas
EXTENSIONES_PERMITIDAS = {".csv", ".xlsx", ".xls"}
TAMANO_MAXIMO_BYTES = 10 * 1024 * 1024


def _nombre_seguro(nombre: str) -> str:
    base = os.path.basename(nombre or "archivo")
    limpio = re.sub(r"[^A-Za-z0-9._-]", "_", base).strip("._")
    return limpio or "archivo"


def _entero_opcional(valor):
    if valor is None:
        return None
    if isinstance(valor, float) and valor != valor:
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _texto(valor, limite):
    if valor is None or (isinstance(valor, float) and valor != valor):
        return None
    texto = str(valor).strip()
    if not texto or texto.lower() == "nan":
        return None
    return texto[:limite]


@router.post("/excel", summary="Subir Excel/CSV y cargar transacciones")
async def subir_archivo(
    request: Request,
    archivo: UploadFile = File(..., description="Archivo CSV, XLSX o XLS"),
    empresa_id: int = Form(..., description="ID de la empresa a la que pertenece el archivo"),
    moneda_default: str = Form("GTQ", description="Moneda por defecto si el archivo no la trae"),
    db: Session = Depends(get_db),
):
    moneda_default = (moneda_default or "GTQ").strip().upper()[:3] or "GTQ"
    emp = empresa_del_grupo(db, request, empresa_id)
    if not emp:
        raise HTTPException(status_code=400, detail=f"Empresa con id={empresa_id} no existe")

    # 2. Validar extensión y tamaño. El nombre se reduce al basename saneado.
    nombre_original = _nombre_seguro(archivo.filename or "archivo")
    ext = os.path.splitext(nombre_original)[1].lower()
    if ext not in EXTENSIONES_PERMITIDAS:
        raise HTTPException(
            status_code=400,
            detail=f"Extensión {ext or '(sin extensión)'} no permitida. Usa: {sorted(EXTENSIONES_PERMITIDAS)}",
        )

    contenido = await archivo.read()
    if len(contenido) > TAMANO_MAXIMO_BYTES:
        raise HTTPException(status_code=413, detail="El archivo supera el máximo de 10 MB.")
    if not contenido:
        raise HTTPException(status_code=400, detail="El archivo está vacío.")

    # 3. Guardar el archivo en uploads/
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_guardado = f"{empresa_id}_{timestamp}_{nombre_original}"
    ruta_destino = os.path.join(UPLOAD_DIR, nombre_guardado)

    try:
        with open(ruta_destino, "wb") as buffer:
            buffer.write(contenido)
    except Exception:
        logger.exception("No se pudo guardar el archivo de carga")
        raise HTTPException(status_code=500, detail="No se pudo guardar el archivo.")

    # 4. Procesar con el servicio de ingesta
    try:
        resultado = procesar_archivo(
            ruta_destino,
            empresa_id=empresa_id,
            moneda_default=moneda_default,
        )
    except ErrorIngesta as e:
        raise HTTPException(status_code=422, detail=f"Error de ingesta: {str(e)}")
    except Exception:
        logger.exception("Fallo al procesar el archivo de carga")
        raise HTTPException(status_code=500, detail="No se pudo procesar el archivo.")

    df = resultado["dataframe"]

    if df.empty:
        raise HTTPException(
            status_code=422,
            detail="El archivo no contiene filas válidas para insertar.",
        )

    registros = df.to_dict(orient="records")
    for registro in registros:
        fecha = registro.get("fecha")
        if fecha is not None and hasattr(fecha, "isoformat"):
            registro["fecha"] = fecha.isoformat()
        registro["empresa_contraparte_id"] = _entero_opcional(registro.get("empresa_contraparte_id"))
    auditoria = validar_transacciones(registros)
    criticas = set()
    for hallazgo in auditoria["errores"]:
        if hallazgo.get("severidad") != "CRITICO":
            continue
        if hallazgo.get("fila") is not None:
            criticas.add(int(hallazgo["fila"]))
        for numero in (hallazgo.get("datos") or {}).get("filas_duplicadas") or []:
            criticas.add(int(numero))

    empresas_validas = {fila[0] for fila in db.query(Empresa.id).all()}
    sucursales = {
        suc.nombre.strip().lower(): suc.id
        for suc in db.query(Sucursal).filter(Sucursal.empresa_id == empresa_id).all()
    }
    tasas, moneda_grupo, _wacc = contexto(db, grupo_id(request))
    contrapartes_invalidas = []

    # 5. Insertar solo las filas que la aduana no marcó como críticas.
    insertadas = 0
    en_cuarentena = 0
    errores_insercion = []
    nuevas = []
    for _, fila in df.iterrows():
        if int(fila["fila_origen"]) in criticas:
            en_cuarentena += 1
            continue
        try:
            moneda = str(fila["moneda"])[:3].upper()
            monto = float(fila["monto"])
            contraparte = _entero_opcional(fila.get("empresa_contraparte_id"))
            if contraparte is not None and contraparte not in empresas_validas:
                contrapartes_invalidas.append(int(fila["fila_origen"]))
                contraparte = None
            nombre_sucursal = _texto(fila.get("sucursal_nombre"), 120)
            sucursal_id = sucursales.get(nombre_sucursal.lower()) if nombre_sucursal else None
            marca = str(fila["es_intercompany"] or "N").upper()[:1]
            if marca not in ("S", "N"):
                marca = "N"
            descripcion = fila["descripcion"]
            banco = fila["banco"]
            categoria = fila["categoria"]
            tx = Transaccion(
                empresa_id=int(fila["empresa_id"]),
                sucursal_id=sucursal_id,
                fecha=fila["fecha"],
                cuenta=str(fila["cuenta"])[:20],
                descripcion=_texto(descripcion, 255),
                monto=monto,
                moneda=moneda,
                monto_base=convertir_a_moneda_base(monto, moneda, tasas, moneda_grupo),
                banco=_texto(banco, 80),
                categoria=_texto(categoria, 80),
                es_intercompany=marca,
                empresa_contraparte_id=contraparte,
                archivo_origen=str(fila["archivo_origen"])[:255],
                fila_origen=int(fila["fila_origen"]) if fila["fila_origen"] else None,
            )
            db.add(tx)
            insertadas += 1
            nuevas.append(tx)
        except Exception:
            logger.exception("Fila de importación descartada")
            errores_insercion.append({"fila": int(fila["fila_origen"]), "error": "No se pudo registrar la fila"})

    try:
        db.flush()
        for tx in nuevas:
            registrar_evento(db, request, tx, "importada")
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Fallo al guardar transacciones importadas")
        raise HTTPException(status_code=500, detail="No se pudieron guardar las transacciones.")

    return {
        "status": "success",
        "archivo": nombre_original,
        "empresa_id": empresa_id,
        "filas_leidas": resultado["filas_leidas"],
        "filas_validas": resultado["filas_validas"],
        "filas_descartadas": resultado["filas_descartadas"],
        "transacciones_insertadas": insertadas,
        "filas_en_cuarentena": en_cuarentena,
        "contrapartes_no_reconocidas": contrapartes_invalidas,
        "errores_insercion": errores_insercion,
        "columnas_detectadas": resultado["columnas_detectadas"],
        "validacion": auditoria,
    }