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

# --- LÓGICA DE WEBHOOK (RECEPCIÓN DE VENTAS DE MELI) ---
# Esta sección detecta si Mercado Libre está enviando una notificación
if "topic" in st.query_params:
    topic = st.query_params.get("topic")
    resource = st.query_params.get("resource")
    MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
    
    if topic == "orders_v2":
        # 1. Consultar detalle de la orden
        headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
        order_res = requests.get(f"https://api.mercadolibre.com{resource}", headers=headers).json()
        
        # 2. Procesar productos vendidos
        for item in order_res.get('order_items', []):
            sku = item.get('item', {}).get('seller_custom_field')
            cant = item.get('quantity')
            if sku:
                # 3. Descontar en Supabase usando el BOT
                # Nota: Definiremos registrar_movimiento más abajo, pero aquí se llama internamente
                try:
                    SUPABASE_URL = os.getenv("SUPABASE_URL")
                    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
                    client = create_client(SUPABASE_URL, SUPABASE_KEY)
                    client.rpc("registrar_salida", {
                        "p_sku": sku, "p_cantidad": int(cant), 
                        "p_canal": "Mercadolibre", "p_usuario": "BOT_MELI"
                    }).execute()
                except: pass
    st.stop() # Evita que se cargue la interfaz visual para MeLi

# --- CONTINUACIÓN DE LA APP NORMAL ---
st.markdown("""<style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    .stMetric {background-color: #f8f9fa; border-radius: 10px; padding: 10px; border: 1px solid #eee;}
    input[type=number]::-webkit-inner-spin-button, input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
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
    st.error("❌ Error: Faltan las credenciales de Supabase.")
    st.stop()

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()
USUARIOS_VALIDOS = ["pau", "dany", "miguel"]

# --- FUNCIONES DE INTEGRACIÓN ---
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
        
        # Sincronizar hacia MeLi después de cualquier cambio en MyM
        prod_data = supabase.table("productos").select("stock_total").eq("sku", sku).single().execute()
        if prod_data.data:
            sincronizar_stock_meli(sku, prod_data.data['stock_total'])
        return True, "Ok"
    except Exception as e: return False, str(e)

# --- (El resto de tu interfaz de pestañas e historial se mantiene igual) ---
# ... [Pega aquí el código de los TABS que ya tenías funcionando anteriormente]
