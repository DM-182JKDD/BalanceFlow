"""Descarga del consolidado en Excel y CSV."""
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Request

from core.acceso import grupo_id, transacciones_visibles
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from database.connection import get_db
from models import Transaccion
from services.consolidacion import consolidado_vacio, consolidar_grupo
from services.exportacion import generar_excel_consolidado
from services.parametros import contexto

router = APIRouter(prefix="/api", tags=["Exportación"])


def _filas(db: Session, request: Request) -> list[dict]:
    consulta = transacciones_visibles(db, request)
    return [
        {
            "id": t.id,
            "empresa_id": t.empresa_id,
            "sucursal_id": t.sucursal_id,
            "fecha": str(t.fecha) if t.fecha is not None else None,
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
        for t in consulta.all()
    ]


def _consolidar_o_error(datos: list[dict], db: Session, request: Request) -> dict:
    tasas, moneda, wacc = contexto(db, grupo_id(request))
    if not datos:
        return consolidado_vacio(moneda)
    return consolidar_grupo(datos, tasas, moneda, wacc)


@router.get("/exportar/excel", summary="Descargar Excel consolidado")
def exportar_excel(request: Request, db: Session = Depends(get_db)):
    reporte = _consolidar_o_error(_filas(db, request), db, request)
    return Response(
        content=generar_excel_consolidado(reporte),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Balance_Consolidado_BalanceFlow.xlsx"},
    )


@router.get("/exportacion/csv", summary="Descargar CSV de transacciones limpias")
def exportar_csv(request: Request, db: Session = Depends(get_db)):
    reporte = _consolidar_o_error(_filas(db, request), db, request)
    limpias = reporte["transacciones_limpias"]
    buffer = io.StringIO()
    if limpias:
        campos = list(limpias[0].keys())
        writer = csv.DictWriter(buffer, fieldnames=campos)
        writer.writeheader()
        for fila in limpias:
            writer.writerow({k: "" if v is None else v for k, v in fila.items()})
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=consolidado.csv"},
    )
