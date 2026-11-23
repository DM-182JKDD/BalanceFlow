import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="BalanceFlow | Consolidación", page_icon="📊", layout="wide")

API_URL = "http://127.0.0.1:8000"

st.title("BalanceFlow — Consolidación")
st.caption("Este panel usa las mismas rutas que la aplicación React.")

if "token" not in st.session_state:
    st.session_state.token = ""

with st.sidebar:
    st.header("Sesión")
    email = st.text_input("Correo", value="admin@balanceflow.local")
    password = st.text_input("Contraseña", type="password")
    if st.button("Entrar", use_container_width=True):
        try:
            respuesta = requests.post(
                f"{API_URL}/api/auth/login",
                json={"email": email, "password": password},
                timeout=15,
            )
            if respuesta.status_code == 200:
                st.session_state.token = respuesta.json()["access_token"]
                st.success("Sesión iniciada")
            else:
                st.error(respuesta.json().get("detail", "No se pudo entrar"))
        except requests.RequestException:
            st.error("El backend no responde en http://127.0.0.1:8000")

token = st.session_state.token
if not token:
    st.info("Inicia sesión para ver el consolidado.")
    st.stop()

headers = {"Authorization": f"Bearer {token}"}

try:
    empresas = requests.get(f"{API_URL}/api/empresas", headers=headers, timeout=15).json()
    resumen = requests.get(f"{API_URL}/api/consolidacion/resumen", headers=headers, timeout=30).json()
except requests.RequestException:
    st.error("No se pudo leer el consolidado.")
    st.stop()

consolidado = resumen.get("consolidado", {})
columnas = st.columns(4)
columnas[0].metric("Ingresos", f"{consolidado.get('total_ingresos', 0):,.2f} {consolidado.get('moneda_base', 'GTQ')}")
columnas[1].metric("Gastos", f"{consolidado.get('total_gastos', 0):,.2f}")
columnas[2].metric("NOPAT", f"{consolidado.get('total_nopat', 0):,.2f}")
columnas[3].metric("Pares eliminados", resumen.get("intercompany", {}).get("resumen", {}).get("eliminadas", 0))

nombres = {empresa["id"]: empresa["nombre"] for empresa in empresas}
detalle = resumen.get("por_empresa") or []
if detalle:
    tabla = pd.DataFrame(detalle)
    tabla["empresa"] = tabla["empresa_id"].map(lambda valor: nombres.get(valor, f"Empresa {valor}"))
    st.bar_chart(tabla.set_index("empresa")[["ingresos", "gastos"]])
    st.dataframe(tabla, use_container_width=True)
else:
    st.info("Aún no hay transacciones consolidadas.")

st.subheader("Cargar archivo")
opciones = {empresa["nombre"]: empresa["id"] for empresa in empresas}
if opciones:
    nombre = st.selectbox("Empresa", list(opciones))
    archivo = st.file_uploader("CSV o Excel", type=["csv", "xlsx", "xls"])
    if st.button("Importar") and archivo is not None:
        respuesta = requests.post(
            f"{API_URL}/api/uploads/excel",
            headers=headers,
            files={"archivo": (archivo.name, archivo.getvalue())},
            data={"empresa_id": opciones[nombre], "moneda_default": "GTQ"},
            timeout=60,
        )
        if respuesta.ok:
            cuerpo = respuesta.json()
            st.success(f"{cuerpo.get('transacciones_insertadas', 0)} registros importados. En cuarentena: {cuerpo.get('filas_en_cuarentena', 0)}.")
        else:
            st.error(respuesta.json().get("detail", "La carga falló"))
