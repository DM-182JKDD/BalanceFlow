import os
import tempfile
from pathlib import Path

_db = Path(tempfile.mkdtemp(prefix="balanceflow-test-")) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db.as_posix()}"
os.environ["DEBUG"] = "false"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:5173"
os.environ["SECRET_KEY"] = "clave-de-prueba-balanceflow-segura"
os.environ["ADMIN_EMAIL"] = "admin@test.local"
os.environ["ADMIN_PASSWORD"] = "clave-admin-test"

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture()
def client():
    from core.security import hash_password
    from database.connection import SessionLocal
    from models import Usuario

    db = SessionLocal()
    admin = db.query(Usuario).filter(Usuario.email == "admin@test.local").first()
    if not db.query(Usuario).filter(Usuario.email == "lector@test.local").first():
        db.add(Usuario(
            email="lector@test.local",
            nombre="Lector",
            password_hash=hash_password("clave-lector-test"),
            rol="lector",
            grupo_id=admin.grupo_id,
            activo=True,
        ))
        db.commit()
    db.close()
    with TestClient(app) as test_client:
        login = test_client.post("/api/auth/login", json={"email": "admin@test.local", "password": "clave-admin-test"})
        assert login.status_code == 200, login.text
        test_client.headers["Authorization"] = f"Bearer {login.json()['access_token']}"
        yield test_client
