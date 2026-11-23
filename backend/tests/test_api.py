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
    assert client.delete(f"/api/sucursales/{sucursal['id']}").status_code == 204
    assert client.delete(f"/api/empresas/{empresa['id']}").status_code == 204
    assert client.delete(f"/api/empresas/{otra['id']}").status_code == 204
