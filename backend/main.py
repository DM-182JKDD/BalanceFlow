from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text, or_
from typing import List

from core.config import get_settings
from database.connection import engine, Base, get_db, SessionLocal
from database.bootstrap import inicializar
from core.acceso import empresa_del_grupo, empresas_visibles, grupo_id, sucursales_visibles, transacciones_visibles
from core.security import decode_access_token
from models import Empresa, Sucursal, Transaccion, Usuario
from schemas import (
    EmpresaCreate, EmpresaUpdate, EmpresaResponse,
    SucursalCreate, SucursalUpdate, SucursalResponse,
    TransaccionCreate, TransaccionUpdate, TransaccionResponse,
)
from services.auditoria import foto, leer_auditoria, registrar_evento
from services.consolidacion import convertir_a_moneda_base, dinero
from services.parametros import contexto
from routers import uploads as uploads_router
from routers import consolidacion as consolidacion_router
from routers import exportacion as exportacion_router
from routers import trazabilidad as trazabilidad_router
from routers import validacion as validacion_router
from routers import auth as auth_router
from routers import configuracion as configuracion_router
from routers import soporte as soporte_router

settings = get_settings()

# Crear tablas al arrancar (idempotente) y datos base.
Base.metadata.create_all(bind=engine)
_arranque = SessionLocal()
try:
    inicializar(_arranque)
finally:
    _arranque.close()

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
app.include_router(auth_router.router)
app.include_router(configuracion_router.router)
app.include_router(soporte_router.router)

_RUTAS_PUBLICAS = {"/", "/health", "/docs", "/redoc", "/openapi.json"}


@app.middleware("http")
async def controlar_acceso(request: Request, call_next):
    path = request.url.path
    if request.method == "OPTIONS" or path in _RUTAS_PUBLICAS or path.startswith("/docs"):
        return await call_next(request)
    if path in {"/api/auth/login", "/api/auth/registro"} and request.method == "POST":
        return await call_next(request)
    header = request.headers.get("authorization", "")
    token = header[7:].strip() if header.lower().startswith("bearer ") else ""
    payload = decode_access_token(token) if token else None
    if not payload:
        return JSONResponse(status_code=401, content={"detail": "Sesión no válida"})
    db = SessionLocal()
    try:
        usuario = db.query(Usuario).filter(Usuario.id == payload.get("sub"), Usuario.activo.is_(True)).first()
    finally:
        db.close()
    if usuario is None:
        return JSONResponse(status_code=401, content={"detail": "Sesión no válida"})
    escritura = request.method in {"POST", "PUT", "PATCH", "DELETE"}
    if escritura and usuario.rol != "admin" and not (path == "/api/soporte" and request.method == "POST"):
        return JSONResponse(status_code=403, content={"detail": "No tienes permiso para modificar datos"})
    request.state.usuario_id = usuario.id
    request.state.rol = usuario.rol
    request.state.grupo_id = usuario.grupo_id
    request.state.empresa_id = usuario.empresa_id
    return await call_next(request)


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
def crear_empresa(payload: EmpresaCreate, request: Request, db: Session = Depends(get_db)):
    nueva = Empresa(**payload.model_dump(), grupo_id=grupo_id(request))
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@app.get("/api/empresas", response_model=List[EmpresaResponse], tags=["Empresas"])
def listar_empresas(request: Request, db: Session = Depends(get_db)):
    return empresas_visibles(db, request).all()


@app.get("/api/empresas/{empresa_id}", response_model=EmpresaResponse, tags=["Empresas"])
def obtener_empresa(empresa_id: int, request: Request, db: Session = Depends(get_db)):
    emp = empresa_del_grupo(db, request, empresa_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return emp


@app.patch("/api/empresas/{empresa_id}", response_model=EmpresaResponse, tags=["Empresas"])
def actualizar_empresa(empresa_id: int, payload: EmpresaUpdate, request: Request, db: Session = Depends(get_db)):
    emp = empresa_del_grupo(db, request, empresa_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(emp, campo, valor)
    db.commit()
    db.refresh(emp)
    return emp


@app.delete("/api/empresas/{empresa_id}", status_code=204, tags=["Empresas"])
def eliminar_empresa(empresa_id: int, request: Request, db: Session = Depends(get_db)):
    emp = empresa_del_grupo(db, request, empresa_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    db.delete(emp)
    db.commit()


# ==================== SUCURSALES ====================

@app.post("/api/sucursales", response_model=SucursalResponse, status_code=201, tags=["Sucursales"])
def crear_sucursal(payload: SucursalCreate, request: Request, db: Session = Depends(get_db)):
    emp = empresa_del_grupo(db, request, payload.empresa_id)
    if not emp:
        raise HTTPException(status_code=400, detail="empresa_id no existe")
    nueva = Sucursal(**payload.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@app.get("/api/sucursales", response_model=List[SucursalResponse], tags=["Sucursales"])
def listar_sucursales(request: Request, empresa_id: int | None = None, db: Session = Depends(get_db)):
    consulta = sucursales_visibles(db, request)
    if empresa_id is not None:
        consulta = consulta.filter(Sucursal.empresa_id == empresa_id)
    return consulta.all()


@app.get("/api/sucursales/{sucursal_id}", response_model=SucursalResponse, tags=["Sucursales"])
def obtener_sucursal(sucursal_id: int, request: Request, db: Session = Depends(get_db)):
    suc = sucursales_visibles(db, request).filter(Sucursal.id == sucursal_id).first()
    if not suc:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    return suc


@app.patch("/api/sucursales/{sucursal_id}", response_model=SucursalResponse, tags=["Sucursales"])
def actualizar_sucursal(sucursal_id: int, payload: SucursalUpdate, request: Request, db: Session = Depends(get_db)):
    suc = sucursales_visibles(db, request).filter(Sucursal.id == sucursal_id).first()
    if not suc:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(suc, campo, valor)
    db.commit()
    db.refresh(suc)
    return suc


@app.delete("/api/sucursales/{sucursal_id}", status_code=204, tags=["Sucursales"])
def eliminar_sucursal(sucursal_id: int, request: Request, db: Session = Depends(get_db)):
    suc = sucursales_visibles(db, request).filter(Sucursal.id == sucursal_id).first()
    if not suc:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    db.query(Transaccion).filter(Transaccion.sucursal_id == suc.id).update({Transaccion.sucursal_id: None})
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


def _aplicar_monto_base(tx: Transaccion, db: Session, grupo: int) -> None:
    tasas, moneda, _wacc = contexto(db, grupo)
    tx.monto = dinero(tx.monto)
    tx.monto_base = convertir_a_moneda_base(tx.monto, tx.moneda, tasas, moneda)


@app.post("/api/transacciones", response_model=TransaccionResponse, status_code=201, tags=["Transacciones"])
def crear_transaccion(payload: TransaccionCreate, request: Request, db: Session = Depends(get_db)):
    empresa_del_grupo(db, request, payload.empresa_id)
    if payload.empresa_contraparte_id is not None:
        empresa_del_grupo(db, request, payload.empresa_contraparte_id)
    _validar_referencias(db, payload.empresa_id, payload.sucursal_id, payload.empresa_contraparte_id)
    datos = payload.model_dump()
    datos.pop("monto_base", None)
    nueva = Transaccion(**datos)
    _aplicar_monto_base(nueva, db, grupo_id(request))
    db.add(nueva)
    db.flush()
    registrar_evento(db, request, nueva, "creada")
    db.commit()
    db.refresh(nueva)
    return nueva


@app.get("/api/transacciones", tags=["Transacciones"])
def listar_transacciones(
    empresa_id: int | None = None,
    sucursal_id: int | None = None,
    q: str | None = None,
    es_intercompany: str | None = None,
    orden: str = "fecha",
    direccion: str = "desc",
    offset: int = 0,
    limit: int = 50,
    request: Request = None,
    db: Session = Depends(get_db),
):
    if request is None:
        raise HTTPException(status_code=401, detail="Sesión no válida")
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit debe estar entre 1 y 200")
    if offset < 0:
        raise HTTPException(status_code=400, detail="offset no puede ser negativo")
    consulta = transacciones_visibles(db, request)
    if empresa_id is not None:
        consulta = consulta.filter(Transaccion.empresa_id == empresa_id)
    if sucursal_id is not None:
        consulta = consulta.filter(Transaccion.sucursal_id == sucursal_id)
    if es_intercompany in {"S", "N"}:
        consulta = consulta.filter(Transaccion.es_intercompany == es_intercompany)
    termino = (q or "").strip()
    if termino:
        like = f"%{termino}%"
        consulta = consulta.filter(or_(
            Transaccion.descripcion.ilike(like),
            Transaccion.cuenta.ilike(like),
            Transaccion.categoria.ilike(like),
            Empresa.nombre.ilike(like),
        ))
    columnas = {"fecha": Transaccion.fecha, "monto": Transaccion.monto, "id": Transaccion.id}
    columna = columnas.get(orden, Transaccion.fecha)
    consulta = consulta.order_by(columna.asc() if direccion == "asc" else columna.desc())
    total = consulta.count()
    filas = consulta.offset(offset).limit(limit).all()
    return {
        "items": [TransaccionResponse.model_validate(fila) for fila in filas],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@app.get("/api/transacciones/conteo", tags=["Transacciones"])
def conteo_transacciones(request: Request, db: Session = Depends(get_db)):
    filas = transacciones_visibles(db, request).with_entities(Transaccion.empresa_id, text("count(*)")).group_by(Transaccion.empresa_id).all()
    return {"por_empresa": {str(empresa_id): total for empresa_id, total in filas}}


@app.get("/api/transacciones/{transaccion_id}", response_model=TransaccionResponse, tags=["Transacciones"])
def obtener_transaccion(transaccion_id: int, request: Request, db: Session = Depends(get_db)):
    tx = transacciones_visibles(db, request).filter(Transaccion.id == transaccion_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    return tx


@app.get("/api/transacciones/{transaccion_id}/auditoria", tags=["Transacciones"])
def auditoria_transaccion(transaccion_id: int, request: Request, db: Session = Depends(get_db)):
    data = leer_auditoria(db, request, transaccion_id)
    tx = data["transaccion"]
    data["transaccion"] = TransaccionResponse.model_validate(tx).model_dump(mode="json") if tx else None
    return data


@app.patch("/api/transacciones/{transaccion_id}", response_model=TransaccionResponse, tags=["Transacciones"])
def actualizar_transaccion(transaccion_id: int, payload: TransaccionUpdate, request: Request, db: Session = Depends(get_db)):
    tx = transacciones_visibles(db, request).filter(Transaccion.id == transaccion_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    antes = foto(tx)
    cambios = payload.model_dump(exclude_unset=True)
    empresa_id = cambios.get("empresa_id", tx.empresa_id)
    sucursal_id = cambios.get("sucursal_id", tx.sucursal_id)
    contraparte_id = cambios.get("empresa_contraparte_id", tx.empresa_contraparte_id)
    if empresa_id:
        empresa_del_grupo(db, request, empresa_id)
    if contraparte_id is not None:
        empresa_del_grupo(db, request, contraparte_id)
    _validar_referencias(db, empresa_id, sucursal_id, contraparte_id)
    for campo, valor in cambios.items():
        setattr(tx, campo, valor)
    _aplicar_monto_base(tx, db, grupo_id(request))
    registrar_evento(db, request, tx, "editada", antes)
    db.commit()
    db.refresh(tx)
    return tx


@app.delete("/api/transacciones/{transaccion_id}", status_code=204, tags=["Transacciones"])
def eliminar_transaccion(transaccion_id: int, request: Request, db: Session = Depends(get_db)):
    tx = transacciones_visibles(db, request).filter(Transaccion.id == transaccion_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    registrar_evento(db, request, tx, "eliminada", foto(tx))
    db.delete(tx)
    db.commit()