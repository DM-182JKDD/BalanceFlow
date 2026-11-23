from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from models import Empresa, Sucursal, Transaccion


def grupo_id(request: Request) -> int:
    valor = getattr(request.state, "grupo_id", None)
    if valor is None:
        raise HTTPException(status_code=401, detail="Sesión no válida")
    return int(valor)


def empresa_asignada(request: Request) -> int | None:
    """None ve todas las empresas de su grupo. Un entero solo ve esa empresa."""
    valor = getattr(request.state, "empresa_id", None)
    return int(valor) if valor is not None else None


def exigir_empresa(request: Request, empresa_id: int) -> None:
    propia = empresa_asignada(request)
    if propia is not None and propia != int(empresa_id):
        raise HTTPException(status_code=404, detail="Empresa no encontrada")


def empresa_del_grupo(db: Session, request: Request, empresa_id: int) -> Empresa:
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id, Empresa.grupo_id == grupo_id(request)).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    exigir_empresa(request, empresa.id)
    return empresa


def empresas_visibles(db: Session, request: Request):
    consulta = db.query(Empresa).filter(Empresa.grupo_id == grupo_id(request))
    propia = empresa_asignada(request)
    if propia is not None:
        consulta = consulta.filter(Empresa.id == propia)
    return consulta


def sucursales_visibles(db: Session, request: Request):
    consulta = db.query(Sucursal).join(Empresa, Sucursal.empresa_id == Empresa.id).filter(Empresa.grupo_id == grupo_id(request))
    propia = empresa_asignada(request)
    if propia is not None:
        consulta = consulta.filter(Sucursal.empresa_id == propia)
    return consulta


def transacciones_visibles(db: Session, request: Request):
    consulta = db.query(Transaccion).join(Empresa, Transaccion.empresa_id == Empresa.id).filter(Empresa.grupo_id == grupo_id(request))
    propia = empresa_asignada(request)
    if propia is not None:
        consulta = consulta.filter(Transaccion.empresa_id == propia)
    return consulta
