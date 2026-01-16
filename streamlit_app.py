import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os
import pandas as pd
from PIL import Image
import requests
import urllib.parse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="M&M Hogar", page_icon="📦", layout="wide")

# --- LÓGICA DE WEBHOOK (MERCADO LIBRE A MYM) ---
# Esta sección debe ir PRIMERO para interceptar las ventas
params = st.query_params
if "topic" in params and "resource" in params:
    topic = params.get("topic")
    resource = params.get("resource")
    token = os.getenv("MELI_ACCESS_TOKEN")
    
    if topic == "orders_v2":
        try:
            headers = {'Authorization': f'Bearer {token}'}
            # Consultamos la venta a Mercado Libre
            res_order = requests.get(f"https://api.mercadolibre.com{resource}", headers=headers).json()
            for item in res_order.get('order_items', []):
                sku = item.get('item', {}).get('seller_custom_field')
                cant = item.get('quantity')
                if sku:
                    # Descontamos en Supabase
                    sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
                    sb.rpc("registrar_salida", {
                        "p_sku": sku, "p_cantidad": int(cant), 
                        "p_canal": "Mercadolibre", "p_usuario": "BOT_MELI"
                    }).execute()
        except: pass
    st.stop() # Importante: No cargar el resto de la web si es MeLi quien llama

# --- ESTILOS ---
st.markdown("""<style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    .stMetric {background-color: #f8f9fa; border-radius: 10px; padding: 10px; border: 1px solid #eee;}
</style>""", unsafe_allow_html=True)

# --- CONEXIÓN ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
MELI_USER_ID = os.getenv("MELI_USER_ID")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
USUARIOS_VALIDOS = ["pau", "dany", "miguel"]

# --- FUNCIONES ---
def sincronizar_stock_meli(sku, nuevo_stock):
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
    try:
        if tipo == "entrada":
            if precio is not None:
                supabase.table("productos").update({"precio_costo_contenedor": float(precio)}).eq("sku", sku).execute()
            supabase.rpc("registrar_entrada", {"p_sku": sku, "p_cantidad": int(cantidad), "p_und_x_embalaje": extra_val, "p_usuario": usuario}).execute()
        else:
            res = supabase.rpc("registrar_salida", {"p_sku": sku, "p_cantidad": int(cantidad), "p_canal": extra_val, "p_usuario": usuario}).execute()
            if "ERROR" in res.data: return False, res.data
        
        # Sincronizar MeLi
        prod = supabase.table("productos").select("stock_total").eq("sku", sku).single().execute()
        if prod.data:
            sincronizar_stock_meli(sku, prod.data['stock_total'])
        return True, "Ok"
    except Exception as e: return False, str(e)

# --- INTERFAZ ---
if 'user' not in st.session_state: st.session_state.user = None
if 'count' not in st.session_state: st.session_state.count = 0

with st.sidebar:
    if st.session_state.user:
        st.write(f"Sesión: {st.session_state.user.upper()}")
        if st.button("Salir"): 
            st.session_state.user = None
            st.rerun()
    else:
        u = st.text_input("Usuario:").lower().strip()
        if st.button("Ingresar"):
            if u in USUARIOS_VALIDOS:
                st.session_state.user = u
                st.rerun()

if not st.session_state.user:
    st.info("Ingresa para continuar")
    st.stop()

t1, t2, t3, t4 = st.tabs(["🛒 Movimientos", "📋 Historial", "📈 Stock", "⚙️ Configuración"])

with t1:
    st.subheader("Registrar Movimiento")
    sk = st.text_input("Buscar SKU", key=f"s_{st.session_state.count}").upper()
    if sk:
        p = supabase.table("productos").select("*").ilike("sku", f"%{sk}%").execute().data
        if p:
            sel = st.selectbox("Producto:", p, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
            c1, c2 = st.columns(2)
            with c1:
                cant_v = st.number_input("Cantidad Venta:", min_value=1)
                can = st.selectbox("Canal:", ["Mercadolibre", "WhatsApp", "Retiro"])
                if st.button("Vender", width="stretch"):
                    ok, m = registrar_movimiento("salida", sel['sku'], cant_v, can, st.session_state.user)
                    if ok: st.success("Vendido!"); st.session_state.count += 1; st.rerun()
            with c2:
                cant_e = st.number_input("Cantidad Entrada:", min_value=1)
                if st.button("Cargar Entrada", width="stretch"):
                    ok, m = registrar_movimiento("entrada", sel['sku'], cant_e, sel['und_x_embalaje'], st.session_state.user)
                    if ok: st.success("Cargado!"); st.session_state.count += 1; st.rerun()

with t2:
    st.subheader("Historial")
    h = supabase.table("salidas").select("*").order("fecha", desc=True).limit(10).execute().data
    if h: st.table(pd.DataFrame(h)[["fecha", "sku", "cantidad", "canal", "usuario"]])

with t3:
    st.subheader("Stock Actual")
    s = supabase.table("productos").select("sku", "nombre", "stock_total").order("sku").execute().data
    if s: st.dataframe(pd.DataFrame(s), width="stretch")

with t4:
    with st.form("nuevo"):
        st.write("Nuevo Producto")
        ns = st.text_input("SKU").upper()
        nn = st.text_input("Nombre")
        if st.form_submit_button("Crear"):
            supabase.table("productos").insert({"sku": ns, "nombre": nn, "stock_total": 0}).execute()
            st.rerun()
