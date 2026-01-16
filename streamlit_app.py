import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os
import pandas as pd
from PIL import Image
import requests
import urllib.parse  # Importante para el SKU con espacios

# --- CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="M&M Hogar", page_icon="📦", layout="wide")

st.markdown("""<style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    .stMetric {background-color: #f8f9fa; border-radius: 10px; padding: 10px; border: 1px solid #eee;}
    [data-testid="stMetricValue"] {font-size: 1.8rem;}
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
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
MELI_USER_ID = os.getenv("MELI_USER_ID")

if not SUPABASE_KEY or not SUPABASE_URL:
    st.error("❌ Error: Faltan las credenciales de Supabase en Railway.")
    st.stop()

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()
USUARIOS_VALIDOS = ["pau", "dany", "miguel"]

# --- FUNCIONES DE INTEGRACIÓN MERCADO LIBRE ---

def sincronizar_stock_meli(sku, nuevo_stock):
    if not MELI_TOKEN or not MELI_USER_ID:
        return False
    try:
        sku_encoded = urllib.parse.quote(sku)
        search_url = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?sku={sku_encoded}"
        headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
        search_res = requests.get(search_url, headers=headers).json()
        
        if search_res.get('results'):
            item_id = search_res['results'][0]
            update_url = f"https://api.mercadolibre.com/items/{item_id}"
            payload = {"available_quantity": int(nuevo_stock)}
            response = requests.put(update_url, json=payload, headers=headers)
            return response.status_code == 200
    except:
        pass
    return False

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
            supabase.rpc("registrar_entrada", {"p_sku": sku, "p_cantidad": int(cantidad), "p_und_x_embalaje": extra_val, "p_usuario": usuario}).execute()
        else:
            res = supabase.rpc("registrar_salida", {"p_sku": sku, "p_cantidad": int(cantidad), "p_canal": extra_val, "p_usuario": usuario}).execute()
            if "ERROR" in res.data: return False, res.data
        
        # Sincronización automática
        prod_data = supabase.table("productos").select("stock_total").eq("sku", sku).single().execute()
        if prod_data.data:
            sincronizar_stock_meli(sku, prod_data.data['stock_total'])
            
        return True, "Operación exitosa"
    except Exception as e:
        return False, str(e)

# --- INTERFAZ USUARIO ---
if 'usuario_ingresado' not in st.session_state: st.session_state.usuario_ingresado = None
if 'form_count' not in st.session_state: st.session_state.form_count = 0
if 'edit_reset_counter' not in st.session_state: st.session_state.edit_reset_counter = 0

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
                costo = st.number_input("Costo Contenedor (CLP):", value=int(p_sel['precio_costo_contenedor']), step=1, key=f"c1_{st.session_state.form_count}")
                if st.button("📥 Confirmar Entrada", type="primary", use_container_width=True):
                    ok, msg = registrar_movimiento("entrada", p_sel['sku'], cant, p_sel['und_x_embalaje'], st.session_state.usuario_ingresado, costo)
                    if ok: 
                        st.session_state.form_count += 1
                        st.success(f"Entrada registrada."); st.rerun()

# --- TAB 2: HISTORIAL ---
with t2:
    st.subheader("Movimientos Recientes")
    hist = []
    ent = supabase.table("entradas").select("*").order("fecha", desc=True).limit(30).execute().data
    for e in ent: e['Tipo'] = "🟢 Entrada"; hist.append(e)
    sal = supabase.table("salidas").select("*").order("fecha", desc=True).limit(30).execute().data
    for s in sal: s['Tipo'] = "🔴 Venta"; hist.append(s)
    if hist:
        df_h = pd.DataFrame(hist).sort_values("fecha", ascending=False)
        st.dataframe(df_h[["fecha", "Tipo", "sku", "cantidad", "usuario"]], use_container_width=True, hide_index=True)

# --- TAB 3: STOCK ---
with t3:
    st.subheader("Estado de Inventario")
    all_p = buscar_productos()
    if all_p:
        df = pd.DataFrame(all_p)
        df['Unitario'] = df['precio_costo_contenedor'] / df['und_x_embalaje'].replace(0, 1)
        df['Inversion_Fila'] = df['Unitario'] * df['stock_total']
        m1, m2, m3 = st.columns(3)
        m1.metric("Inversión Total", formato_clp(df['Inversion_Fila'].sum()))
        m2.metric("Total Unidades", int(df['stock_total'].sum()))
        m3.metric("SKUs Activos", len(df))
        df_view = df.copy()
        df_view['Costo Contenedor'] = df_view['precio_costo_contenedor'].apply(formato_clp)
        df_view['Valor Unitario'] = df_view['Unitario'].apply(formato_clp)
        st.dataframe(df_view[["sku", "nombre", "stock_total", "und_x_embalaje", "Costo Contenedor", "Valor Unitario"]], use_container_width=True, hide_index=True)

# --- TAB 4: CONFIGURACIÓN ---
with t4:
    st.subheader("Configuración de Productos")
    c_edit, c_new = st.columns(2)
    with c_edit:
        st.markdown("### ✏️ Editar Producto")
        edit_query = st.text_input("Buscar para editar:", key=f"edit_search_box_{st.session_state.edit_reset_counter}").upper()
        if edit_query:
            prods_edit = buscar_productos(edit_query)
            if prods_edit:
                p_to_edit = st.selectbox("Seleccione producto:", prods_edit, format_func=lambda x: f"{x['sku']} - {x['nombre']}", key=f"edit_select_{st.session_state.edit_reset_counter}")
                with st.form(key=f"form_edit_dyn_{st.session_state.edit_reset_counter}"):
                    sku_fijo = p_to_edit['sku']
                    st.text_input("SKU:", value=sku_fijo, disabled=True)
                    new_name = st.text_input("Nombre:", value=p_to_edit['nombre'])
                    new_und = st.number_input("Unidades x Embalaje:", min_value=1, value=int(p_to_edit['und_x_embalaje']))
                    new_costo = st.number_input("Costo Contenedor (CLP):", min_value=0, value=int(p_to_edit['precio_costo_contenedor']))
                    if st.form_submit_button("Actualizar Producto", type="primary", use_container_width=True):
                        try:
                            supabase.table("productos").update({"nombre": new_name, "und_x_embalaje": new_und, "precio_costo_contenedor": new_costo}).eq("sku", sku_fijo).execute()
                            supabase.table("entradas").insert({"sku": sku_fijo, "cantidad": 0, "usuario": f"{st.session_state.usuario_ingresado} (EDIT)"}).execute()
                            st.session_state.edit_reset_counter += 1
                            st.success(f"✅ {sku_fijo} actualizado.")
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")
    with c_new:
        st.markdown("### 🆕 Nuevo Producto")
        with st.form("crear_nuevo", clear_on_submit=True):
            f_sku = st.text_input("SKU:").upper().strip()
            f_nom = st.text_input("Nombre:")
            f_und = st.number_input("Unidades x Embalaje:", min_value=1, value=1)
            f_costo = st.number_input("Costo Contenedor Inicial (CLP):", min_value=0, value=0)
            if st.form_submit_button("Crear Producto", use_container_width=True):
                if f_sku and f_nom:
                    try:
                        supabase.table("productos").insert({"sku": f_sku, "nombre": f_nom, "und_x_embalaje": f_und, "stock_total": 0, "precio_costo_contenedor": f_costo}).execute()
                        st.success("✅ Creado con éxito"); st.rerun()
                    except: st.error("El SKU ya existe.")
