import logging
import secrets

from sqlalchemy import inspect, text

from models import Grupo, Usuario
from core.config import get_settings
from core.security import hash_password
from services.parametros import sembrar_configuracion

logger = logging.getLogger("balanceflow")


def _columnas(db, tabla: str) -> set[str]:
    try:
        return {columna["name"] for columna in inspect(db.get_bind()).get_columns(tabla)}
    except Exception:
        return set()


def _agregar_grupo_id(db, tabla: str) -> None:
    if "grupo_id" in _columnas(db, tabla):
        return
    db.execute(text(f"ALTER TABLE {tabla} ADD COLUMN grupo_id INTEGER"))
    db.commit()


def _reconstruir_tabla_por_grupo(db, tabla: str, grupo: int, definicion: str, copia: str) -> None:
    if "grupo_id" in _columnas(db, tabla):
        return
    previa = f"{tabla}_previa"
    db.execute(text(f"ALTER TABLE {tabla} RENAME TO {previa}"))
    db.execute(text(definicion))
    db.execute(text(copia), {"grupo": grupo})
    db.execute(text(f"DROP TABLE {previa}"))
    db.commit()


def migrar_grupos(db) -> None:
    """Las bases creadas antes del servicio reciben un grupo y la columna grupo_id."""
    _agregar_grupo_id(db, "empresas")
    _agregar_grupo_id(db, "usuarios")
    huerfanos = db.execute(text(
        "SELECT (SELECT COUNT(*) FROM usuarios WHERE grupo_id IS NULL) + (SELECT COUNT(*) FROM empresas WHERE grupo_id IS NULL)"
    )).scalar() or 0
    grupo_id = None
    if huerfanos:
        grupo = Grupo(nombre="Demostración")
        db.add(grupo)
        db.commit()
        db.refresh(grupo)
        grupo_id = grupo.id
        db.execute(text("UPDATE usuarios SET grupo_id = :grupo WHERE grupo_id IS NULL"), {"grupo": grupo_id})
        db.execute(text("UPDATE empresas SET grupo_id = :grupo WHERE grupo_id IS NULL"), {"grupo": grupo_id})
        db.commit()
    if grupo_id is None and "grupo_id" not in _columnas(db, "tasas_cambio"):
        existente = db.query(Grupo).order_by(Grupo.id).first()
        if existente is None:
            existente = Grupo(nombre="Demostración")
            db.add(existente)
            db.commit()
            db.refresh(existente)
        grupo_id = existente.id
    if grupo_id is not None:
        _reconstruir_tabla_por_grupo(
            db,
            "tasas_cambio",
            grupo_id,
            """
            CREATE TABLE tasas_cambio (
                grupo_id INTEGER NOT NULL,
                moneda VARCHAR(3) NOT NULL,
                tasa_gtq FLOAT NOT NULL,
                PRIMARY KEY (grupo_id, moneda)
            )
            """,
            "INSERT INTO tasas_cambio (grupo_id, moneda, tasa_gtq) SELECT :grupo, moneda, tasa_gtq FROM tasas_cambio_previa",
        )
        _reconstruir_tabla_por_grupo(
            db,
            "parametros",
            grupo_id,
            """
            CREATE TABLE parametros (
                grupo_id INTEGER NOT NULL,
                clave VARCHAR(40) NOT NULL,
                valor VARCHAR(40) NOT NULL,
                PRIMARY KEY (grupo_id, clave)
            )
            """,
            "INSERT INTO parametros (grupo_id, clave, valor) SELECT :grupo, clave, valor FROM parametros_previa",
        )
        sembrar_configuracion(db, grupo_id)
        db.commit()


def inicializar(db) -> None:
    """Prepara la base. Cada arranque no inventa empresas ni usuarios de ejemplo."""
    from services.auditoria import sembrar_eventos_existentes

    migrar_grupos(db)
    if db.query(Usuario).count() == 0:
        _crear_admin(db)
    sembrar_eventos_existentes(db)


def _crear_admin(db) -> None:
    ajustes = get_settings()
    email = ajustes.ADMIN_EMAIL.strip().lower() or "admin@balanceflow.local"
    password = ajustes.ADMIN_PASSWORD or None
    generada = not password
    if generada:
        password = secrets.token_urlsafe(12)
    grupo = Grupo(nombre="Espacio de trabajo")
    db.add(grupo)
    db.flush()
    sembrar_configuracion(db, grupo.id)
    db.add(Usuario(
        email=email,
        nombre="Administrador",
        password_hash=hash_password(password),
        rol="admin",
        grupo_id=grupo.id,
        activo=True,
    ))
    db.commit()
    logger.warning("Administrador inicial: %s", email)
    if generada:
        logger.warning("Contraseña generada para este arranque: %s", password)
        print(f"Administrador inicial: {email}")
        print(f"Contraseña generada: {password}")
