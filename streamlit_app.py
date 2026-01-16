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

# Conexión
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
MELI_USER_ID = os.getenv("MELI_USER_ID")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def sincronizar_meli(sku, cantidad):
    if not MELI_TOKEN: return "⚠️ Sin Token MeLi"
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    # Limpiamos el SKU de cualquier espacio accidental
    sku_clean = str(sku).strip()
    
    try:
        # BÚSQUEDA REFORZADA: Probamos buscar por el campo específico de vendedor
        url_busqueda = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?seller_custom_field={urllib.parse.quote(sku_clean)}"
        r_search = requests.get(url_busqueda, headers=headers).json()
        
        # Si no lo encuentra así, intentamos la búsqueda general por SKU
        if not r_search.get('results'):
            url_busqueda = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?sku={urllib.parse.quote(sku_clean)}"
            r_search = requests.get(url_busqueda, headers=headers).json()

        if r_search.get('results'):
            item_id = r_search['results'][0]
            # Actualizamos stock
            res_upd = requests.put(f"https://api.mercadolibre.com/items/{item_id}", 
                                   json={"available_quantity": int(cantidad)}, 
                                   headers=headers)
            
            if res_upd.status_code == 200:
                return f"✅ MeLi Sincronizado ({cantidad} uds)"
            else:
                error_msg = res_upd.json().get('message', 'Error desconocido')
                return f"❌ MeLi rechazó el cambio: {error_msg}"
            
        return f"❓ SKU '{sku_clean}' no hallado en MeLi. Revisa espacios."
    except Exception as e:
        return f"❌ Error técnico: {str(e)}"

# --- INTERFAZ (Tu versión estable con Sincro) ---
if 'form_count' not in st.session_state: st.session_state.form_count = 0

st.title("📦 M&M Hogar - Gestión")

# Selector de producto desde Supabase
try:
    prods = supabase.table("productos").select("*").order("sku").execute().data
    if prods:
        p_sel = st.selectbox("Producto a vender:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']} (Disp: {x['stock_total']})")
        cant = st.number_input("Cantidad:", min_value=1, value=1)
        
        if st.button("🚀 Finalizar Venta y Sincronizar", type="primary"):
            # 1. Registrar en Supabase
            res = supabase.rpc("registrar_salida", {
                "p_sku": p_sel['sku'], "p_cantidad": cant,
                "p_canal": "Mercadolibre", "p_usuario": "Admin"
            }).execute()
            
            # 2. Obtener el stock real que quedó después del descuento
            stock_actualizado = supabase.table("productos").select("stock_total").eq("sku", p_sel['sku']).single().execute().data['stock_total']
            
            # 3. Sincronizar con MeLi
            with st.spinner("Actualizando Mercado Libre..."):
                resultado = sincronizar_meli(p_sel['sku'], stock_actualizado)
            
            if "✅" in resultado:
                st.success(resultado)
            else:
                st.warning(resultado)
            
            st.rerun()
except Exception as e:
    st.error(f"Error de conexión: {e}")
