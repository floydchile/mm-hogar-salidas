import streamlit as st
from supabase import create_client, Client
import os
import pandas as pd
from PIL import Image
import requests
import urllib.parse

# --- CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="M&M Hogar - Gestión Total", page_icon="📦", layout="wide")

st.markdown("""<style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    .stMetric {background-color: #f8f9fa; border-radius: 10px; padding: 10px; border: 1px solid #eee;}
    [data-testid="stMetricValue"] {font-size: 1.8rem;}
</style>""", unsafe_allow_html=True)

# --- CONEXIÓN ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
MELI_USER_ID = os.getenv("MELI_USER_ID")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
USUARIOS_VALIDOS = ["pau", "dany", "miguel"]

# --- LÓGICA DE BÚSQUEDA AVANZADA MELI ---
def encontrar_item_id_meli(sku_objetivo):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    sku_clean = str(sku_objetivo).strip()
    
    # 1. Intentamos búsqueda por texto general (q)
    url_q = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?q={urllib.parse.quote(sku_clean)}"
    res_q = requests.get(url_q, headers=headers).json()
    ids = res_q.get('results', [])

    # 2. Si no hay resultados, probamos con las últimas 50 publicaciones (Barrido)
    if not ids:
        url_rec = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?sort=date_desc&limit=50"
        ids = requests.get(url_rec, headers=headers).json().get('results', [])

    for item_id in ids:
        det = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=headers).json()
        if det.get('status') not in ['active', 'paused']: continue
        
        # Revisamos SKU en campo principal y en atributos (Ficha técnica)
        sku_main = str(det.get('seller_custom_field', '')).strip()
        sku_attr = next((str(a.get('value_name', '')).strip() for a in det.get('attributes', []) if a.get('id') == 'SELLER_SKU'), "")
        
        if sku_clean in [sku_main, sku_attr]:
            return item_id
    return None

def sincronizar_stock_meli(sku, nuevo_stock):
    item_id = encontrar_item_id_meli(sku)
    if item_id:
        headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
        # Actualizamos stock y de paso "reparamos" el SKU en el campo principal
        requests.put(f"https://api.mercadolibre.com/items/{item_id}", 
                     json={"available_quantity": int(nuevo_stock), "seller_custom_field": sku}, 
                     headers=headers)
        return f"✅ Sincronizado en {item_id}"
    return "❌ No se halló publicación activa en MeLi"

# --- INTERFAZ ---
if 'usuario' not in st.session_state: st.session_state.usuario = None

with st.sidebar:
    if st.session_state.usuario:
        st.success(f"Usuario: {st.session_state.usuario.upper()}")
        if st.button("Cerrar Sesión"): 
            st.session_state.usuario = None
            st.rerun()
    else:
        user_input = st.text_input("Usuario:").lower().strip()
        if st.button("Entrar"):
            if user_input in USUARIOS_VALIDOS:
                st.session_state.usuario = user_input
                st.rerun()

if not st.session_state.usuario:
    st.title("📦 Acceso M&M Hogar")
    st.info("Ingresa tus credenciales en el panel izquierdo.")
    st.stop()

st.title("🚀 Gestión MyM & Mercado Libre")
t1, t2, t3 = st.tabs(["🛒 Ventas / Salidas", "📊 Inventario", "🛠️ Sincro Manual"])

with t1:
    prods = supabase.table("productos").select("*").order("sku").execute().data
    if prods:
        with st.form("form_salida"):
            p = st.selectbox("Producto:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']} (Stock: {x['stock_total']})")
            cant = st.number_input("Cantidad Vendida:", min_value=1, value=1)
            canal = st.selectbox("Canal:", ["Mercadolibre", "WhatsApp", "Local", "Web"])
            if st.form_submit_button("Finalizar Venta"):
                # 1. Descontar en Supabase
                supabase.rpc("registrar_salida", {"p_sku": p['sku'], "p_cantidad": cant, "p_canal": canal, "p_usuario": st.session_state.usuario}).execute()
                # 2. Obtener nuevo stock
                new_s = supabase.table("productos").select("stock_total").eq("sku", p['sku']).single().execute().data['stock_total']
                # 3. Sincronizar
                res_ml = sincronizar_stock_meli(p['sku'], new_s)
                st.write(res_ml)
                st.success("Operación terminada")
                st.rerun()

with t2:
    if prods:
        st.dataframe(pd.DataFrame(prods)[["sku", "nombre", "stock_total"]], use_container_width=True)

with t3:
    st.subheader("Forzar Sincronización Directa")
    c1, c2, c3 = st.columns(3)
    f_mlc = c1.text_input("ID MLC (ej: MLC2884836674)")
    f_sku = c2.text_input("SKU exacto")
    f_stk = c3.number_input("Stock a subir", min_value=0)
    if st.button("Ejecutar Sincro Forzada"):
        headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
        r = requests.put(f"https://api.mercadolibre.com/items/{f_mlc}", 
                         json={"available_quantity": int(f_stk), "seller_custom_field": f_sku}, headers=headers)
        if r.status_code == 200: st.success("🚀 ¡Actualizado!")
        else: st.error(f"Error: {r.json().get('message')}")
