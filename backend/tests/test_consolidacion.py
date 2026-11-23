import json

from services.consolidacion import consolidar_grupo, convertir_a_moneda_base
from services.validacion import validar_transacciones


def test_conversion_usd_usa_la_tasa_del_grupo():
    assert convertir_a_moneda_base(10, "USD") == 78.5
    assert convertir_a_moneda_base(10, "XYZ") == 0.0


def test_par_intercompany_se_elimina_cuando_cuadra_en_gtq():
    resultado = consolidar_grupo([
        {"id": 1, "empresa_id": 1, "cuenta": "4100", "monto": 100, "moneda": "GTQ", "es_intercompany": "S", "empresa_contraparte_id": 2},
        {"id": 2, "empresa_id": 2, "cuenta": "5100", "monto": -785, "moneda": "USD", "es_intercompany": "S", "empresa_contraparte_id": 1},
    ])
    # 100 GTQ no cuadra con 785 USD. El caso que sí cuadra:
    cuadrado = consolidar_grupo([
        {"id": 1, "empresa_id": 1, "cuenta": "4100", "monto": 7850, "moneda": "GTQ", "es_intercompany": "S", "empresa_contraparte_id": 2},
        {"id": 2, "empresa_id": 2, "cuenta": "5100", "monto": -1000, "moneda": "USD", "es_intercompany": "S", "empresa_contraparte_id": 1},
    ])
    assert resultado["intercompany"]["resumen"]["eliminadas"] == 0
    assert cuadrado["intercompany"]["resumen"]["eliminadas"] == 1
    assert cuadrado["consolidado"]["total_ingresos"] == 0


def test_el_consolidado_no_incluye_nan():
    resultado = consolidar_grupo([
        {"id": 1, "empresa_id": 1, "sucursal_id": None, "cuenta": "4100", "monto": 10, "moneda": "GTQ", "es_intercompany": "S"},
        {"id": 2, "empresa_id": 1, "sucursal_id": 3, "cuenta": "5100", "monto": 4, "moneda": "GTQ", "es_intercompany": "N"},
    ])
    json.dumps(resultado)
    assert resultado["intercompany"]["descuadres"][0]["datos"]["sucursal_id"] is None


def test_aduana_detecta_moneda_invalida():
    reporte = validar_transacciones([
        {"empresa_id": 1, "fecha": "2026-11-21", "cuenta": "4100", "monto": 10, "moneda": "XYZ", "descripcion": "x", "es_intercompany": "N"},
    ])
    assert reporte["estado"] == "CON_ERRORES"
    assert reporte["errores"][0]["tipo"] == "MONEDA_INVALIDA"
