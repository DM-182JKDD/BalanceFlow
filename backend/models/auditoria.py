from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from database.connection import Base


class EventoAuditoria(Base):
    """Hecho inmutable sobre una transacción. Sobrevive aunque el movimiento se borre."""

    __tablename__ = "eventos_auditoria"

    id = Column(Integer, primary_key=True)
    grupo_id = Column(Integer, ForeignKey("grupos.id"), nullable=False, index=True)
    transaccion_id = Column(Integer, nullable=False, index=True)
    empresa_id = Column(Integer, nullable=False, index=True)
    accion = Column(String(20), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    detalle = Column(Text, nullable=False)
    creado_en = Column(DateTime, server_default=func.now(), nullable=False)
