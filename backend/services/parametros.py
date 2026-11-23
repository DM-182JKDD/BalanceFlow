from models import Parametro, TasaCambio
from services.consolidacion import MONEDA_BASE, TASAS_CAMBIO


def sembrar_configuracion(db, grupo_id: int) -> None:
    """Tasas y parámetros iniciales. El grupo los cambia después."""
    if db.query(TasaCambio).filter(TasaCambio.grupo_id == grupo_id).count() == 0:
        for moneda, tasa in TASAS_CAMBIO.items():
            db.add(TasaCambio(grupo_id=grupo_id, moneda=moneda, tasa_gtq=tasa))
    if not db.query(Parametro).filter(Parametro.grupo_id == grupo_id, Parametro.clave == "moneda_base").first():
        db.add(Parametro(grupo_id=grupo_id, clave="moneda_base", valor=MONEDA_BASE))
    if not db.query(Parametro).filter(Parametro.grupo_id == grupo_id, Parametro.clave == "wacc").first():
        db.add(Parametro(grupo_id=grupo_id, clave="wacc", valor="0.10"))


def contexto(db, grupo_id: int) -> tuple[dict, str, float]:
    filas = db.query(TasaCambio).filter(TasaCambio.grupo_id == grupo_id).all()
    tasas = {fila.moneda.upper(): float(fila.tasa_gtq) for fila in filas} or dict(TASAS_CAMBIO)
    guardados = {
        fila.clave: fila.valor
        for fila in db.query(Parametro).filter(Parametro.grupo_id == grupo_id).all()
    }
    moneda = str(guardados.get("moneda_base") or MONEDA_BASE).upper()
    try:
        wacc = float(guardados.get("wacc") or 0.10)
    except ValueError:
        wacc = 0.10
    return tasas, moneda, wacc


def guardar(db, grupo_id: int, moneda_base: str | None = None, wacc: float | None = None, tasas: dict | None = None, nombre_grupo: str | None = None) -> dict:
    from models import Grupo

    if nombre_grupo and nombre_grupo.strip():
        grupo = db.query(Grupo).filter(Grupo.id == grupo_id).first()
        if grupo:
            grupo.nombre = nombre_grupo.strip()[:120]
    if moneda_base:
        _upsert(db, grupo_id, "moneda_base", moneda_base.upper())
    if wacc is not None:
        _upsert(db, grupo_id, "wacc", str(round(float(wacc), 4)))
    if tasas:
        for moneda, tasa in tasas.items():
            codigo = str(moneda).upper()[:3]
            if len(codigo) != 3:
                continue
            fila = db.query(TasaCambio).filter(TasaCambio.grupo_id == grupo_id, TasaCambio.moneda == codigo).first()
            if fila:
                fila.tasa_gtq = float(tasa)
            else:
                db.add(TasaCambio(grupo_id=grupo_id, moneda=codigo, tasa_gtq=float(tasa)))
    db.commit()
    tasas_activas, moneda, costo = contexto(db, grupo_id)
    grupo = db.query(Grupo).filter(Grupo.id == grupo_id).first()
    return {
        "nombre_grupo": grupo.nombre if grupo else "",
        "moneda_base": moneda,
        "wacc": costo,
        "tasas": tasas_activas,
    }


def _upsert(db, grupo_id: int, clave: str, valor: str) -> None:
    fila = db.query(Parametro).filter(Parametro.grupo_id == grupo_id, Parametro.clave == clave).first()
    if fila:
        fila.valor = valor
    else:
        db.add(Parametro(grupo_id=grupo_id, clave=clave, valor=valor))
