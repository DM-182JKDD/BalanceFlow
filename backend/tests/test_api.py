def test_sin_token_no_entra(client):
    response = client.get("/api/empresas", headers={"Authorization": ""})
    assert response.status_code == 401


def test_lector_no_puede_crear(client):
    login = client.post("/api/auth/login", json={"email": "lector@test.local", "password": "clave-lector-test"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    response = client.post(
        "/api/empresas",
        json={"nombre": "Bloqueada", "pais": "Guatemala", "moneda_local": "GTQ"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_consolidado_vacio_responde_200(client):
    response = client.get("/api/consolidacion/resumen")
    assert response.status_code == 200
    assert response.json()["consolidado"]["total_ingresos"] == 0


def test_usuario_de_empresa_solo_ve_la_suya(client):
    propia = client.post("/api/empresas", json={"nombre": "Norte", "pais": "Guatemala", "moneda_local": "GTQ"}).json()
    ajena = client.post("/api/empresas", json={"nombre": "Sur", "pais": "Mexico", "moneda_local": "MXN"}).json()
    for empresa, monto in ((propia, 10), (ajena, 20)):
        alta = client.post("/api/transacciones", json={
            "empresa_id": empresa["id"], "fecha": "2026-11-01", "cuenta": "4100", "monto": monto, "moneda": "GTQ",
        })
        assert alta.status_code == 201
    creado = client.post("/api/auth/usuarios", json={
        "email": "norte@test.local", "nombre": "Norte", "password": "clave-norte-test", "rol": "empresa", "empresa_id": propia["id"],
    })
    assert creado.status_code == 201
    login = client.post("/api/auth/login", json={"email": "norte@test.local", "password": "clave-norte-test"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    empresas = client.get("/api/empresas", headers=headers)
    assert empresas.status_code == 200
    assert [fila["id"] for fila in empresas.json()] == [propia["id"]]
    assert client.get(f"/api/empresas/{ajena['id']}", headers=headers).status_code == 404
    movimientos = client.get("/api/transacciones", headers=headers).json()
    assert movimientos["total"] == 1
    assert movimientos["items"][0]["empresa_id"] == propia["id"]
    propia_id = movimientos["items"][0]["id"]
    pista = client.get(f"/api/transacciones/{propia_id}/auditoria", headers=headers)
    assert pista.status_code == 200
    assert pista.json()["eventos"][0]["accion"] == "creada"
    ajenas = client.get("/api/transacciones").json()["items"]
    ajena_id = next(fila["id"] for fila in ajenas if fila["empresa_id"] == ajena["id"])
    assert client.get(f"/api/transacciones/{ajena_id}/auditoria", headers=headers).status_code == 404
    resumen = client.get("/api/consolidacion/resumen", headers=headers).json()
    assert resumen["total_transacciones_originales"] == 1
    assert client.post("/api/empresas", json={"nombre": "Otra", "pais": "GT", "moneda_local": "GTQ"}, headers=headers).status_code == 403


def test_registro_empieza_en_un_grupo_vacio(client):
    client.post("/api/empresas", json={"nombre": "Ajena", "pais": "Guatemala", "moneda_local": "GTQ"})
    alta = client.post("/api/auth/registro", json={
        "nombre": "Ana Ruiz",
        "email": "ana@cliente.test",
        "password": "clave-ana-test",
        "nombre_grupo": "Grupo Ruiz",
    })
    assert alta.status_code == 201
    cuerpo = alta.json()
    assert cuerpo["usuario"]["rol"] == "admin"
    assert cuerpo["usuario"]["grupo_nombre"] == "Grupo Ruiz"
    headers = {"Authorization": f"Bearer {cuerpo['access_token']}"}
    assert client.get("/api/empresas", headers=headers).json() == []
    propia = client.post("/api/empresas", json={"nombre": "Ruiz SA", "pais": "Costa Rica", "moneda_local": "CRC"}, headers=headers)
    assert propia.status_code == 201
    visibles = client.get("/api/empresas", headers=headers).json()
    assert [fila["nombre"] for fila in visibles] == ["Ruiz SA"]
    del_admin = client.get("/api/empresas").json()
    assert "Ruiz SA" not in [fila["nombre"] for fila in del_admin]
    assert "Ajena" in [fila["nombre"] for fila in del_admin]
    config = client.get("/api/configuracion", headers=headers).json()
    assert config["nombre_grupo"] == "Grupo Ruiz"
    assert "GTQ" in config["tasas"]


def test_salud_no_expone_la_ruta_de_la_base(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert "url" not in body
    assert "sqlite" not in response.text.lower()


def test_crud_empresa_sucursal_y_transaccion(client):
    empresa = client.post("/api/empresas", json={"nombre": "Norte", "pais": "Guatemala", "moneda_local": "GTQ"}).json()
    otra = client.post("/api/empresas", json={"nombre": "Sur", "pais": "Mexico", "moneda_local": "MXN"}).json()
    sucursal = client.post("/api/sucursales", json={"empresa_id": empresa["id"], "nombre": "Central", "ciudad": "Guatemala"}).json()

    ajena = client.post("/api/transacciones", json={
        "empresa_id": otra["id"],
        "sucursal_id": sucursal["id"],
        "fecha": "2026-11-01",
        "cuenta": "4100",
        "monto": 100,
        "moneda": "MXN",
    })
    assert ajena.status_code == 400

    creada = client.post("/api/transacciones", json={
        "empresa_id": empresa["id"],
        "sucursal_id": sucursal["id"],
        "fecha": "2026-11-01",
        "cuenta": "4100",
        "descripcion": "Venta",
        "monto": 100,
        "moneda": "USD",
        "es_intercompany": "S",
        "empresa_contraparte_id": otra["id"],
    })
    assert creada.status_code == 201
    cuerpo = creada.json()
    assert cuerpo["monto_base"] == 785.0

    editada = client.patch(f"/api/transacciones/{cuerpo['id']}", json={"monto": 2, "moneda": "GTQ", "es_intercompany": "N", "empresa_contraparte_id": None})
    assert editada.status_code == 200
    assert editada.json()["monto_base"] == 2.0
    pista = client.get(f"/api/transacciones/{cuerpo['id']}/auditoria").json()
    assert [evento["accion"] for evento in pista["eventos"]] == ["creada", "editada"]
    assert pista["eventos"][1]["detalle"]["cambios"]["monto"]["despues"] == 2.0
    assert pista["eventos"][1]["usuario"]["email"] == "admin@test.local"

    resumen = client.get("/api/consolidacion/resumen")
    assert resumen.status_code == 200
    assert resumen.json()["consolidado"]["moneda_base"] == "GTQ"

    excel = client.get("/api/exportar/excel")
    assert excel.status_code == 200
    assert excel.headers["content-type"].startswith("application/vnd.openxmlformats")

    csv = client.get("/api/exportacion/csv")
    assert csv.status_code == 200
    assert "text/csv" in csv.headers["content-type"]

    auditoria = client.get("/api/validacion")
    assert auditoria.status_code == 200
    assert "estado" in auditoria.json()

    assert client.delete(f"/api/transacciones/{cuerpo['id']}").status_code == 204
    borrada = client.get(f"/api/transacciones/{cuerpo['id']}/auditoria").json()
    assert borrada["eliminada"] is True
    assert borrada["transaccion"] is None
    assert borrada["eventos"][-1]["accion"] == "eliminada"
    assert client.delete(f"/api/sucursales/{sucursal['id']}").status_code == 204
    assert client.delete(f"/api/empresas/{empresa['id']}").status_code == 204
    assert client.delete(f"/api/empresas/{otra['id']}").status_code == 204
