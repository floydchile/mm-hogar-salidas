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
    """Formatea números a moneda chilena: $1.234.567"""
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

# --- LÓGICA DE NEGOCIO (RPC) ---
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

# --- TABS PRINCIPALES ---
st.title("📦 M&M Hogar - Sistema de Gestión")
t1, t2, t3, t4 = st.tabs(["🛒 Movimientos", "📋 Historial", "📈 Stock e Inventario", "⚙️ Configuración"])

with t1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📥 Entrada de Stock")
        sku_in = st.text_input("Buscar SKU para Entrada:").upper()
        if sku_in:
            prods = buscar_productos(sku_in)
            if prods:
                p = prods[0]
                st.info(f"Producto: {p['nombre']} | Stock: {p['stock_total']}")
                cant = st.number_input("Cantidad a ingresar:", min_value=1, key="n1")
                costo = st.number_input("Costo Contenedor (CLP):", value=int(p['precio_costo_contenedor']), step=1000)
                if st.button("📥 Confirmar Entrada", type="primary"):
                    ok, msg = registrar_movimiento("entrada", p['sku'], cant, p['und_x_embalaje'], st.session_state.usuario_ingresado, costo)
                    if ok: st.success(f"Entrada registrada. Costo: {formato_clp(costo)}"); st.balloons()
                    else: st.error(msg)
            else: st.warning("SKU no encontrado.")

    with c2:
        st.subheader("🚀 Registro de Venta")
        sku_out = st.text_input("Buscar SKU para Venta:").upper()
        if sku_out:
            prods = buscar_productos(sku_out)
            if prods:
                p = prods[0]
                st.info(f"Disponible: {p['stock_total']} unidades")
                cant_v = st.number_input("Cantidad a vender:", min_value=1, key="n2")
                canal = st.selectbox("Canal:", ["Mercadolibre", "Falabella", "Walmart", "Hites", "Paris", "Web", "WhatsApp", "Retiro"])
                if st.button("🚀 Finalizar Venta", type="primary"):
                    ok, msg = registrar_movimiento("salida", p['sku'], cant_v, canal, st.session_state.usuario_ingresado)
                    if ok: st.success("Venta guardada exitosamente!"); st.rerun()
                    else: st.error(msg)

with t2:
    st.subheader("Movimientos Recientes")
    hist = []
    ent = supabase.table("entradas").select("*").order("fecha", desc=True).limit(50).execute().data
    for e in ent: e['Tipo'] = "🟢 Entrada"; hist.append(e)
    sal = supabase.table("salidas").select("*").order("fecha", desc=True).limit(50).execute().data
    for s in sal: s['Tipo'] = "🔴 Venta"; hist.append(s)
    
    if hist:
        df_h = pd.DataFrame(hist).sort_values("fecha", ascending=False)
        st.dataframe(df_h[["fecha", "Tipo", "sku", "cantidad", "usuario"]], use_container_width=True, hide_index=True)

with t3:
    st.subheader("Estado de Inventario")
    all_p = buscar_productos()
    if all_p:
        df = pd.DataFrame(all_p)
        # Cálculos
        df['Unitario'] = df['precio_costo_contenedor'] / df['und_x_embalaje'].replace(0, 1)
        df['Inversion_Fila'] = df['Unitario'] * df['stock_total']
        
        # Métricas con formato chileno
        m1, m2, m3 = st.columns(3)
        m1.metric("Inversión Total", formato_clp(df['Inversion_Fila'].sum()))
        m2.metric("Total Unidades", int(df['stock_total'].sum()))
        m3.metric("SKUs Activos", len(df))
        
        # Preparar tabla para mostrar
        df_view = df.copy()
        df_view['Costo Contenedor'] = df_view['precio_costo_contenedor'].apply(formato_clp)
        df_view['Valor Unitario'] = df_view['Unitario'].apply(formato_clp)
        
        st.dataframe(
            df_view[["sku", "nombre", "stock_total", "und_x_embalaje", "Costo Contenedor", "Valor Unitario"]], 
            use_container_width=True, 
            hide_index=True
        )

with t4:
    st.subheader("Configuración de Productos")
    with st.expander("🆕 Crear Nuevo Producto"):
        with st.form("crear"):
            c1, c2, c3 = st.columns(3)
            f_sku = c1.text_input("SKU").upper().strip()
            f_nom = c2.text_input("Nombre")
            f_und = c3.number_input("Unidades x Embalaje", min_value=1, value=1)
            if st.form_submit_button("Guardar Producto"):
                if f_sku and f_nom:
                    try:
                        supabase.table("productos").insert({"sku": f_sku, "nombre": f_nom, "und_x_embalaje": f_und, "stock_total": 0}).execute()
                        st.success("Producto creado!"); st.rerun()
                    except: st.error("Error: El SKU ya podría existir.")
