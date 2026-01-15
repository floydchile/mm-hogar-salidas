import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os
import pandas as pd
from PIL import Image

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="M&M Hogar", page_icon="📦", layout="wide")

st.markdown("""<style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    .stMetric {background-color: #f8f9fa; border-radius: 10px; padding: 10px; border: 1px solid #eee;}
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    input[type=number] { -moz-appearance: textfield; }
</style>""", unsafe_allow_html=True)

# --- CONEXIÓN ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_KEY or not SUPABASE_URL:
    st.error("❌ Error: Faltan las credenciales de Supabase.")
    st.stop()

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()
USUARIOS_VALIDOS = ["pau", "dany", "miguel"]

# --- FUNCIONES ---
def formato_clp(valor):
    return f"${int(valor):,}".replace(",", ".")

def buscar_productos(query: str = ""):
    try:
        db_query = supabase.table("productos").select("*")
        if query:
            db_query = db_query.or_(f"sku.ilike.%{query}%,nombre.ilike.%{query}%")
        return db_query.order("sku").execute().data
    except: return []

def registrar_movimiento(tipo, sku, cantidad, extra_val, usuario, precio=None):
    try:
        if tipo == "entrada":
            if precio is not None:
                supabase.table("productos").update({"precio_costo_contenedor": float(precio)}).eq("sku", sku).execute()
            supabase.rpc("registrar_entrada", {"p_sku": sku, "p_cantidad": int(cantidad), "p_und_x_embalaje": extra_val, "p_usuario": usuario}).execute()
        else:
            res = supabase.rpc("registrar_salida", {"p_sku": sku, "p_cantidad": int(cantidad), "p_canal": extra_val, "p_usuario": usuario}).execute()
            if "ERROR" in res.data: return False, res.data
        return True, "OK"
    except Exception as e: return False, str(e)

# --- LOGIN ---
if 'usuario_ingresado' not in st.session_state: st.session_state.usuario_ingresado = None
if 'form_count' not in st.session_state: st.session_state.form_count = 0
if 'edit_form_count' not in st.session_state: st.session_state.edit_form_count = 0

with st.sidebar:
    if st.session_state.usuario_ingresado:
        st.write(f"Usuario: **{st.session_state.usuario_ingresado.upper()}**")
        if st.button("Cerrar Sesión"):
            st.session_state.usuario_ingresado = None
            st.rerun()
    else:
        u = st.text_input("Usuario:").lower().strip()
        if st.button("Entrar"):
            if u in USUARIOS_VALIDOS:
                st.session_state.usuario_ingresado = u
                st.rerun()

if not st.session_state.usuario_ingresado:
    st.info("Inicie sesión para continuar")
    st.stop()

# --- TABS ---
t1, t2, t3, t4 = st.tabs(["🛒 Movimientos", "📋 Historial", "📈 Stock", "⚙️ Configuración"])

with t1:
    c_v, c_e = st.columns(2)
    with c_v:
        st.subheader("Venta")
        sk_v = st.text_input("Buscar Venta:", key=f"sv_{st.session_state.form_count}").upper()
        if sk_v:
            ps_v = buscar_productos(sk_v)
            if ps_v:
                p_v = st.selectbox("Producto:", ps_v, format_func=lambda x: f"{x['sku']} ({x['stock_total']})", key=f"pv_{st.session_state.form_count}")
                ct_v = st.number_input("Cant:", min_value=1, key=f"cv_{st.session_state.form_count}")
                cn = st.selectbox("Canal:", ["Mercadolibre", "Falabella", "Walmart", "Web", "Retiro"], key=f"cn_{st.session_state.form_count}")
                if st.button("Finalizar Venta"):
                    ok, m = registrar_movimiento("salida", p_v['sku'], ct_v, cn, st.session_state.usuario_ingresado)
                    if ok: st.session_state.form_count += 1; st.rerun()

    with c_e:
        st.subheader("Entrada")
        sk_e = st.text_input("Buscar Entrada:", key=f"se_{st.session_state.form_count}").upper()
        if sk_e:
            ps_e = buscar_productos(sk_e)
            if ps_e:
                p_e = st.selectbox("Producto:", ps_e, format_func=lambda x: x['sku'], key=f"pe_{st.session_state.form_count}")
                ct_e = st.number_input("Cant:", min_value=1, key=f"ce_{st.session_state.form_count}")
                cs_e = st.number_input("Costo:", value=int(p_e['precio_costo_contenedor']), key=f"cse_{st.session_state.form_count}")
                if st.button("Confirmar Entrada"):
                    ok, m = registrar_movimiento("entrada", p_e['sku'], ct_e, p_e['und_x_embalaje'], st.session_state.usuario_ingresado, cs_e)
                    if ok: st.session_state.form_count += 1; st.rerun()

with t2:
    st.subheader("Historial")
    h = []
    try:
        e_d = supabase.table("entradas").select("*").order("fecha", desc=True).limit(20).execute().data
        for x in e_d: x['Tipo'] = "🟢 Entrada"; h.append(x)
        s_d = supabase.table("salidas").select("*").order("fecha", desc=True).limit(20).execute().data
        for x in s_d: x['Tipo'] = "🔴 Venta"; h.append(x)
        if h:
            df_h = pd.DataFrame(h).sort_values("fecha", ascending=False)
            st.dataframe(df_h[["fecha", "Tipo", "sku", "cantidad", "usuario"]], use_container_width=True, hide_index=True)
    except: st.write("Sin datos")

with t3:
    st.subheader("Stock")
    all_p = buscar_productos()
    if all_p:
        df_p = pd.DataFrame(all_p)
        df_p['Inversion'] = (df_p['precio_costo_contenedor'] / df_p['und_x_embalaje'].replace(0,1)) * df_p['stock_total']
        st.metric("Total Inversión", formato_clp(df_p['Inversion'].sum()))
        st.dataframe(df_p[["sku", "nombre", "stock_total"]], use_container_width=True, hide_index=True)

with t4:
    st.subheader("Configuración")
    c_edit, c_new = st.columns(2)
    with c_edit:
        st.write("### Editar")
        q_ed = st.text_input("Buscar:", key=f"q_ed_{st.session_state.edit_form_count}").upper()
        if q_ed:
            ps_ed = buscar_productos(q_ed)
            if ps_ed:
                p_ed = st.selectbox("Seleccione:", ps_ed, format_func=lambda x: x['sku'])
                with st.form(key=f"f_ed_{st.session_state.edit_form_count}"):
                    st.text_input("SKU:", value=p_ed['sku'], disabled=True)
                    n_nm = st.text_input("Nombre:", value=p_ed['nombre'])
                    n_un = st.number_input("Und x Emb:", min_value=1, value=int(p_ed['und_x_embalaje']))
                    n_cs = st.number_input("Costo:", min_value=0, value=int(p_ed['precio_costo_contenedor']))
                    if st.form_submit_button("Actualizar"):
                        supabase.table("productos").update({"nombre": n_nm, "und_x_embalaje": n_un, "precio_costo_contenedor": n_cs}).eq("sku", p_ed['sku']).execute()
                        supabase.table("entradas").insert({"sku": p_ed['sku'], "cantidad": 0, "usuario": f"{st.session_state.usuario_ingresado} (EDIT)"}).execute()
                        st.session_state.edit_form_count += 1
                        st.success("✅ Guardado")
                        st.rerun()

    with c_new:
        st.write("### Nuevo")
        with st.form("f_nw", clear_on_submit=True):
            f_sk = st.text_input("SKU:").upper().strip()
            f_no = st.text_input("Nombre:")
            f_un = st.number_input("Und x Emb:", min_value=1, value=1)
            if st.form_submit_button("Crear"):
                if f_sk and f_no:
                    try:
                        supabase.table("productos").insert({"sku": f_sk, "nombre": f_no, "und_x_embalaje": f_un, "stock_total": 0, "precio_costo_contenedor": 0}).execute()
                        st.success("✅ Creado")
                        st.rerun()
                    except: st.error("Error/Duplicado")
