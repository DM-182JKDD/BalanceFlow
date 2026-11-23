from sqlalchemy import Column, DateTime, Integer, String, func

from database.connection import Base


class Grupo(Base):
    """Espacio de un cliente del servicio. Los datos de ejemplo son un grupo más."""

    __tablename__ = "grupos"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(120), nullable=False)
    creado_en = Column(DateTime, server_default=func.now(), nullable=False)
