import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os
import pandas as pd
from PIL import Image

# --- CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="M&M Hogar", page_icon="📦", layout="wide")

st.markdown("""<style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    /* Quitar botones +/- de los inputs numéricos de forma agresiva */
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

# --- FUNCIONES ---
def buscar_productos(query: str = ""):
    try:
        db_query = supabase.table("productos").select("*")
        if query:
            db_query = db_query.or_(f"sku.ilike.%{query}%,nombre.ilike.%{query}%")
        return db_query.order("sku").execute().data
    except Exception as e:
        return []

# --- INTERFAZ ---
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
    st.warning("Por favor, inicia sesión.")
    st.stop()

t1, t2, t3, t4 = st.tabs(["🛒 Movimientos", "📋 Historial", "📈 Stock", "⚙️ Configuración"])

# --- TAB 1: MOVIMIENTOS (VENTA IZQ, ENTRADA DER) ---
with t1:
    c_venta, c_entrada = st.columns(2)
    with c_venta:
        st.subheader("🚀 Registro de Venta")
        search_v = st.text_input("Buscar producto (Venta):")
        res_v = buscar_productos(search_v)
        if search_v and res_v:
            p_v = st.selectbox("Elegir:", res_v, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
            cant_v = st.number_input("Cantidad:", min_value=1, key="nv")
            canal = st.selectbox("Canal:", ["Mercadolibre", "Falabella", "Walmart", "Web", "WhatsApp", "Retiro"])
            if st.button("Finalizar Venta", type="primary"):
                res = supabase.rpc("registrar_salida", {"p_sku": p_v['sku'], "p_cantidad": int(cant_v), "p_canal": canal, "p_usuario": st.session_state.usuario_ingresado}).execute()
                st.success("Venta registrada"); st.rerun()

    with c_entrada:
        st.subheader("📥 Entrada de Stock")
        search_e = st.text_input("Buscar producto (Entrada):")
        res_e = buscar_productos(search_e)
        if search_e and res_e:
            p_e = st.selectbox("Elegir:", res_e, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
            cant_e = st.number_input("Unidades:", min_value=1, key="ne")
            costo_e = st.number_input("Costo Contenedor:", value=float(p_e['precio_costo_contenedor']))
            if st.button("Confirmar Entrada", type="primary"):
                supabase.table("productos").update({"precio_costo_contenedor": float(costo_e)}).eq("sku", p_e['sku']).execute()
                supabase.rpc("registrar_entrada", {"p_sku": p_e['sku'], "p_cantidad": int(cant_e), "p_und_x_embalaje": p_e['und_x_embalaje'], "p_usuario": st.session_state.usuario_ingresado}).execute()
                st.success("Entrada registrada"); st.rerun()

# --- TAB 4: CONFIGURACIÓN (LÓGICA ANTI-DUPLICADO MEJORADA) ---
with t4:
    st.subheader("⚙️ Configuración")
    col_edit, col_new = st.columns(2)
    
    with col_edit:
        st.markdown("### ✏️ Editar Producto")
        s_edit = st.text_input("Buscar para editar:").upper()
        if s_edit:
            prods = buscar_productos(s_edit)
            if prods:
                # Usamos una clave única para el selectbox basada en el SKU actual
                p_edit = st.selectbox("Seleccione producto:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
                
                # NO usamos st.form aquí para tener un control más directo sobre el guardado
                sku_original = p_edit['sku']
                
                new_sku = st.text_input("Editar SKU:", value=sku_original).upper().strip()
                new_nom = st.text_input("Editar Nombre:", value=p_edit['nombre'])
                new_und = st.number_input("Editar Unidades x Embalaje:", min_value=1, value=int(p_edit['und_x_embalaje']))
                new_cost = st.number_input("Editar Costo Contenedor (CLP):", min_value=0, value=int(p_edit['precio_costo_contenedor']))
                
                if st.button("💾 Guardar Cambios", type="primary", use_container_width=True):
                    try:
                        # 1. Creamos el diccionario con los datos básicos
                        payload = {
                            "nombre": new_nom,
                            "und_x_embalaje": new_und,
                            "precio_costo_contenedor": new_cost
                        }
                        
                        # 2. Lógica crucial: Solo incluimos el SKU si realmente cambió
                        if new_sku != sku_original:
                            payload["sku"] = new_sku
                            
                        # 3. Ejecutamos la actualización filtrando por el SKU que sabemos que existe
                        result = supabase.table("productos").update(payload).eq("sku", sku_original).execute()
                        
                        if result.data:
                            st.success("✅ Producto actualizado correctamente")
                            st.rerun()
                        else:
                            st.error("No se pudo actualizar el producto.")
                            
                    except Exception as e:
                        if "23505" in str(e):
                            st.error("❌ Error: Ya existe otro producto con ese nuevo SKU.")
                        else:
                            st.error(f"❌ Error inesperado: {e}")

    with col_new:
        st.markdown("### 🆕 Nuevo Producto")
        with st.form("new_form", clear_on_submit=True):
            n_sku = st.text_input("SKU:").upper().strip()
            n_nom = st.text_input("Nombre:")
            n_und = st.number_input("Unidades x Embalaje:", min_value=1, value=1)
            n_cost = st.number_input("Costo Contenedor Inicial:", min_value=0, value=0)
            
            if st.form_submit_button("Crear Producto", use_container_width=True):
                if n_sku and n_nom:
                    try:
                        supabase.table("productos").insert({
                            "sku": n_sku, "nombre": n_nom, "und_x_embalaje": n_und, 
                            "stock_total": 0, "precio_costo_contenedor": n_cost
                        }).execute()
                        st.success("✅ Producto creado"); st.rerun()
                    except: st.error("❌ El SKU ya existe.")
