import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os
import pandas as pd
from PIL import Image

# --- CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="M&M Hogar", page_icon="📦", layout="wide")

# Estilos CSS corregidos: Invertir columnas y quitar botones +/-
st.markdown("""<style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    .stMetric {background-color: #f8f9fa; border-radius: 10px; padding: 10px; border: 1px solid #eee;}
    [data-testid="stMetricValue"] {font-size: 1.8rem;}
    /* Quita los botones de incremento/decremento en Chrome, Safari, Edge y Firefox */
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
        st.error(f"Error al buscar: {e}")
        return []

# --- INTERFAZ ---
if 'form_count' not in st.session_state: st.session_state.form_count = 0
if 'usuario_ingresado' not in st.session_state: st.session_state.usuario_ingresado = None

# Sidebar (Login)
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
    st.warning("Inicia sesión para operar.")
    st.stop()

t1, t2, t3, t4 = st.tabs(["🛒 Movimientos", "📋 Historial", "📈 Stock", "⚙️ Configuración"])

# --- TAB 1: MOVIMIENTOS (ORDEN INVERTIDO) ---
with t1:
    c_venta, c_entrada = st.columns(2)
    
    with c_venta: # Venta a la izquierda
        st.subheader("🚀 Registro de Venta")
        search_v = st.text_input("Buscar producto:", key=f"sv_{st.session_state.form_count}")
        res_v = buscar_productos(search_v)
        if search_v and res_v:
            p_v = st.selectbox("Seleccionar:", res_v, format_func=lambda x: f"{x['sku']} - {x['nombre']}", key=f"selv_{st.session_state.form_count}")
            cant_v = st.number_input("Cantidad:", min_value=1, key=f"nv_{st.session_state.form_count}")
            canal = st.selectbox("Canal:", ["Mercadolibre", "Falabella", "Walmart", "Web", "WhatsApp", "Retiro"], key=f"cv_{st.session_state.form_count}")
            if st.button("Finalizar Venta", type="primary"):
                res = supabase.rpc("registrar_salida", {"p_sku": p_v['sku'], "p_cantidad": int(cant_v), "p_canal": canal, "p_usuario": st.session_state.usuario_ingresado}).execute()
                if "ERROR" not in str(res.data):
                    st.session_state.form_count += 1
                    st.success("Venta registrada"); st.rerun()
                else: st.error(res.data)

    with c_entrada: # Entrada a la derecha
        st.subheader("📥 Entrada de Stock")
        search_e = st.text_input("Buscar producto:", key=f"se_{st.session_state.form_count}")
        res_e = buscar_productos(search_e)
        if search_e and res_e:
            p_e = st.selectbox("Seleccionar:", res_e, format_func=lambda x: f"{x['sku']} - {x['nombre']}", key=f"sele_{st.session_state.form_count}")
            cant_e = st.number_input("Unidades:", min_value=1, key=f"ne_{st.session_state.form_count}")
            costo_e = st.number_input("Costo Contenedor:", value=float(p_e['precio_costo_contenedor']), key=f"ce_{st.session_state.form_count}")
            if st.button("Confirmar Entrada", type="primary"):
                supabase.table("productos").update({"precio_costo_contenedor": float(costo_e)}).eq("sku", p_e['sku']).execute()
                supabase.rpc("registrar_entrada", {"p_sku": p_e['sku'], "p_cantidad": int(cant_e), "p_und_x_embalaje": p_e['und_x_embalaje'], "p_usuario": st.session_state.usuario_ingresado}).execute()
                st.session_state.form_count += 1
                st.success("Entrada registrada"); st.rerun()

# --- TAB 4: CONFIGURACIÓN (SOLUCIÓN ERROR DUPLICADO) ---
with t4:
    st.subheader("⚙️ Configuración de Productos")
    col_edit, col_new = st.columns(2)
    
    with col_edit:
        st.markdown("### ✏️ Editar Producto")
        s_edit = st.text_input("Buscar para editar:", key="s_edit").upper()
        if s_edit:
            prods = buscar_productos(s_edit)
            if prods:
                p_edit = st.selectbox("Elegir producto:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
                
                with st.form("edit_form"):
                    # Guardamos el SKU original para el filtro .eq()
                    sku_original = p_edit['sku']
                    
                    new_sku = st.text_input("SKU:", value=p_edit['sku']).upper().strip()
                    new_nom = st.text_input("Nombre:", value=p_edit['nombre'])
                    new_und = st.number_input("Unidades x Embalaje:", min_value=1, value=int(p_edit['und_x_embalaje']))
                    new_cost = st.number_input("Costo Contenedor (CLP):", min_value=0, value=int(p_edit['precio_costo_contenedor']))
                    
                    if st.form_submit_button("Actualizar Producto", type="primary"):
                        try:
                            # Preparamos los datos a actualizar
                            update_data = {
                                "nombre": new_nom,
                                "und_x_embalaje": new_und,
                                "precio_costo_contenedor": new_cost
                            }
                            # Solo intentamos actualizar el SKU si cambió (así evitamos el error 23505)
                            if new_sku != sku_original:
                                update_data["sku"] = new_sku
                            
                            supabase.table("productos").update(update_data).eq("sku", sku_original).execute()
                            st.success("✅ Producto actualizado"); st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar: {e}")

    with col_new:
        st.markdown("### 🆕 Nuevo Producto")
        with st.form("new_form", clear_on_submit=True):
            n_sku = st.text_input("SKU:").upper().strip()
            n_nom = st.text_input("Nombre:")
            n_und = st.number_input("Unidades x Embalaje:", min_value=1, value=1)
            n_cost = st.number_input("Costo Contenedor Inicial (CLP):", min_value=0, value=0)
            
            if st.form_submit_button("Crear Producto"):
                if n_sku and n_nom:
                    try:
                        supabase.table("productos").insert({
                            "sku": n_sku, "nombre": n_nom, "und_x_embalaje": n_und, 
                            "stock_total": 0, "precio_costo_contenedor": n_cost
                        }).execute()
                        st.success("✅ Creado correctamente"); st.rerun()
                    except: st.error("El SKU ya existe")
