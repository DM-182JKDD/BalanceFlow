from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.acceso import grupo_id
from database.connection import get_db
from models import Grupo
from services.parametros import contexto, guardar

router = APIRouter(prefix="/api/configuracion", tags=["Configuración"])


class ConfiguracionUpdate(BaseModel):
    nombre_grupo: str | None = Field(None, min_length=1, max_length=120)
    moneda_base: str | None = Field(None, min_length=3, max_length=3)
    wacc: float | None = Field(None, ge=0, le=1)
    tasas: dict[str, float] | None = None


@router.get("")
def obtener(request: Request, db: Session = Depends(get_db)):
    grupo = grupo_id(request)
    tasas, moneda, wacc = contexto(db, grupo)
    nombre = db.query(Grupo.nombre).filter(Grupo.id == grupo).scalar() or ""
    return {"nombre_grupo": nombre, "moneda_base": moneda, "wacc": wacc, "tasas": tasas}


@router.patch("")
def actualizar(payload: ConfiguracionUpdate, request: Request, db: Session = Depends(get_db)):
    grupo = grupo_id(request)
    tasas, moneda_actual, _wacc = contexto(db, grupo)
    if payload.moneda_base and payload.moneda_base.upper() not in tasas and payload.moneda_base.upper() != moneda_actual:
        if not payload.tasas or payload.moneda_base.upper() not in {k.upper() for k in payload.tasas}:
            raise HTTPException(status_code=400, detail="La moneda base no tiene tasa configurada")
    return guardar(db, grupo, payload.moneda_base, payload.wacc, payload.tasas, payload.nombre_grupo)
