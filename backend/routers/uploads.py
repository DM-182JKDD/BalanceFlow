"""
Router de uploads: recibe archivos Excel/CSV, los normaliza con services.ingesta
e inserta las transacciones en la base de datos.
"""
import logging
import os
import re
from datetime import datetime

from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from sqlalchemy.orm import Session

from database.connection import get_db
from models import Empresa, Transaccion
from services.consolidacion import convertir_a_moneda_base
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
    archivo: UploadFile = File(..., description="Archivo CSV, XLSX o XLS"),
    empresa_id: int = Form(..., description="ID de la empresa a la que pertenece el archivo"),
    moneda_default: str = Form("GTQ", description="Moneda por defecto si el archivo no la trae"),
    db: Session = Depends(get_db),
):
    moneda_default = (moneda_default or "GTQ").strip().upper()[:3] or "GTQ"
    # 1. Validar empresa
    emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
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

    # 5. Insertar transacciones en la BD
    insertadas = 0
    errores_insercion = []
    for _, fila in df.iterrows():
        try:
            moneda = str(fila["moneda"])[:3].upper()
            monto = float(fila["monto"])
            marca = str(fila["es_intercompany"] or "N").upper()[:1]
            if marca not in ("S", "N"):
                marca = "N"
            descripcion = fila["descripcion"]
            banco = fila["banco"]
            categoria = fila["categoria"]
            tx = Transaccion(
                empresa_id=int(fila["empresa_id"]),
                sucursal_id=None,
                fecha=fila["fecha"],
                cuenta=str(fila["cuenta"])[:20],
                descripcion=_texto(descripcion, 255),
                monto=monto,
                moneda=moneda,
                monto_base=convertir_a_moneda_base(monto, moneda),
                banco=_texto(banco, 80),
                categoria=_texto(categoria, 80),
                es_intercompany=marca,
                empresa_contraparte_id=_entero_opcional(fila.get("empresa_contraparte_id")),
                archivo_origen=str(fila["archivo_origen"])[:255],
                fila_origen=int(fila["fila_origen"]) if fila["fila_origen"] else None,
            )
            db.add(tx)
            insertadas += 1
        except Exception as e:
            errores_insercion.append({"fila": int(fila["fila_origen"]), "error": str(e)})

    registros = df.to_dict(orient="records")
    for registro in registros:
        fecha = registro.get("fecha")
        if fecha is not None and hasattr(fecha, "isoformat"):
            registro["fecha"] = fecha.isoformat()
        registro["empresa_contraparte_id"] = _entero_opcional(registro.get("empresa_contraparte_id"))
    auditoria = validar_transacciones(registros)

    try:
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
        "errores_insercion": errores_insercion,
        "columnas_detectadas": resultado["columnas_detectadas"],
        "validacion": auditoria,
    }