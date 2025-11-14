# app_vendedores.py
# Ejecuta: streamlit run app_vendedores.py --server.port 8503

import os
import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(page_title="Ventas por Región y Vendedor", layout="wide")
st.title("💻 Testeando Streamlit")
st.title("📊 Dashboard de Ventas")
st.caption("Versión: **v2.0 (map-interactive)** — si no ves este texto, no estás corriendo el archivo actualizado.")

with st.sidebar:
    st.header("⚙️ Configuración")
    up = st.file_uploader("Sube tu archivo Excel (.xlsx)", type=["xlsx"], help="Arrastra o selecciona tu Excel.")
    st.caption("Si no subes nada, intentaré leer **vendedores.xlsx** de esta carpeta.")

@st.cache_data
def load_df(uploaded_file):
    if uploaded_file is not None:
        return pd.read_excel(uploaded_file)
    if os.path.exists("vendedores.xlsx"):
        return pd.read_excel("vendedores.xlsx")
    return pd.DataFrame()

df = load_df(up)
if df.empty:
    st.info("Sube un Excel o coloca **vendedores.xlsx** en la carpeta del proyecto para continuar.")
    st.stop()

# -------- Mapeo interactivo de columnas --------
st.sidebar.subheader("🧭 Mapeo de columnas")
cols = [c for c in df.columns if isinstance(c, str)]
lookup = {c.lower().strip(): c for c in cols}
def guess(keys):
    for k in keys:
        if k in lookup: return lookup[k]
    return None

g_region   = guess(["región","region","zona","area"])
g_vendedor = guess(["vendedor","ejecutivo","asesor","salesperson","nombre","nombre vendedor","vendedores"])
g_unid     = guess(["unidades vendidas","unidades","qty","cantidad"])
g_ventas   = guess(["ventas totales","ventas","monto","sales","importe"])
g_fecha    = guess(["fecha","date"])

c_region = st.sidebar.selectbox("Columna de **Región**",   options=cols, index=(cols.index(g_region)   if g_region   in cols else 0))
c_vend   = st.sidebar.selectbox("Columna de **Vendedor**", options=cols, index=(cols.index(g_vendedor) if g_vendedor in cols else 0))
c_unid   = st.sidebar.selectbox("Columna de **Unidades**", options=cols, index=(cols.index(g_unid)     if g_unid     in cols else 0))
c_ventas = st.sidebar.selectbox("Columna de **Ventas**",   options=cols, index=(cols.index(g_ventas)   if g_ventas   in cols else 0))
use_fecha = st.sidebar.checkbox("Mi archivo tiene **Fecha**", value=bool(g_fecha))
c_fecha = st.sidebar.selectbox("Columna de **Fecha**", options=cols, index=(cols.index(g_fecha) if (use_fecha and g_fecha in cols) else 0)) if use_fecha else None

rename_map = {c_region:"region", c_vend:"vendedor", c_unid:"unidades", c_ventas:"ventas"}
if use_fecha and c_fecha: rename_map[c_fecha] = "fecha"
df = df.rename(columns=rename_map)

df["unidades"] = pd.to_numeric(df["unidades"], errors="coerce")
df["ventas"]   = pd.to_numeric(df["ventas"],   errors="coerce")
if "fecha" in df.columns:
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

st.sidebar.success("✅ Columnas mapeadas. (Si algo no cuadra, cambia la selección arriba.)")
st.sidebar.write("Columnas actuales:", list(df.columns))

needed = {"region","vendedor","unidades","ventas"}
missing = [c for c in needed if c not in df.columns]
if missing:
    st.error(f"Faltan columnas requeridas: {', '.join(missing)}. Ajusta el mapeo en la barra lateral.")
    st.stop()

# -------- Filtros --------
with st.sidebar:
    st.header("🔎 Filtros")
    reg_opts = ["(Todas)"] + sorted(df["region"].dropna().astype(str).unique().tolist())
    reg_sel  = st.selectbox("Región", reg_opts, index=0)

    origen = df if reg_sel=="(Todas)" else df[df["region"].astype(str)==reg_sel]
    vend_opts = ["(Todos)"] + sorted(origen["vendedor"].dropna().astype(str).unique().tolist())
    vend_sel  = st.selectbox("Vendedor", vend_opts, index=0)

    if st.button("🔄 Limpiar filtros"):
        st.experimental_rerun()

mask = pd.Series(True, index=df.index)
if reg_sel  != "(Todas)": mask &= df["region"].astype(str).eq(reg_sel)
if vend_sel != "(Todos)": mask &= df["vendedor"].astype(str).eq(vend_sel)
df_f = df.loc[mask].copy()

# -------- Métricas --------
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("🧾 Registros", len(df_f))
with c2: st.metric("📦 Unidades", int(df_f["unidades"].sum()))
with c3: st.metric("💰 Ventas Totales", f"${df_f['ventas'].sum():,.2f}")
with c4:
    pct_global = 0 if df["ventas"].sum()==0 else (df_f["ventas"].sum()/df["ventas"].sum())*100
    st.metric("📊 % del Total Global", f"{pct_global:.2f}%")

# -------- Tabla + descarga --------
st.subheader("📋 Tabla (según filtros)")
st.dataframe(df_f, use_container_width=True, height=360)
st.download_button("⬇️ Descargar CSV filtrado",
                   data=df_f.to_csv(index=False),
                   file_name="ventas_filtrado.csv",
                   mime="text/csv")

# -------- Gráficas --------
st.subheader("📈 Visualizaciones")
def agg(by):
    g = df_f.groupby(by, dropna=True).agg(
        unidades=("unidades","sum"),
        ventas=("ventas","sum")
    ).reset_index()
    total = g["ventas"].sum()
    g["pct_ventas"] = (g["ventas"]/total*100).round(2) if total else 0
    return g

tab1, tab2, tab3 = st.tabs(["Unidades Vendidas", "Ventas Totales", "% de Ventas"])

with tab1:
    by = st.radio("Agrupar por", ["region","vendedor"], horizontal=True, key="u_by")
    d = agg(by)
    chart = (alt.Chart(d).mark_bar()
             .encode(x=by, y="unidades:Q", tooltip=[by, alt.Tooltip("unidades:Q", format=",.0f")])
             .properties(height=360))
    st.altair_chart(chart, use_container_width=True)

with tab2:
    by = st.radio("Agrupar por", ["region","vendedor"], horizontal=True, key="v_by")
    d = agg(by)
    chart = (alt.Chart(d).mark_bar()
             .encode(x=by, y="ventas:Q", tooltip=[by, alt.Tooltip("ventas:Q", format="$,.2f")])
             .properties(height=360))
    st.altair_chart(chart, use_container_width=True)

with tab3:
    by = st.radio("Agrupar por", ["region","vendedor"], horizontal=True, key="p_by")
    d = agg(by)
    chart = (alt.Chart(d).mark_bar()
             .encode(x=by, y="pct_ventas:Q", tooltip=[by, "pct_ventas:Q"])
             .properties(height=360))
    st.altair_chart(chart, use_container_width=True)

# -------- Detalle por vendedor --------
st.subheader("🧑‍💼 Detalle de Vendedor")
vend_list = sorted(df_f["vendedor"].dropna().astype(str).unique().tolist())
if len(vend_list) == 0:
    st.info("No hay vendedores en el filtro actual.")
else:
    vend_det = st.selectbox("Selecciona vendedor", vend_list)
    df_v = df_f[df_f["vendedor"].astype(str)==vend_det]
    mc1, mc2, mc3 = st.columns(3)
    with mc1: st.metric("📦 Unidades (vendedor)", int(df_v["unidades"].sum()))
    with mc2: st.metric("💰 Ventas (vendedor)", f"${df_v['ventas'].sum():,.2f}")
    with mc3:
        pct = 0 if df_f["ventas"].sum()==0 else (df_v["ventas"].sum()/df_f["ventas"].sum())*100
        st.metric("📊 % dentro del filtro", f"{pct:.2f}%")
    st.dataframe(df_v, use_container_width=True, height=280)

st.caption("Hecho con ❤️ en Streamlit por AlejandraGlz. ")
