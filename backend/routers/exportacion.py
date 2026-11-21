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