from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from database.connection import Base


class TicketSoporte(Base):
    __tablename__ = "tickets_soporte"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    mensaje = Column(String(1000), nullable=False)
    creado_en = Column(DateTime, server_default=func.now(), nullable=False)
