from sqlalchemy import Column, Float, ForeignKey, Integer, String

from database.connection import Base


class TasaCambio(Base):
    __tablename__ = "tasas_cambio"

    grupo_id = Column(Integer, ForeignKey("grupos.id"), primary_key=True)
    moneda = Column(String(3), primary_key=True)
    tasa_gtq = Column(Float, nullable=False)


class Parametro(Base):
    __tablename__ = "parametros"

    grupo_id = Column(Integer, ForeignKey("grupos.id"), primary_key=True)
    clave = Column(String(40), primary_key=True)
    valor = Column(String(40), nullable=False)
