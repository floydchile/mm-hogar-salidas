import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os
import pandas as pd
from PIL import Image
import requests
import urllib.parse

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

# --- CONEXIÓN A VARIABLES DE ENTORNO ---
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

# --- LÓGICA DE WEBHOOK (RECEPTOR DE VENTAS DE MERCADO LIBRE) ---
# Se activa solo cuando Mercado Libre envía una notificación vía URL
params = st.query_params
if "topic" in params and "resource" in params:
    topic = params.get("topic")
    resource = params.get("resource")
    
    if topic == "orders_v2":
        try:
            headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
            # Consultar detalle de la orden en Mercado Libre
            order_res = requests.get(f"https://api.mercadolibre.com{resource}", headers=headers).json()
            
            for item in order_res.get('order_items', []):
                sku = item.get('item', {}).get('seller_custom_field') # El SKU guardado en MeLi
                cant = item.get('quantity')
                if sku:
                    # Descontar stock en Supabase automáticamente
                    supabase.rpc("registrar_salida", {
                        "p_sku": sku, 
                        "p_cantidad": int(cant), 
                        "p_canal": "Mercadolibre", 
                        "p_usuario": "BOT_MELI"
                    }).execute()
        except:
            pass
    st.stop() # Detiene la carga de la interfaz para peticiones de API

# --- FUNCIONES DE INTEGRACIÓN ---

def sincronizar_stock_meli(sku, nuevo_stock):
    """Actualiza el stock en Mercado Libre buscando el producto por SKU"""
    if not MELI_TOKEN or not MELI_USER_ID: return False
    try:
        sku_encoded = urllib.parse.quote(sku)
        search_url = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?sku={sku_encoded}"
        headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
        search_res = requests.get(search_url, headers=headers).json()
        
        if search_res.get('results'):
            item_id = search_res['results'][0]
            requests.put(f"https://api.mercadolibre.com/items/{item_id}", 
                         json={"available_quantity": int(nuevo_stock)}, headers=headers)
            return True
    except: pass
    return False

def registrar_movimiento(tipo, sku, cantidad, extra_val, usuario, precio=None):
    """Registra entrada o salida en Supabase y sincroniza con MeLi"""
    try:
        if tipo == "entrada":
            if precio is not None:
                supabase.table("productos").update({"precio_costo_contenedor": float(precio)}).eq("sku", sku).execute()
            supabase.rpc("registrar_entrada", {"p_sku": sku, "p_cantidad": int(cantidad), "p_und_x_embalaje": extra_val, "p_usuario": usuario}).execute()
        else:
            res = supabase.rpc("registrar_salida", {"p_sku": sku, "p_cantidad": int(cantidad), "p_canal": extra_val, "p_usuario": usuario}).execute()
            if "ERROR" in res.data: return False, res.data
        
        # Sincronización automática de salida hacia Mercado Libre
        prod_data = supabase.table("productos").select("stock_total").eq("sku", sku).single().execute()
        if prod_data.data:
            sincronizar_stock_meli(sku, prod_data.data['stock_total'])
        return True, "Ok"
    except Exception as e: return False, str(e)

def buscar_productos(query: str = ""):
    try:
        db_query = supabase.table("productos").select("*")
        if query:
            db_query = db_query.or_(f"sku.ilike.%{query}%,nombre.ilike.%{query}%")
        return db_query.order("sku").execute().data
    except: return []

# --- INTERFAZ DE USUARIO ---

# Carga de Logo
try:
    logo = Image.open("assets/mym_hogar.png")
except:
    logo = None

if 'usuario_ingresado' not in st.session_state: st.session_state.usuario_ingresado = None
if 'form_count' not in st.session_state: st.session_state.form_count = 0

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

st.title("📦 M&M Hogar - Gestión de Inventario")
t1, t2, t3, t4 = st.tabs(["🛒 Movimientos", "📋 Historial", "📈 Stock", "⚙️ Configuración"])

with t1:
    col_v, col_e = st.columns(2)
    with col_v:
        st.subheader("🚀 Registro de Venta")
        sku_out = st.text_input("Buscar SKU para Venta:", key=f"out_{st.session_state.form_count}").upper()
        if sku_out:
            prods = buscar_productos(sku_out)
            if prods:
                p = st.selectbox("Seleccionar:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']} (Disp: {x['stock_total']})")
                cant = st.number_input("Cantidad:", min_value=1, key=f"c_out_{st.session_state.form_count}")
                can = st.selectbox("Canal:", ["Mercadolibre", "WhatsApp", "Web", "Retiro", "Otros"])
                if st.button("🚀 Finalizar Venta", use_container_width=True, type="primary"):
                    ok, msg = registrar_movimiento("salida", p['sku'], cant, can, st.session_state.usuario_ingresado)
                    if ok: 
                        st.success("Venta guardada y Mercado Libre actualizado!"); 
                        st.session_state.form_count += 1; 
                        st.rerun()

    with col_e:
        st.subheader("📥 Entrada de Stock")
        sku_in = st.text_input("Buscar SKU para Entrada:", key=f"in_{st.session_state.form_count}").upper()
        if sku_in:
            prods_in = buscar_productos(sku_in)
            if prods_in:
                p_in = st.selectbox("Seleccionar:", prods_in, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
                c_in = st.number_input("Cantidad Unidades:", min_value=1, key=f"c_in_{st.session_state.form_count}")
                costo = st.number_input("Costo Contenedor:", value=int(p_in['precio_costo_contenedor']))
                if st.button("📥 Confirmar Entrada", use_container_width=True, type="primary"):
                    ok, msg = registrar_movimiento("entrada", p_in['sku'], c_in, p_in['und_x_embalaje'], st.session_state.usuario_ingresado, costo)
                    if ok: 
                        st.success("Entrada registrada y Mercado Libre actualizado!"); 
                        st.session_state.form_count += 1; 
                        st.rerun()

with t2:
    st.subheader("📋 Historial Reciente")
    h_e = supabase.table("entradas").select("*").order("fecha", desc=True).limit(15).execute().data
    h_s = supabase.table("salidas").select("*").order("fecha", desc=True).limit(15).execute().data
    hist = []
    for x in h_e: x['Tipo'] = "🟢 Entrada"; hist.append(x)
    for x in h_s: x['Tipo'] = "🔴 Salida"; hist.append(x)
    if hist:
        df_h = pd.DataFrame(hist).sort_values("fecha", ascending=False)
        st.dataframe(df_h[["fecha", "Tipo", "sku", "cantidad", "canal", "usuario"]], use_container_width=True)

with t3:
    st.subheader("📈 Estado de Inventario")
    all_p = buscar_productos()
    if all_p:
        df = pd.DataFrame(all_p)
        st.dataframe(df[["sku", "nombre", "stock_total", "und_x_embalaje", "precio_costo_contenedor"]], use_container_width=True)

with t4:
    st.subheader("⚙️ Configuración de Productos")
    with st.form("nuevo_p"):
        st.write("Añadir Nuevo Producto")
        n_sku = st.text_input("SKU").upper().strip()
        n_nom = st.text_input("Nombre")
        n_und = st.number_input("Unidades por Embalaje", min_value=1, value=1)
        if st.form_submit_button("Crear Producto"):
            if n_sku and n_nom:
                supabase.table("productos").insert({"sku": n_sku, "nombre": n_nom, "und_x_embalaje": n_und, "stock_total": 0}).execute()
                st.success("Producto creado!")
                st.rerun()
