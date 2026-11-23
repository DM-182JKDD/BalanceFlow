from services.consolidacion import TASAS_CAMBIO


def convertir_a_moneda_base(monto: float, moneda_origen: str, moneda_base: str = "GTQ") -> float:
    """Convierte usando la misma tabla de tasas que el motor de consolidación."""
    origen = (moneda_origen or "GTQ").upper()
    base = (moneda_base or "GTQ").upper()
    if origen not in TASAS_CAMBIO or base not in TASAS_CAMBIO or TASAS_CAMBIO[base] == 0:
        return 0.0
    en_gtq = float(monto) * TASAS_CAMBIO[origen]
    return round(en_gtq / TASAS_CAMBIO[base], 2)

