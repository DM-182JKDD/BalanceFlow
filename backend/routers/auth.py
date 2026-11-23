from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.acceso import empresa_del_grupo, grupo_id
from core.security import create_access_token, hash_password, verify_password
from database.connection import get_db
from models import Grupo, Usuario
from services.parametros import sembrar_configuracion

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=8, max_length=128)


class RegistroRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=120)
    email: str = Field(..., min_length=3, max_length=120)
    password: str = Field(..., min_length=8, max_length=128)
    nombre_grupo: str = Field(..., min_length=1, max_length=120)


class UsuarioPublico(BaseModel):
    id: int
    email: str
    nombre: str
    rol: str
    grupo_id: int | None = None
    grupo_nombre: str = ""
    empresa_id: int | None = None


class UsuarioCreate(BaseModel):
    email: str = Field(..., min_length=3, max_length=120)
    nombre: str = Field(..., min_length=1, max_length=120)
    password: str = Field(..., min_length=8, max_length=128)
    rol: str = Field("lector", pattern="^(admin|lector|empresa)$")
    empresa_id: int | None = None


def _publico(db: Session, usuario: Usuario) -> UsuarioPublico:
    grupo = db.query(Grupo).filter(Grupo.id == usuario.grupo_id).first()
    return UsuarioPublico(
        id=usuario.id,
        email=usuario.email,
        nombre=usuario.nombre,
        rol=usuario.rol,
        grupo_id=usuario.grupo_id,
        grupo_nombre=grupo.nombre if grupo else "",
        empresa_id=usuario.empresa_id,
    )


def _sesion(db: Session, usuario: Usuario) -> dict:
    return {
        "access_token": create_access_token(usuario.id, usuario.email, usuario.rol),
        "token_type": "bearer",
        "usuario": _publico(db, usuario),
    }


@router.post("/registro", status_code=201)
def registrarse(payload: RegistroRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if db.query(Usuario).filter(func.lower(Usuario.email) == email).first():
        raise HTTPException(status_code=409, detail="Ese correo ya está registrado")
    grupo = Grupo(nombre=payload.nombre_grupo.strip())
    db.add(grupo)
    db.flush()
    sembrar_configuracion(db, grupo.id)
    usuario = Usuario(
        email=email,
        nombre=payload.nombre.strip(),
        password_hash=hash_password(payload.password),
        rol="admin",
        grupo_id=grupo.id,
        activo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return _sesion(db, usuario)


@router.post("/usuarios", status_code=201)
def crear_usuario(payload: UsuarioCreate, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if db.query(Usuario).filter(func.lower(Usuario.email) == email).first():
        raise HTTPException(status_code=409, detail="Ese correo ya está registrado")
    if payload.rol == "empresa" and payload.empresa_id is None:
        raise HTTPException(status_code=422, detail="Un usuario de empresa necesita empresa_id")
    if payload.rol == "empresa":
        empresa_del_grupo(db, request, payload.empresa_id)
    grupo = grupo_id(request)
    usuario = Usuario(
        email=email,
        nombre=payload.nombre.strip(),
        password_hash=hash_password(payload.password),
        rol=payload.rol,
        grupo_id=grupo,
        empresa_id=payload.empresa_id if payload.rol == "empresa" else None,
        activo=True,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    return _publico(db, usuario)


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    usuario = db.query(Usuario).filter(func.lower(Usuario.email) == payload.email.strip().lower()).first()
    if not usuario or not usuario.activo or not usuario.grupo_id or not verify_password(payload.password, usuario.password_hash):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    return _sesion(db, usuario)
