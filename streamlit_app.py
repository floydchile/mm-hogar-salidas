import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os
import pandas as pd
from PIL import Image

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="M&M Hogar", page_icon="📦", layout="wide")

# ESTILOS: Quitar botones +/- y ajustar padding
st.markdown("""<style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    input[type=number] { -moz-appearance: textfield; }
</style>""", unsafe_allow_html=True)

# --- CONEXIÓN ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://nijzonhfxyihpgozinge.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()
USUARIOS_VALIDOS = ["pau", "dany", "miguel"]

# --- FUNCIONES AUXILIARES ---
def buscar_productos_db(query: str = ""):
    try:
        db_query = supabase.table("productos").select("*")
        if query:
            db_query = db_query.or_(f"sku.ilike.%{query}%,nombre.ilike.%{query}%")
        return db_query.order("sku").execute().data
    except Exception: return []

# --- INTERFAZ Y SESIÓN ---
if 'usuario_ingresado' not in st.session_state: st.session_state.usuario_ingresado = None

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
    st.title("📦 M&M Hogar")
    st.warning("Inicia sesión en el panel lateral.")
    st.stop()

# --- DEFINICIÓN DE PESTAÑAS ---
tabs = st.tabs(["🛒 Movimientos", "📋 Historial", "📈 Stock", "⚙️ Configuración"])

# 1. PESTAÑA MOVIMIENTOS (ORDEN SOLICITADO)
with tabs[0]:
    col_v, col_e = st.columns(2)
    
    with col_v: # REGISTRO DE VENTA A LA IZQUIERDA
        st.subheader("🚀 Registro de Venta")
        s_v = st.text_input("Buscar para Venta:", key="sv")
        res_v = buscar_productos_db(s_v)
        if s_v and res_v:
            p_v = st.selectbox("Producto:", res_v, format_func=lambda x: f"{x['sku']} - {x['nombre']}", key="sel_v")
            c_v = st.number_input("Cantidad:", min_value=1, key="nv")
            canal = st.selectbox("Canal:", ["Mercadolibre", "Falabella", "Walmart", "Web", "WhatsApp", "Retiro"])
            if st.button("Finalizar Venta", type="primary", use_container_width=True):
                res = supabase.rpc("registrar_salida", {"p_sku": p_v['sku'], "p_cantidad": int(c_v), "p_canal": canal, "p_usuario": st.session_state.usuario_ingresado}).execute()
                if "ERROR" not in str(res.data): st.success("✅ Venta registrada"); st.rerun()
                else: st.error(res.data)

    with col_e: # ENTRADA DE STOCK A LA DERECHA
        st.subheader("📥 Entrada de Stock")
        s_e = st.text_input("Buscar para Entrada:", key="se")
        res_e = buscar_productos_db(s_e)
        if s_e and res_e:
            p_e = st.selectbox("Producto:", res_e, format_func=lambda x: f"{x['sku']} - {x['nombre']}", key="sel_e")
            c_e = st.number_input("Unidades:", min_value=1, key="ne")
            costo_e = st.number_input("Costo Contenedor:", value=float(p_e['precio_costo_contenedor']), key="ce")
            if st.button("Confirmar Entrada", type="primary", use_container_width=True):
                supabase.table("productos").update({"precio_costo_contenedor": float(costo_e)}).eq("sku", p_e['sku']).execute()
                supabase.rpc("registrar_entrada", {"p_sku": p_e['sku'], "p_cantidad": int(c_e), "p_und_x_embalaje": p_e['und_x_embalaje'], "p_usuario": st.session_state.usuario_ingresado}).execute()
                st.success("✅ Entrada registrada"); st.rerun()

# 2. PESTAÑA HISTORIAL
with tabs[1]:
    st.subheader("Últimos Movimientos")
    data_h = []
    ent = supabase.table("entradas").select("*").order("fecha", desc=True).limit(20).execute().data
    sal = supabase.table("salidas").select("*").order("fecha", desc=True).limit(20).execute().data
    for e in ent: e['tipo'] = "🟢 ENTRADA"; data_h.append(e)
    for s in sal: s['tipo'] = "🔴 VENTA"; data_h.append(s)
    if data_h:
        df_h = pd.DataFrame(data_h).sort_values("fecha", ascending=False)
        st.dataframe(df_h[["fecha", "tipo", "sku", "cantidad", "usuario"]], use_container_width=True)

# 3. PESTAÑA STOCK
with tabs[2]:
    st.subheader("Estado de Inventario")
    prods = buscar_productos_db()
    if prods:
        df_p = pd.DataFrame(prods)
        df_p['Inversión'] = (df_p['precio_costo_contenedor'] / df_p['und_x_embalaje'].replace(0,1)) * df_p['stock_total']
        st.metric("Inversión Total", f"${df_p['Inversión'].sum():,.0f}")
        st.dataframe(df_p[["sku", "nombre", "stock_total", "und_x_embalaje", "precio_costo_contenedor"]], use_container_width=True)

# 4. PESTAÑA CONFIGURACIÓN (REPARADA)
with tabs[3]:
    st.subheader("Configuración de Productos")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### ✏️ Editar Existente")
        s_edit = st.text_input("Buscar para editar:").upper()
        if s_edit:
            res_ed = buscar_productos_db(s_edit)
            if res_ed:
                p_edit = st.selectbox("Seleccione:", res_ed, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
                
                # Campos de edición (sin st.form para evitar conflictos de caché)
                sku_original = p_edit['sku']
                new_nom = st.text_input("Nombre:", value=p_edit['nombre'])
                new_und = st.number_input("Unidades x Emb:", min_value=1, value=int(p_edit['und_x_embalaje']))
                new_cost = st.number_input("Costo Contenedor:", min_value=0, value=int(p_edit['precio_costo_contenedor']))
                
                if st.button("Guardar Cambios"):
                    # LA SOLUCIÓN: No enviamos 'sku' en el update si no ha cambiado
                    upd = {"nombre": new_nom, "und_x_embalaje": new_und, "precio_costo_contenedor": new_cost}
                    try:
                        supabase.table("productos").update(upd).eq("sku", sku_original).execute()
                        st.success("✅ Actualizado"); st.rerun()
                    except Exception as e: st.error(e)

    with col2:
        st.markdown("### 🆕 Crear Producto")
        with st.form("crear_p", clear_on_submit=True):
            n_sku = st.text_input("SKU:").upper().strip()
            n_nom = st.text_input("Nombre:")
            n_und = st.number_input("Unidades x Emb:", min_value=1, value=1)
            n_cost = st.number_input("Costo Contenedor Inicial:", min_value=0, value=0)
            if st.form_submit_button("Crear"):
                try:
                    supabase.table("productos").insert({"sku": n_sku, "nombre": n_nom, "und_x_embalaje": n_und, "precio_costo_contenedor": n_cost, "stock_total": 0}).execute()
                    st.success("✅ Creado"); st.rerun()
                except: st.error("Ese SKU ya existe.")
