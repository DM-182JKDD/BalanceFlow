<<<<<<< HEAD
"""Endpoint para descargar el Excel del consolidado."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database.connection import get_db
from models import Transaccion
from services.consolidacion import ErrorConsolidacion, consolidar_grupo
from services.exportacion import generar_excel_consolidado

router = APIRouter(prefix="/api/exportar", tags=["Exportación"])


@router.get("/excel", summary="Descargar Excel consolidado")
def exportar_excel(db: Session = Depends(get_db)):
    transacciones = db.query(Transaccion).all()
    if not transacciones:
        raise HTTPException(status_code=404, detail="No hay transacciones para exportar.")

    datos = [
        {
            "id": t.id,
            "empresa_id": t.empresa_id,
            "sucursal_id": t.sucursal_id,
            "fecha": str(t.fecha),
            "cuenta": t.cuenta,
            "descripcion": t.descripcion,
            "monto": t.monto,
            "moneda": t.moneda,
            "monto_base": t.monto_base,
            "banco": t.banco,
            "categoria": t.categoria,
            "es_intercompany": t.es_intercompany,
            "empresa_contraparte_id": t.empresa_contraparte_id,
            "archivo_origen": t.archivo_origen,
            "fila_origen": t.fila_origen,
        }
        for t in transacciones
    ]

    try:
        reporte = consolidar_grupo(datos)
    except ErrorConsolidacion as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return Response(
        content=generar_excel_consolidado(reporte),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Balance_Consolidado_BalanceFlow.xlsx"},
    )
=======
import csv
import io

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from database.connection import SessionLocal
from models import Transaccion
from services.consolidacion import consolidar_grupo

router = APIRouter(prefix="/api/exportacion", tags=["Exportación"])


def _filas():
    db = SessionLocal()
    try:
        return [
            {c.name: getattr(t, c.name) for c in t.__table__.columns}
            for t in db.query(Transaccion).all()
        ]
    finally:
        db.close()


@router.get("/csv")
def exportar_csv():
    """Exporta las transacciones limpias (post-eliminación intercompany) a CSV."""
    r = consolidar_grupo(_filas())
    limpias = r["transacciones_limpias"]
    buf = io.StringIO()
    if limpias:
        w = csv.DictWriter(buf, fieldnames=list(limpias[0].keys()))
        w.writeheader()
        w.writerows(limpias)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=consolidado.csv"},
    )
>>>>>>> 9274efb6cd6060b92a1a46ed627856742652eef2
