import math
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

from core.acceso import empresa_asignada, grupo_id, transacciones_visibles
from database.connection import SessionLocal
from models import Transaccion
from services.consolidacion import consolidar_grupo
from services.parametros import contexto

router = APIRouter(prefix="/api/trazabilidad", tags=["Trazabilidad"])

PREFIJOS = {"ingresos": "4", "gastos": "5", "activos": "1", "pasivos": "2"}


def _limpiar(d: dict) -> dict:
    """pandas convierte None en NaN y eso rompe el JSON."""
    return {
        k: (None if isinstance(v, float) and math.isnan(v) else v)
        for k, v in d.items()
    }


def _filas(request: Request, empresa_id: int | None):
    db = SessionLocal()
    try:
        consulta = transacciones_visibles(db, request)
        if empresa_id is not None:
            consulta = consulta.filter(Transaccion.empresa_id == empresa_id)
        filas = [
            {c.name: getattr(t, c.name) for c in t.__table__.columns}
            for t in consulta.all()
        ]
        tasas, moneda, wacc = contexto(db, grupo_id(request))
        return filas, tasas, moneda, wacc
    finally:
        db.close()


@router.get("/{componente}")
def trazar(componente: str, request: Request, empresa_id: Optional[int] = None):
    """
    Drill-down: de qué transacciones sale cada cifra.
    componente: ingresos | gastos | activos | pasivos
    """
    if componente not in PREFIJOS:
        raise HTTPException(400, f"Componente inválido. Usa: {list(PREFIJOS)}")

    propia = empresa_asignada(request)
    if propia is not None:
        empresa_id = propia
    filas, tasas, moneda, wacc = _filas(request, empresa_id)
    r = consolidar_grupo(filas, tasas, moneda, wacc) if filas else consolidar_grupo([], tasas, moneda, wacc)
    pref = PREFIJOS[componente]

    detalle = []
    for t in r["transacciones_limpias"]:
        if not str(t.get("cuenta", "")).startswith(pref):
            continue
        if empresa_id and t.get("empresa_id") != empresa_id:
            continue
        t = _limpiar(t)
        moneda = str(t.get("moneda", "")).upper()
        detalle.append({
            "id": t.get("id"),
            "empresa_id": t.get("empresa_id"),
            "fecha": str(t.get("fecha")),
            "cuenta": t.get("cuenta"),
            "descripcion": t.get("descripcion"),
            "monto_original": t.get("monto"),
            "moneda": moneda,
            "tasa_aplicada": tasas.get(moneda),
            "monto_gtq": t.get("monto_base"),
            "es_intercompany": t.get("es_intercompany"),
            "archivo_origen": t.get("archivo_origen"),
            "fila_origen": t.get("fila_origen"),
            "creada_en": str(t.get("creada_en") or ""),
        })

    return {
        "componente": componente,
        "empresa_id": empresa_id,
        "total_registros": len(detalle),
        "total_gtq": round(sum(abs(d["monto_gtq"] or 0) for d in detalle), 2),
        "registros": detalle,
        "intercompany_eliminadas": r["intercompany"]["eliminadas"],
    }