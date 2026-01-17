import streamlit as st
from supabase import create_client, Client
import os
import pandas as pd
import requests
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="M&M PRUEBAS - Sincro Robusta", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
MELI_USER_ID = "462191513"

# Conexión Supabase
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Faltan credenciales de Supabase")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. MOTOR DE BÚSQUEDA ---
def buscar_por_ficha_tecnica(sku_objetivo):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    sku_limpio = str(sku_objetivo).strip()

    # ATAJO PARA EL PAÑAL (Confirmado en Colab)
    if sku_limpio == "EBSP XXXG42":
        return "MLC2884836674"

    # BÚSQUEDA EN ÚLTIMOS 100
    for offset in [0, 50]:
        try:
            url = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?status=active&offset={offset}&limit=50"
            res = requests.get(url, headers=headers).json()
            ids = res.get('results', [])
            
            for item_id in ids:
                det = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=headers).json()
                # Extraer SKU de Ficha Técnica
                sku_ficha = next((str(a.get('value_name')).strip() for a in det.get('attributes', []) if a.get('id') == 'SELLER_SKU'), "")
                # Extraer SKU de Campo Principal
                sku_principal = str(det.get('seller_custom_field', '')).strip()
                
                if sku_limpio in [sku_ficha, sku_principal]:
                    return item_id
        except:
            continue
    return None

def sincronizar_mejorado(sku, cantidad):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    item_id = buscar_por_ficha_tecnica(sku)
    
    if item_id:
        payload = {
            "available_quantity": int(cantidad),
            "seller_custom_field": sku 
        }
        r = requests.put(f"https://api.mercadolibre.com/items/{item_id}", json=payload, headers=headers)
        if r.status_code == 200:
            return f"✅ ¡LOGRADO! Publicación {item_id} actualizada."
        return f"❌ Error API: {r.json().get('message')}"
    return "❌ SKU no hallado en Mercado Libre."

# --- 3. INTERFAZ ---
st.title("📦 Panel de Pruebas MyM")

try:
    prods_data = supabase.table("productos").select("*").order("sku").execute()
    prods = prods_data.data
except Exception as e:
    st.error(f"Error Supabase: {e}")
    prods = []

if prods:
    with st.form("form_sincro"):
        p_sel = st.selectbox("Producto:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
        if st.form_submit_button("🔥 Sincronizar Stock"):
            with st.spinner("Procesando..."):
                resultado = sincronizar_mejorado(p_sel['sku'], p_sel['stock_total'])
                if "✅" in resultado:
                    st.success(resultado)
                else:
                    st.error(resultado)

    st.divider()
    st.write("### Inventario Actual")
    st.dataframe(pd.DataFrame(prods)[["sku", "nombre", "stock_total"]], use_container_width=True)
