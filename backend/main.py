from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List

from core.config import get_settings
from database.connection import engine, Base, get_db
from models import Empresa, Sucursal, Transaccion
from schemas import (
    EmpresaCreate, EmpresaUpdate, EmpresaResponse,
    SucursalCreate, SucursalUpdate, SucursalResponse,
    TransaccionCreate, TransaccionUpdate, TransaccionResponse,
)
from services.consolidacion import convertir_a_moneda_base
from routers import uploads as uploads_router
from routers import consolidacion as consolidacion_router
from routers import exportacion as exportacion_router
from routers import trazabilidad as trazabilidad_router
from routers import validacion as validacion_router

settings = get_settings()

# Crear tablas al arrancar (idempotente)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend de consolidación multiempresa y aduana financiera",
    version=settings.APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Registrar routers
app.include_router(uploads_router.router)
app.include_router(consolidacion_router.router)
app.include_router(exportacion_router.router)
app.include_router(trazabilidad_router.router)
app.include_router(validacion_router.router)


# ==================== HEALTH ====================

@app.get("/", tags=["Health"])
def read_root():
    return {
        "status": "success",
        "message": "¡Backend de BalanceFlow activo y listo para el hackathon! 🚀",
        "version": settings.APP_VERSION,
    }


@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "conectada"}
    except Exception:
        return {"status": "unhealthy", "database": "no disponible"}


# ==================== EMPRESAS ====================

@app.post("/api/empresas", response_model=EmpresaResponse, status_code=201, tags=["Empresas"])
def crear_empresa(payload: EmpresaCreate, db: Session = Depends(get_db)):
    nueva = Empresa(**payload.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@app.get("/api/empresas", response_model=List[EmpresaResponse], tags=["Empresas"])
def listar_empresas(db: Session = Depends(get_db)):
    return db.query(Empresa).all()


@app.get("/api/empresas/{empresa_id}", response_model=EmpresaResponse, tags=["Empresas"])
def obtener_empresa(empresa_id: int, db: Session = Depends(get_db)):
    emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return emp


@app.patch("/api/empresas/{empresa_id}", response_model=EmpresaResponse, tags=["Empresas"])
def actualizar_empresa(empresa_id: int, payload: EmpresaUpdate, db: Session = Depends(get_db)):
    emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(emp, campo, valor)
    db.commit()
    db.refresh(emp)
    return emp


@app.delete("/api/empresas/{empresa_id}", status_code=204, tags=["Empresas"])
def eliminar_empresa(empresa_id: int, db: Session = Depends(get_db)):
    emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    db.delete(emp)
    db.commit()


# ==================== SUCURSALES ====================

@app.post("/api/sucursales", response_model=SucursalResponse, status_code=201, tags=["Sucursales"])
def crear_sucursal(payload: SucursalCreate, db: Session = Depends(get_db)):
    emp = db.query(Empresa).filter(Empresa.id == payload.empresa_id).first()
    if not emp:
        raise HTTPException(status_code=400, detail="empresa_id no existe")
    nueva = Sucursal(**payload.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@app.get("/api/sucursales", response_model=List[SucursalResponse], tags=["Sucursales"])
def listar_sucursales(empresa_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Sucursal)
    if empresa_id is not None:
        q = q.filter(Sucursal.empresa_id == empresa_id)
    return q.all()


@app.get("/api/sucursales/{sucursal_id}", response_model=SucursalResponse, tags=["Sucursales"])
def obtener_sucursal(sucursal_id: int, db: Session = Depends(get_db)):
    suc = db.query(Sucursal).filter(Sucursal.id == sucursal_id).first()
    if not suc:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    return suc


@app.patch("/api/sucursales/{sucursal_id}", response_model=SucursalResponse, tags=["Sucursales"])
def actualizar_sucursal(sucursal_id: int, payload: SucursalUpdate, db: Session = Depends(get_db)):
    suc = db.query(Sucursal).filter(Sucursal.id == sucursal_id).first()
    if not suc:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(suc, campo, valor)
    db.commit()
    db.refresh(suc)
    return suc


@app.delete("/api/sucursales/{sucursal_id}", status_code=204, tags=["Sucursales"])
def eliminar_sucursal(sucursal_id: int, db: Session = Depends(get_db)):
    suc = db.query(Sucursal).filter(Sucursal.id == sucursal_id).first()
    if not suc:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    db.delete(suc)
    db.commit()


# ==================== TRANSACCIONES ====================

def _validar_referencias(db: Session, empresa_id: int, sucursal_id: int | None, contraparte_id: int | None):
    emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not emp:
        raise HTTPException(status_code=400, detail="empresa_id no existe")
    if sucursal_id is not None:
        suc = db.query(Sucursal).filter(Sucursal.id == sucursal_id).first()
        if not suc:
            raise HTTPException(status_code=400, detail="sucursal_id no existe")
        if suc.empresa_id != empresa_id:
            raise HTTPException(status_code=400, detail="La sucursal no pertenece a la empresa")
    if contraparte_id is not None:
        contra = db.query(Empresa).filter(Empresa.id == contraparte_id).first()
        if not contra:
            raise HTTPException(status_code=400, detail="empresa_contraparte_id no existe")
        if contraparte_id == empresa_id:
            raise HTTPException(status_code=400, detail="La contraparte debe ser otra empresa")


def _aplicar_monto_base(tx: Transaccion) -> None:
    tx.monto_base = convertir_a_moneda_base(tx.monto, tx.moneda)


@app.post("/api/transacciones", response_model=TransaccionResponse, status_code=201, tags=["Transacciones"])
def crear_transaccion(payload: TransaccionCreate, db: Session = Depends(get_db)):
    _validar_referencias(db, payload.empresa_id, payload.sucursal_id, payload.empresa_contraparte_id)
    datos = payload.model_dump()
    datos.pop("monto_base", None)
    nueva = Transaccion(**datos)
    _aplicar_monto_base(nueva)
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@app.get("/api/transacciones", response_model=List[TransaccionResponse], tags=["Transacciones"])
def listar_transacciones(
    empresa_id: int | None = None,
    sucursal_id: int | None = None,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    if limit < 1 or limit > 1000:
        raise HTTPException(status_code=400, detail="limit debe estar entre 1 y 1000")
    q = db.query(Transaccion)
    if empresa_id is not None:
        q = q.filter(Transaccion.empresa_id == empresa_id)
    if sucursal_id is not None:
        q = q.filter(Transaccion.sucursal_id == sucursal_id)
    return q.limit(limit).all()


@app.get("/api/transacciones/{transaccion_id}", response_model=TransaccionResponse, tags=["Transacciones"])
def obtener_transaccion(transaccion_id: int, db: Session = Depends(get_db)):
    tx = db.query(Transaccion).filter(Transaccion.id == transaccion_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    return tx


@app.patch("/api/transacciones/{transaccion_id}", response_model=TransaccionResponse, tags=["Transacciones"])
def actualizar_transaccion(transaccion_id: int, payload: TransaccionUpdate, db: Session = Depends(get_db)):
    tx = db.query(Transaccion).filter(Transaccion.id == transaccion_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    cambios = payload.model_dump(exclude_unset=True)
    empresa_id = cambios.get("empresa_id", tx.empresa_id)
    sucursal_id = cambios.get("sucursal_id", tx.sucursal_id)
    contraparte_id = cambios.get("empresa_contraparte_id", tx.empresa_contraparte_id)
    _validar_referencias(db, empresa_id, sucursal_id, contraparte_id)
    for campo, valor in cambios.items():
        setattr(tx, campo, valor)
    _aplicar_monto_base(tx)
    db.commit()
    db.refresh(tx)
    return tx


@app.delete("/api/transacciones/{transaccion_id}", status_code=204, tags=["Transacciones"])
def eliminar_transaccion(transaccion_id: int, db: Session = Depends(get_db)):
    tx = db.query(Transaccion).filter(Transaccion.id == transaccion_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    db.delete(tx)
    db.commit()