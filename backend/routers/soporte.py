from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.connection import get_db
from models import TicketSoporte, Usuario

router = APIRouter(prefix="/api/soporte", tags=["Soporte"])


class TicketCreate(BaseModel):
    mensaje: str = Field(..., min_length=5, max_length=1000)


@router.post("", status_code=201)
def crear_ticket(payload: TicketCreate, request: Request, db: Session = Depends(get_db)):
    usuario_id = getattr(request.state, "usuario_id", None)
    if usuario_id is None:
        raise HTTPException(status_code=401, detail="Sesión no válida")
    if not db.query(Usuario.id).filter(Usuario.id == usuario_id).first():
        raise HTTPException(status_code=401, detail="Sesión no válida")
    ticket = TicketSoporte(usuario_id=usuario_id, mensaje=payload.mensaje.strip())
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return {"id": ticket.id, "mensaje": "Mensaje enviado al equipo de soporte."}
