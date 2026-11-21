"""
Servicio de consolidación: convierte monedas, elimina intercompany
y calcula indicadores financieros (ROIC, ROCE, EVA).
"""
from collections import defaultdict
from typing import Any

import pandas as pd


# Tasas de cambio ficticias para el hackathon (1 unidad de moneda = X GTQ)
TASAS_CAMBIO = {
    "GTQ": 1.0,
    "USD": 7.85,
    "EUR": 8.55,
    "MXN": 0.45,
    "CRC": 0.015,
    "HNL": 0.32,
    "NIO": 0.21,
    "PAB": 7.85,
}

MONEDA_BASE = "GTQ"


class ErrorConsolidacion(Exception):
    """Error controlado en la consolidación."""
    pass


# ==================== CONVERSIÓN DE MONEDAS ====================

def convertir_a_moneda_base(monto: float, moneda: str) -> float:
    """
    Convierte un monto a GTQ (moneda base del grupo).
    Si la moneda es inválida, devuelve 0.0 y NO rompe la consolidación
    (la aduana ya la marcó como error en el paso de validación).
    """
    moneda = str(moneda).upper().strip()
    if moneda not in TASAS_CAMBIO:
        return 0.0
    return round(float(monto) * TASAS_CAMBIO[moneda], 2)


def convertir_dataframe(df: pd.DataFrame, columna_monto: str = "monto", columna_moneda: str = "moneda") -> pd.DataFrame:
    """Agrega columna monto_base con todos los montos convertidos a GTQ."""
    df = df.copy()
    df["monto_base"] = df.apply(
        lambda r: convertir_a_moneda_base(r[columna_monto], r[columna_moneda]),
        axis=1,
    )
    return df


# ==================== ELIMINACIÓN INTERCOMPANY ====================

def eliminar_intercompany(transacciones: list[dict]) -> dict:
    """
    Cruza transacciones intercompany entre empresas del grupo.
    Compara en MONEDA BASE (monto_base) con tolerancia de 0.5 GTQ.
    Devuelve:
      - transacciones_limpias: sin las ventas internas duplicadas
      - eliminadas: lista de las que se eliminaron (con su espejo)
      - descuadres: pares que no cuadran (para reporte)
    """
    intercompany = [t for t in transacciones if str(t.get("es_intercompany", "N")).upper() == "S"]
    normales = [t for t in transacciones if str(t.get("es_intercompany", "N")).upper() != "S"]

    eliminadas = []
    descuadres = []
    usadas = set()

    for i, tx in enumerate(intercompany):
        if i in usadas:
            continue

        contraparte_id = tx.get("empresa_contraparte_id")
        monto_base = round(float(tx.get("monto_base", tx.get("monto", 0)) or 0), 2)

        if contraparte_id is None:
            descuadres.append({
                "tipo": "SIN_CONTRAPARTE",
                "mensaje": f"Transacción intercompany sin empresa_contraparte_id (fila {tx.get('fila_origen')})",
                "datos": tx,
            })
            continue

        # Buscar el espejo comparando en MONEDA BASE
        espejo_idx = None
        for j, other in enumerate(intercompany):
            if j <= i or j in usadas:
                continue
            other_base = round(float(other.get("monto_base", other.get("monto", 0)) or 0), 2)
            if (
                other.get("empresa_id") == contraparte_id
                and abs(other_base - monto_base) < 0.5  # tolerancia 0.5 GTQ
            ):
                espejo_idx = j
                break

        if espejo_idx is None:
            descuadres.append({
                "tipo": "ASIMETRICO",
                "mensaje": f"Venta de empresa {tx.get('empresa_id')} a {contraparte_id} por {monto_base} GTQ sin espejo",
                "datos": tx,
            })
            continue

        # Par encontrado: eliminar ambos
        usadas.add(i)
        usadas.add(espejo_idx)
        eliminadas.append({
            "empresa_origen": tx.get("empresa_id"),
            "empresa_destino": contraparte_id,
            "monto": monto_base,
            "moneda": MONEDA_BASE,
            "fila_origen": tx.get("fila_origen"),
            "fila_espejo": intercompany[espejo_idx].get("fila_origen"),
        })

    # Quedan las normales + las intercompany que no se eliminaron (sin espejo)
    intercompany_no_eliminadas = [t for idx, t in enumerate(intercompany) if idx not in usadas]
    transacciones_limpias = normales + intercompany_no_eliminadas

    return {
        "transacciones_limpias": transacciones_limpias,
        "eliminadas": eliminadas,
        "descuadres": descuadres,
        "resumen": {
            "total_original": len(transacciones),
            "total_limpio": len(transacciones_limpias),
            "eliminadas": len(eliminadas),
            "descuadres": len(descuadres),
        },
    }


# ==================== INDICADORES FINANCIEROS ====================

def calcular_indicadores_por_empresa(transacciones: list[dict]) -> dict:
    """
    Calcula ROIC, ROCE y EVA por empresa usando las transacciones.
    Fórmulas simplificadas para el hackathon:
      - NOPAT = Ingresos (cuentas 4xxx) - Gastos (cuentas 5xxx)
      - Capital invertido = Activos (1xxx) - Pasivos corrientes (2xxx)
      - ROIC = NOPAT / Capital invertido
      - ROCE = EBIT / Capital empleado (activos - pasivos corrientes)
      - EVA = NOPAT - (Capital invertido × WACC)
    """
    WACC = 0.10  # 10% costo de capital (ficticio para el hackathon)

    por_empresa: dict[int, dict] = defaultdict(lambda: {
        "ingresos": 0.0,
        "gastos": 0.0,
        "activos": 0.0,
        "pasivos": 0.0,
    })

    for tx in transacciones:
        emp_id = tx.get("empresa_id")
        cuenta = str(tx.get("cuenta", ""))
        monto = float(tx.get("monto_base", tx.get("monto", 0)) or 0)

        if cuenta.startswith("4"):
            por_empresa[emp_id]["ingresos"] += monto
        elif cuenta.startswith("5"):
            por_empresa[emp_id]["gastos"] += monto
        elif cuenta.startswith("1"):
            por_empresa[emp_id]["activos"] += monto
        elif cuenta.startswith("2"):
            por_empresa[emp_id]["pasivos"] += monto

    resultados = {}
    for emp_id, datos in por_empresa.items():
        ingresos = datos["ingresos"]
        gastos = abs(datos["gastos"])  # gastos suelen venir negativos
        nopat = ingresos - gastos
        capital_invertido = max(datos["activos"] - datos["pasivos"], 1.0)
        ebit = nopat  # simplificación
        capital_empleado = max(datos["activos"] - datos["pasivos"], 1.0)

        roic = nopat / capital_invertido if capital_invertido else 0.0
        roce = ebit / capital_empleado if capital_empleado else 0.0
        eva = nopat - (capital_invertido * WACC)

        resultados[emp_id] = {
            "empresa_id": emp_id,
            "ingresos": round(ingresos, 2),
            "gastos": round(gastos, 2),
            "nopat": round(nopat, 2),
            "capital_invertido": round(capital_invertido, 2),
            "roic": round(roic, 4),
            "roce": round(roce, 4),
            "eva": round(eva, 2),
            "wacc": WACC,
        }

    return resultados


def consolidar_grupo(transacciones: list[dict]) -> dict:
    """
    Pipeline completo de consolidación:
      1. Convertir todas las transacciones a moneda base
      2. Eliminar intercompany
      3. Calcular indicadores por empresa
      4. Calcular consolidado del grupo
    """
    if not transacciones:
        raise ErrorConsolidacion("No hay transacciones para consolidar.")

    # 1. Convertir a moneda base
    df = pd.DataFrame(transacciones)
    if "monto_base" not in df.columns or df["monto_base"].isna().all():
        df = convertir_dataframe(df, "monto", "moneda")

    transacciones_convertidas = df.to_dict(orient="records")

    # 2. Eliminar intercompany
    limpieza = eliminar_intercompany(transacciones_convertidas)
    transacciones_limpias = limpieza["transacciones_limpias"]

    # 3. Indicadores por empresa
    indicadores = calcular_indicadores_por_empresa(transacciones_limpias)

    # 4. Consolidado del grupo
    total_ingresos = sum(i["ingresos"] for i in indicadores.values())
    total_gastos = sum(i["gastos"] for i in indicadores.values())
    total_nopat = total_ingresos - total_gastos
    total_capital = sum(i["capital_invertido"] for i in indicadores.values())
    total_eva = sum(i["eva"] for i in indicadores.values())

    consolidado = {
        "moneda_base": MONEDA_BASE,
        "empresas_incluidas": list(indicadores.keys()),
        "total_ingresos": round(total_ingresos, 2),
        "total_gastos": round(total_gastos, 2),
        "total_nopat": round(total_nopat, 2),
        "total_capital_invertido": round(total_capital, 2),
        "roic_grupo": round(total_nopat / total_capital, 4) if total_capital else 0.0,
        "eva_grupo": round(total_eva, 2),
    }

    return {
        "consolidado": consolidado,
        "por_empresa": list(indicadores.values()),
        "intercompany": {
            "eliminadas": limpieza["eliminadas"],
            "descuadres": limpieza["descuadres"],
            "resumen": limpieza["resumen"],
        },
        "transacciones_limpias": transacciones_limpias,
    }


# ==================== EXPLICADOR DE DESVIACIONES ====================

def explicar_desviacion(
    consolidado_actual: dict,
    consolidado_anterior: dict | None = None,
) -> dict:
    """
    Compara dos consolidados y explica las desviaciones con causa raíz.
    Si no hay anterior, compara contra cero.
    """
    if consolidado_anterior is None:
        consolidado_anterior = {
            "total_ingresos": 0, "total_gastos": 0, "total_nopat": 0,
            "total_capital_invertido": 0, "roic_grupo": 0, "eva_grupo": 0,
        }

    explicaciones = []
    campos = ["total_ingresos", "total_gastos", "total_nopat", "roic_grupo", "eva_grupo"]

    for campo in campos:
        actual = consolidado_actual.get(campo, 0)
        anterior = consolidado_anterior.get(campo, 0)
        if anterior == 0:
            continue
        variacion = actual - anterior
        pct = (variacion / abs(anterior)) * 100 if anterior else 0

        if abs(pct) >= 1.0:  # Solo mostrar cambios > 1%
            explicaciones.append({
                "campo": campo,
                "valor_anterior": round(anterior, 2),
                "valor_actual": round(actual, 2),
                "variacion_absoluta": round(variacion, 2),
                "variacion_pct": round(pct, 2),
                "direccion": "subió" if variacion > 0 else "bajó",
            })

    return {
        "explicaciones": explicaciones,
        "total_cambios": len(explicaciones),
    }