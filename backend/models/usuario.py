from sqlalchemy import Boolean, Column, ForeignKey, Integer, String

from database.connection import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    nombre = Column(String(120), nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol = Column(String(20), nullable=False, default="lector")
    grupo_id = Column(Integer, ForeignKey("grupos.id"), nullable=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True, index=True)
    activo = Column(Boolean, nullable=False, default=True)
