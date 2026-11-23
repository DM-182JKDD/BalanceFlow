"""
Router de consolidación: endpoints para consolidar el grupo,
ver indicadores financieros y explicar desviaciones.
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core.acceso import empresa_del_grupo, grupo_id, transacciones_visibles
from database.connection import get_db
from models import Transaccion
from services.consolidacion import consolidar_grupo, consolidado_vacio, explicar_desviacion
from services.parametros import contexto

router = APIRouter(prefix="/api/consolidacion", tags=["Consolidación"])


def _visibles(db: Session, request: Request):
    return transacciones_visibles(db, request)


def _datos(transacciones) -> list[dict]:
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
            "banco": t.banco,
            "categoria": t.categoria,
            "es_intercompany": t.es_intercompany,
            "empresa_contraparte_id": t.empresa_contraparte_id,
            "archivo_origen": t.archivo_origen,
            "fila_origen": t.fila_origen,
        }
        for t in transacciones
    ]


def _consolidar(datos: list[dict], db: Session, request: Request, moneda_base: str | None = None) -> dict:
    tasas, moneda, wacc = contexto(db, grupo_id(request))
    destino = (moneda_base or moneda).upper()
    if destino not in tasas:
        raise HTTPException(status_code=400, detail="Moneda base sin tasa configurada")
    if not datos:
        return consolidado_vacio(destino)
    return consolidar_grupo(datos, tasas, destino, wacc)


def _respuesta(datos: list[dict], resultado: dict) -> dict:
    return {
        "consolidado": resultado["consolidado"],
        "por_empresa": resultado["por_empresa"],
        "intercompany": resultado["intercompany"],
        "total_transacciones_originales": len(datos),
        "total_transacciones_limpias": len(resultado["transacciones_limpias"]),
    }


@router.get("/resumen", summary="Consolidado del grupo con indicadores")
def resumen_consolidado(request: Request, moneda_base: str | None = None, db: Session = Depends(get_db)):
    datos = _datos(_visibles(db, request).all())
    return _respuesta(datos, _consolidar(datos, db, request, moneda_base))


@router.get("/por-empresa/{empresa_id}", summary="Indicadores de una empresa")
def indicadores_empresa(empresa_id: int, request: Request, moneda_base: str | None = None, db: Session = Depends(get_db)):
    empresa_del_grupo(db, request, empresa_id)
    datos = _datos(db.query(Transaccion).filter(Transaccion.empresa_id == empresa_id).all())
    resultado = _consolidar(datos, db, request, moneda_base)
    return {"empresa_id": empresa_id, "consolidado": resultado["consolidado"], "detalle": resultado["por_empresa"]}


@router.get("/intercompany", summary="Detalle de eliminaciones intercompany")
def detalle_intercompany(request: Request, moneda_base: str | None = None, db: Session = Depends(get_db)):
    datos = _datos(_visibles(db, request).all())
    return _consolidar(datos, db, request, moneda_base)["intercompany"]


@router.get("/serie", summary="Ingresos y gastos por mes")
def serie(request: Request, ventana: int = 180, moneda_base: str | None = None, db: Session = Depends(get_db)):
    if ventana < 1 or ventana > 730:
        raise HTTPException(status_code=400, detail="ventana debe estar entre 1 y 730 días")
    datos = _datos(_visibles(db, request).all())
    resultado = _consolidar(datos, db, request, moneda_base)
    hoy = date.today()
    inicio = hoy - timedelta(days=ventana)
    puntos: dict[str, dict] = {}
    for tx in resultado["transacciones_limpias"]:
        texto = str(tx.get("fecha") or "")[:10]
        try:
            fecha = date.fromisoformat(texto)
        except ValueError:
            continue
        if fecha < inicio or fecha > hoy:
            continue
        clave = f"{fecha.year:04d}-{fecha.month:02d}"
        cubo = puntos.setdefault(clave, {"mes": clave, "ingresos": 0.0, "gastos": 0.0})
        cuenta = str(tx.get("cuenta") or "")
        monto = float(tx.get("monto_base") or 0)
        if cuenta.startswith("4"):
            cubo["ingresos"] += monto
        elif cuenta.startswith("5"):
            cubo["gastos"] += abs(monto)
    ordenados = [puntos[k] for k in sorted(puntos)]
    for punto in ordenados:
        punto["ingresos"] = round(punto["ingresos"], 2)
        punto["gastos"] = round(punto["gastos"], 2)
    return {"moneda_base": resultado["consolidado"]["moneda_base"], "puntos": ordenados}


@router.get("/desviaciones", summary="Variación del periodo reciente contra el anterior")
def desviaciones(request: Request, dias: int = 30, moneda_base: str | None = None, db: Session = Depends(get_db)):
    if dias < 1 or dias > 365:
        raise HTTPException(status_code=400, detail="dias debe estar entre 1 y 365")
    hoy = date.today()
    corte = hoy - timedelta(days=dias)
    anterior = corte - timedelta(days=dias)
    datos = _datos(_visibles(db, request).all())

    def _en_rango(inicio, fin):
        seleccion = []
        for fila in datos:
            try:
                fecha = date.fromisoformat(str(fila.get("fecha") or "")[:10])
            except ValueError:
                continue
            if inicio <= fecha <= fin:
                seleccion.append(fila)
        return seleccion

    actual = _consolidar(_en_rango(corte, hoy), db, request, moneda_base)
    previo = _consolidar(_en_rango(anterior, corte - timedelta(days=1)), db, request, moneda_base)
    return {
        "dias": dias,
        "moneda_base": actual["consolidado"]["moneda_base"],
        **explicar_desviacion(actual["consolidado"], previo["consolidado"]),
    }
