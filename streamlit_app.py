import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os
import pandas as pd
from PIL import Image
import re

# CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="M&M Hogar", page_icon="📦", layout="wide")

# ESTILOS
st.markdown("""<style>
    .block-container {padding-top: 1rem;}
    [data-testid="stMetricValue"] {font-size: 1.8rem;}
</style>""", unsafe_allow_html=True)

# CONEXIÓN SUPABASE (Usando Variables de Entorno)
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

# --- FUNCIONES DE LÓGICA DE NEGOCIO ---

def buscar_productos_db(query: str = ""):
    """Busca productos directamente en la base de datos (más rápido)"""
    try:
        db_query = supabase.table("productos").select("*")
        if query:
            # Filtra por SKU o Nombre usando ILIKE (no distingue mayúsculas)
            db_query = db_query.or_(f"sku.ilike.%{query}%,nombre.ilike.%{query}%")
        response = db_query.order("sku").execute()
        return response.data
    except Exception as e:
        st.error(f"Error al buscar: {e}")
        return []

def ejecutar_entrada(sku, cantidad, und_emb, usuario, precio_costo):
    """Llama a la función SQL segura en Supabase"""
    try:
        # Primero actualizamos el precio de costo (operación simple)
        supabase.table("productos").update({
            "precio_costo_contenedor": float(precio_costo)
        }).eq("sku", sku).execute()
        
        # Luego ejecutamos la entrada atómica (Stock + Registro)
        supabase.rpc("registrar_entrada", {
            "p_sku": sku,
            "p_cantidad": int(cantidad),
            "p_und_x_embalaje": int(und_emb),
            "p_usuario": usuario
        }).execute()
        return True, "✅ Entrada registrada con éxito"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def ejecutar_salida(sku, cantidad, canal, usuario):
    """Llama a la función SQL segura en Supabase con chequeo de stock"""
    try:
        response = supabase.rpc("registrar_salida", {
            "p_sku": sku,
            "p_cantidad": int(cantidad),
            "p_canal": canal,
            "p_usuario": usuario
        }).execute()
        
        if "ERROR" in response.data:
            return False, response.data
        return True, "✅ Venta registrada correctamente"
    except Exception as e:
        return False, f"❌ Error de sistema: {str(e)}"

# --- INTERFAZ ---

# Session State Initialization
if 'usuario_ingresado' not in st.session_state: st.session_state.usuario_ingresado = None

with st.sidebar:
    if st.session_state.usuario_ingresado:
        st.success(f"Usuario: {st.session_state.usuario_ingresado.upper()}")
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.usuario_ingresado = None
            st.rerun()
    else:
        user = st.text_input("Usuario:").lower().strip()
        if st.button("Ingresar"):
            if user in USUARIOS_VALIDOS:
                st.session_state.usuario_ingresado = user
                st.rerun()
            else: st.error("Usuario no autorizado")
    st.divider()

# HEADER
st.title("📦 M&M Hogar - Inventario")
if not st.session_state.usuario_ingresado:
    st.warning("Inicia sesión para operar.")
    st.stop()

tabs = st.tabs(["🛒 Movimientos", "📋 Historial", "📈 Stock y Costos", "🔧 Configuración"])

# --- TAB 1: MOVIMIENTOS (ENTRADAS Y SALIDAS) ---
with tabs[0]:
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.subheader("📥 Entrada de Mercadería")
        search_in = st.text_input("Buscar producto para entrada:", key="search_in")
        results = buscar_productos_db(search_in)
        
        if search_in and results:
            selected_prod = st.selectbox("Selecciona producto:", results, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
            cant_in = st.number_input("Cantidad Unidades:", min_value=1, key="cant_in")
            costo = st.number_input("Precio Costo Contenedor:", value=float(selected_prod['precio_costo_contenedor']), key="cost_in")
            
            if st.button("Registrar Entrada", type="primary"):
                ok, msg = ejecutar_entrada(selected_prod['sku'], cant_in, selected_prod['und_x_embalaje'], st.session_state.usuario_ingresado, costo)
                if ok: st.success(msg); st.balloons()
                else: st.error(msg)
        elif search_in:
            st.info("No se encontró el producto. Créalo en 'Configuración'.")

    with col_b:
        st.subheader("📤 Registrar Venta")
        search_out = st.text_input("Buscar producto para venta:", key="search_out")
        results_out = buscar_productos_db(search_out)
        
        if search_out and results_out:
            selected_out = st.selectbox("Selecciona producto:", results_out, format_func=lambda x: f"{x['sku']} - {x['nombre']}", key="sel_out")
            cant_out = st.number_input("Cantidad:", min_value=1, key="cant_out")
            canal = st.selectbox("Canal:", ["Mercadolibre", "Falabella", "Walmart", "Web", "WhatsApp", "Retiro"], key="canal")
            
            if st.button("Finalizar Venta", type="primary"):
                ok, msg = ejecutar_salida(selected_out['sku'], cant_out, canal, st.session_state.usuario_ingresado)
                if ok: st.success(msg); st.rerun()
                else: st.error(msg)

# --- TAB 2: HISTORIAL ---
with tabs[1]:
    st.subheader("Movimientos Recientes")
    tipo_h = st.radio("Ver:", ["Todo", "Entradas", "Ventas"], horizontal=True)
    
    data = []
    if tipo_h in ["Todo", "Entradas"]:
        ent = supabase.table("entradas").select("*").order("fecha", desc=True).limit(50).execute().data
        for e in ent: e['tipo'] = "🟢 ENTRADA"; data.append(e)
    if tipo_h in ["Todo", "Ventas"]:
        sal = supabase.table("salidas").select("*").order("fecha", desc=True).limit(50).execute().data
        for s in sal: s['tipo'] = "🔴 VENTA"; data.append(s)
    
    if data:
        df = pd.DataFrame(data).sort_values("fecha", ascending=False)
        st.dataframe(df[["fecha", "tipo", "sku", "cantidad", "usuario"]], use_container_width=True)
    else: st.info("No hay datos.")

# --- TAB 3: STOCK Y COSTOS ---
with tabs[2]:
    st.subheader("Estado de Inventario")
    prods = buscar_productos_db()
    if prods:
        df_p = pd.DataFrame(prods)
        df_p['Inversión'] = (df_p['precio_costo_contenedor'] / df_p['und_x_embalaje']) * df_p['stock_total']
        
        m1, m2 = st.columns(2)
        m1.metric("Inversión Total", f"${df_p['Inversión'].sum():,.0f}")
        m2.metric("Total Unidades", int(df_p['stock_total'].sum()))
        
        st.dataframe(df_p[["sku", "nombre", "stock_total", "und_x_embalaje", "precio_costo_contenedor", "Inversión"]], use_container_width=True)

# --- TAB 4: CONFIGURACIÓN ---
with tabs[3]:
    st.subheader("Crear Nuevo Producto")
    with st.form("nuevo_p"):
        c1, c2, c3 = st.columns(3)
        n_sku = c1.text_input("SKU (Único)").upper().strip()
        n_nom = c2.text_input("Nombre")
        n_und = c3.number_input("Unidades por Embalaje", min_value=1, value=1)
        if st.form_submit_button("Crear Producto"):
            try:
                supabase.table("productos").insert({"sku": n_sku, "nombre": n_nom, "und_x_embalaje": n_und, "stock_total": 0}).execute()
                st.success("Producto creado")
            except Exception as e: st.error(f"Error: {e}")
