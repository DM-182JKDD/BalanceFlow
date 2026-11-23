import os
import tempfile
from pathlib import Path

_db = Path(tempfile.mkdtemp(prefix="balanceflow-test-")) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db.as_posix()}"
os.environ["DEBUG"] = "false"
os.environ["ALLOWED_ORIGINS"] = "http://localhost:5173"

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
