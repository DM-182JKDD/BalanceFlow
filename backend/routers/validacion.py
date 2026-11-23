"""Aduana financiera sobre las transacciones ya persistidas."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.connection import get_db
from models import Transaccion
from services.validacion import validar_transacciones

router = APIRouter(prefix="/api/validacion", tags=["Validación"])


def _serializar(tx: Transaccion) -> dict:
    fila = {col.name: getattr(tx, col.name) for col in tx.__table__.columns}
    if fila.get("fecha") is not None:
        fila["fecha"] = str(fila["fecha"])
    creada = fila.get("creada_en")
    if creada is not None and hasattr(creada, "isoformat"):
        fila["creada_en"] = creada.isoformat()
    return fila


@router.get("", summary="Auditar transacciones cargadas")
def auditar(empresa_id: int | None = None, db: Session = Depends(get_db)):
    consulta = db.query(Transaccion)
    if empresa_id is not None:
        consulta = consulta.filter(Transaccion.empresa_id == empresa_id)
    return validar_transacciones([_serializar(tx) for tx in consulta.all()])
