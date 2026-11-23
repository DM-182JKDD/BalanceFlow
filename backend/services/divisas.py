from services.consolidacion import convertir_a_moneda_base as _convertir


def convertir_a_moneda_base(monto: float, moneda_origen: str, moneda_base: str = "GTQ") -> float:
    """Convierte usando la misma tabla y el mismo redondeo que el motor de consolidación."""
    return _convertir(monto, moneda_origen, moneda_destino=moneda_base)
