import streamlit as st
from supabase import create_client, Client
import os
import pandas as pd

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="M&M Hogar", page_icon="📦", layout="wide")

# CSS para ocultar botones +/- y limpiar la vista
st.markdown("""<style>
    .block-container {padding-top: 1rem;}
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    input[type=number] { -moz-appearance: textfield; }
</style>""", unsafe_allow_html=True)

# --- 2. CONEXIÓN ---
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://nijzonhfxyihpgozinge.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()
USUARIOS_VALIDOS = ["pau", "dany", "miguel"]

# --- 3. FUNCIONES ---
def buscar_prods(query: str = ""):
    try:
        db = supabase.table("productos").select("*")
        if query:
            db = db.or_(f"sku.ilike.%{query}%,nombre.ilike.%{query}%")
        return db.order("sku").execute().data
    except: return []

# --- 4. LOGIN ---
if 'usuario_ingresado' not in st.session_state: 
    st.session_state.usuario_ingresado = None

with st.sidebar:
    if st.session_state.usuario_ingresado:
        st.success(f"Sesión: {st.session_state.usuario_ingresado.upper()}")
        if st.button("🚪 Cerrar Sesión"):
            st.session_state.usuario_ingresado = None
            st.rerun()
    else:
        u = st.text_input("Usuario:").lower().strip()
        if st.button("Ingresar"):
            if u in USUARIOS_VALIDOS:
                st.session_state.usuario_ingresado = u
                st.rerun()

if not st.session_state.usuario_ingresado:
    st.title("📦 M&M Hogar")
    st.info("Inicia sesión para ver el panel.")
    st.stop()

# --- 5. ESTRUCTURA DE PESTAÑAS (Esto es lo que había desaparecido) ---
t_mov, t_hist, t_stock, t_conf = st.tabs(["🛒 Movimientos", "📋 Historial", "📈 Stock", "⚙️ Configuración"])

with t_mov:
    col_v, col_e = st.columns(2)
    
    with col_v: # VENTA A LA IZQUIERDA
        st.subheader("🚀 Registro de Venta")
        busq_v = st.text_input("Buscar producto (Venta):", key="bv")
        prods_v = buscar_prods(busq_v)
        if busq_v and prods_v:
            sel_v = st.selectbox("Seleccionar:", prods_v, format_func=lambda x: f"{x['sku']} - {x['nombre']}", key="sv")
            cant_v = st.number_input("Cantidad:", min_value=1, key="nv")
            canal = st.selectbox("Canal:", ["Mercadolibre", "Falabella", "Walmart", "Web", "WhatsApp", "Retiro"])
            if st.button("Finalizar Venta", type="primary"):
                res = supabase.rpc("registrar_salida", {"p_sku": sel_v['sku'], "p_cantidad": int(cant_v), "p_canal": canal, "p_usuario": st.session_state.usuario_ingresado}).execute()
                st.success("Venta guardada"); st.rerun()

    with col_e: # ENTRADA A LA DERECHA
        st.subheader("📥 Entrada de Stock")
        busq_e = st.text_input("Buscar producto (Entrada):", key="be")
        prods_e = buscar_prods(busq_e)
        if busq_e and prods_e:
            sel_e = st.selectbox("Seleccionar:", prods_e, format_func=lambda x: f"{x['sku']} - {x['nombre']}", key="se")
            cant_e = st.number_input("Unidades:", min_value=1, key="ne")
            costo_e = st.number_input("Costo Contenedor:", value=float(sel_e['precio_costo_contenedor']), key="ce")
            if st.button("Confirmar Entrada", type="primary"):
                supabase.table("productos").update({"precio_costo_contenedor": float(costo_e)}).eq("sku", sel_e['sku']).execute()
                supabase.rpc("registrar_entrada", {"p_sku": sel_e['sku'], "p_cantidad": int(cant_e), "p_und_x_embalaje": sel_e['und_x_embalaje'], "p_usuario": st.session_state.usuario_ingresado}).execute()
                st.success("Entrada procesada"); st.rerun()

with t_hist:
    st.subheader("Historial")
    # Carga simple de historial
    ent = supabase.table("entradas").select("*").limit(10).execute().data
    if ent: st.table(pd.DataFrame(ent)[["fecha", "sku", "cantidad", "usuario"]])

with t_stock:
    st.subheader("Inventario")
    prods = buscar_prods()
    if prods: st.dataframe(pd.DataFrame(prods)[["sku", "nombre", "stock_total"]], use_container_width=True)

with t_conf:
    st.subheader("Configuración")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### ✏️ Editar")
        busq_ed = st.text_input("Buscar para editar:").upper()
        res_ed = buscar_prods(busq_ed)
        if busq_ed and res_ed:
            p = st.selectbox("Elegir:", res_ed, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
            
            # LÓGICA ANTI-DUPLICADO:
            new_sku = st.text_input("SKU:", value=p['sku']).upper().strip()
            new_nom = st.text_input("Nombre:", value=p['nombre'])
            new_cost = st.number_input("Costo:", value=float(p['precio_costo_contenedor']))
            
            if st.button("Actualizar Producto"):
                # Si el SKU no cambió, NO lo enviamos en el diccionario de actualización
                datos_upd = {"nombre": new_nom, "precio_costo_contenedor": new_cost}
                if new_sku != p['sku']:
                    datos_upd["sku"] = new_sku
                
                supabase.table("productos").update(datos_upd).eq("sku", p['sku']).execute()
                st.success("Cambios guardados"); st.rerun()

    with c2:
        st.markdown("### 🆕 Nuevo")
        with st.form("nuevo_p"):
            n_sku = st.text_input("SKU:")
            n_nom = st.text_input("Nombre:")
            if st.form_submit_button("Crear"):
                supabase.table("productos").insert({"sku": n_sku.upper(), "nombre": n_nom, "stock_total": 0}).execute()
                st.success("Creado"); st.rerun()
