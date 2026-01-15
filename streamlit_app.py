import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os
import pandas as pd
from PIL import Image
import re

# --- CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="M&M Hogar", page_icon="📦", layout="wide")

st.markdown("""<style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    .stMetric {background-color: #f8f9fa; border-radius: 10px; padding: 10px; border: 1px solid #eee;}
    [data-testid="stMetricValue"] {font-size: 1.8rem;}
    /* Quitar botones +/- de los inputs numéricos */
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    input[type=number] { -moz-appearance: textfield; }
</style>""", unsafe_allow_html=True)

# Carga de Logo
try:
    logo = Image.open("assets/mym_hogar.png")
except:
    logo = None

# --- CONEXIÓN ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_KEY or not SUPABASE_URL:
    st.error("❌ Error: Faltan las credenciales de Supabase en Railway.")
    st.stop()

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()
USUARIOS_VALIDOS = ["pau", "dany", "miguel"]

# --- FUNCIONES AUXILIARES ---
def formato_clp(valor):
    return f"${int(valor):,}".replace(",", ".")

def buscar_productos(query: str = ""):
    try:
        db_query = supabase.table("productos").select("*")
        if query:
            db_query = db_query.or_(f"sku.ilike.%{query}%,nombre.ilike.%{query}%")
        return db_query.order("sku").execute().data
    except Exception as e:
        st.error(f"Error al buscar: {e}")
        return []

# --- LÓGICA DE NEGOCIO ---
def registrar_movimiento(tipo, sku, cantidad, extra_val, usuario, precio=None):
    try:
        if tipo == "entrada":
            if precio is not None:
                supabase.table("productos").update({"precio_costo_contenedor": float(precio)}).eq("sku", sku).execute()
            supabase.rpc("registrar_entrada", {
                "p_sku": sku, "p_cantidad": int(cantidad), 
                "p_und_x_embalaje": extra_val, "p_usuario": usuario
            }).execute()
        else:
            res = supabase.rpc("registrar_salida", {
                "p_sku": sku, "p_cantidad": int(cantidad), 
                "p_canal": extra_val, "p_usuario": usuario
            }).execute()
            if "ERROR" in res.data: return False, res.data
        return True, "Operación exitosa"
    except Exception as e:
        return False, str(e)

# --- INTERFAZ USUARIO ---
if 'usuario_ingresado' not in st.session_state: st.session_state.usuario_ingresado = None
if 'form_count' not in st.session_state: st.session_state.form_count = 0
if 'edit_form_count' not in st.session_state: st.session_state.edit_form_count = 0

with st.sidebar:
    if logo: st.image(logo, width=150)
    if st.session_state.usuario_ingresado:
        st.success(f"Sesión: {st.session_state.usuario_ingresado.upper()}")
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            st.session_state.usuario_ingresado = None
            st.rerun()
    else:
        user = st.text_input("Usuario:").lower().strip()
        if st.button("✅ Ingresar", use_container_width=True, type="primary"):
            if user in USUARIOS_VALIDOS:
                st.session_state.usuario_ingresado = user
                st.rerun()
            else: st.error("Usuario inválido")

if not st.session_state.usuario_ingresado:
    st.title("📦 M&M Hogar")
    st.info("👋 Por favor ingresa tu usuario en el menú lateral.")
    st.stop()

st.title("📦 M&M Hogar - Gestión")
t1, t2, t3, t4 = st.tabs(["🛒 Movimientos", "📋 Historial", "📈 Stock e Inventario", "⚙️ Configuración"])

# --- TAB 1: MOVIMIENTOS ---
with t1:
    col_venta, col_entrada = st.columns(2)
    with col_venta:
        st.subheader("🚀 Registro de Venta")
        sku_out = st.text_input("Buscar para Venta:", key=f"out_search_{st.session_state.form_count}").upper()
        if sku_out:
            prods_v = buscar_productos(sku_out)
            if prods_v:
                p_v_sel = st.selectbox("Seleccionar:", prods_v, format_func=lambda x: f"{x['sku']} - {x['nombre']} (Disp: {x['stock_total']})", key=f"sb_out_{st.session_state.form_count}")
                cant_v = st.number_input("Cantidad:", min_value=1, key=f"n2_{st.session_state.form_count}")
                canal = st.selectbox("Canal:", ["Mercadolibre", "Falabella", "Walmart", "Hites", "Paris", "Web", "WhatsApp", "Retiro"], key=f"canal_{st.session_state.form_count}")
                if p_v_sel['stock_total'] < cant_v: st.warning(f"Stock insuficiente: {p_v_sel['stock_total']}")
                if st.button("🚀 Finalizar Venta", type="primary", use_container_width=True):
                    ok, msg = registrar_movimiento("salida", p_v_sel['sku'], cant_v, canal, st.session_state.usuario_ingresado)
                    if ok: 
                        st.session_state.form_count += 1
                        st.success("Venta guardada!"); st.rerun()

    with col_entrada:
        st.subheader("📥 Entrada de Stock")
        sku_in = st.text_input("Buscar para Entrada:", key=f"in_search_{st.session_state.form_count}").upper()
        if sku_in:
            prods = buscar_productos(sku_in)
            if prods:
                p_sel = st.selectbox("Seleccionar:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']}", key=f"sb_in_{st.session_state.form_count}")
                cant = st.number_input("Cantidad:", min_value=1, key=f"n1_{st.session_state.form_count}")
                costo = st.number_input("C
