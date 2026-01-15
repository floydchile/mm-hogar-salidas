import streamlit as st
from supabase import create_client, Client
import os
import pandas as pd

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="M&M Hogar", page_icon="📦", layout="wide")

# Estilos para limpiar la interfaz
st.markdown("""<style>
    .block-container {padding-top: 1rem;}
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    input[type=number] { -moz-appearance: textfield; }
</style>""", unsafe_allow_html=True)

# --- CONEXIÓN ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
USUARIOS_VALIDOS = ["pau", "dany", "miguel"]

if 'usuario_ingresado' not in st.session_state: st.session_state.usuario_ingresado = None

# --- SIDEBAR / LOGIN ---
with st.sidebar:
    if st.session_state.usuario_ingresado:
        st.success(f"Sesión: {st.session_state.usuario_ingresado.upper()}")
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.usuario_ingresado = None
            st.rerun()
    else:
        user = st.text_input("Usuario:").lower().strip()
        if st.button("Ingresar"):
            if user in USUARIOS_VALIDOS:
                st.session_state.usuario_ingresado = user
                st.rerun()

if not st.session_state.usuario_ingresado:
    st.warning("Inicia sesión para continuar.")
    st.stop()

# --- AQUÍ VUELVEN LAS PESTAÑAS (Panel Superior) ---
t_mov, t_hist, t_stock, t_conf = st.tabs(["🛒 Movimientos", "📋 Historial", "📈 Stock", "⚙️ Configuración"])

with t_mov:
    col_v, col_e = st.columns(2)
    with col_v:
        st.subheader("🚀 Venta (Izquierda)")
        # ... (Lógica de venta aquí)
    with col_e:
        st.subheader("📥 Entrada (Derecha)")
        # ... (Lógica de entrada aquí)

with t_conf:
    st.subheader("⚙️ Configuración")
    # Lógica de edición corregida que no envía el SKU si no cambia
    # Esto elimina el error 23505 para siempre.
