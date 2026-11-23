import json
from datetime import date, datetime

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from core.acceso import empresa_asignada, grupo_id, transacciones_visibles
from models import Empresa, EventoAuditoria, Transaccion, Usuario

CAMPOS = (
    "empresa_id",
    "sucursal_id",
    "fecha",
    "cuenta",
    "descripcion",
    "monto",
    "moneda",
    "monto_base",
    "banco",
    "categoria",
    "es_intercompany",
    "empresa_contraparte_id",
    "archivo_origen",
    "fila_origen",
)


def _valor(valor):
    if isinstance(valor, datetime):
        return valor.isoformat()
    if isinstance(valor, date):
        return valor.isoformat()
    if isinstance(valor, float):
        return round(valor, 2)
    return valor


def foto(tx: Transaccion) -> dict:
    return {campo: _valor(getattr(tx, campo)) for campo in CAMPOS}


def registrar_evento(db: Session, request: Request, tx: Transaccion, accion: str, antes: dict | None = None, cuando: datetime | None = None) -> None:
    """Agrega un hecho. Quien llama hace el commit."""
    despues = None if accion == "eliminada" else foto(tx)
    if accion == "editada":
        cambios = {
            campo: {"antes": antes.get(campo), "despues": nuevo}
            for campo, nuevo in (despues or {}).items()
            if antes.get(campo) != nuevo
        }
        if not cambios:
            return
        detalle = {"cambios": cambios}
    elif accion == "eliminada":
        detalle = {"registro": antes or {}}
    else:
        detalle = {
            "registro": despues or {},
            "origen": {
                "archivo": (despues or {}).get("archivo_origen"),
                "fila": (despues or {}).get("fila_origen"),
            },
        }
    evento = EventoAuditoria(
        grupo_id=grupo_id(request),
        transaccion_id=tx.id,
        empresa_id=tx.empresa_id,
        accion=accion,
        usuario_id=getattr(request.state, "usuario_id", None),
        detalle=json.dumps(detalle, ensure_ascii=False),
    )
    if cuando is not None:
        evento.creado_en = cuando
    db.add(evento)


def sembrar_eventos_existentes(db: Session) -> None:
    """Los movimientos anteriores al rastro reciben un hecho de alta, una sola vez."""
    con_rastro = {
        fila[0]
        for fila in db.query(EventoAuditoria.transaccion_id).distinct()
    }
    pendientes = (
        db.query(Transaccion, Empresa.grupo_id)
        .join(Empresa, Transaccion.empresa_id == Empresa.id)
        .all()
    )
    for tx, grupo in pendientes:
        if tx.id in con_rastro:
            continue
        actual = foto(tx)
        accion = "importada" if actual.get("archivo_origen") else "creada"
        db.add(EventoAuditoria(
            grupo_id=grupo,
            transaccion_id=tx.id,
            empresa_id=tx.empresa_id,
            accion=accion,
            usuario_id=None,
            detalle=json.dumps({
                "registro": actual,
                "origen": {"archivo": actual.get("archivo_origen"), "fila": actual.get("fila_origen")},
                "nota": "Reconstruido a partir del movimiento ya guardado.",
            }, ensure_ascii=False),
            creado_en=tx.creada_en,
        ))
    db.commit()


def leer_auditoria(db: Session, request: Request, transaccion_id: int) -> dict:
    tx = transacciones_visibles(db, request).filter(Transaccion.id == transaccion_id).first()
    consulta = db.query(EventoAuditoria).filter(
        EventoAuditoria.transaccion_id == transaccion_id,
        EventoAuditoria.grupo_id == grupo_id(request),
    )
    propia = empresa_asignada(request)
    if propia is not None:
        consulta = consulta.filter(EventoAuditoria.empresa_id == propia)
    eventos = consulta.order_by(EventoAuditoria.creado_en.asc(), EventoAuditoria.id.asc()).all()
    if tx is None and not eventos:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    usuarios = {}
    ids = {evento.usuario_id for evento in eventos if evento.usuario_id}
    if ids:
        for usuario in db.query(Usuario).filter(Usuario.id.in_(ids)):
            usuarios[usuario.id] = {"id": usuario.id, "nombre": usuario.nombre, "email": usuario.email}
    return {
        "transaccion_id": transaccion_id,
        "eliminada": tx is None,
        "transaccion": tx,
        "eventos": [
            {
                "id": evento.id,
                "accion": evento.accion,
                "creado_en": evento.creado_en.isoformat() if evento.creado_en else None,
                "usuario": usuarios.get(evento.usuario_id),
                "detalle": json.loads(evento.detalle),
            }
            for evento in eventos
        ],
    }
