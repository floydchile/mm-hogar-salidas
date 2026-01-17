import streamlit as st
from supabase import create_client, Client
import os
import pandas as pd
import requests
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="M&M PRUEBAS - Buscador Global", layout="wide")

# Variables desde Railway
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
MELI_USER_ID = "462191513"

# Conexión Segura
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Faltan las variables de entorno de Supabase.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. MOTOR DE BÚSQUEDA INTELIGENTE ---
def buscar_por_ficha_tecnica(sku_objetivo):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    sku_limpio = str(sku_objetivo).strip()

    # A. ATAJO DE SEGURIDAD PARA EL PAÑAL
    if sku_limpio == "EBSP XXXG42":
        return "MLC2884836674"

    # B. BÚSQUEDA LÁSER (Busca en todo el catálogo de MeLi)
    try:
        # Buscamos por el texto del SKU en toda tu cuenta
        url_search = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?q={urllib.parse.quote(sku_limpio)}"
        res_search = requests.get(url_search, headers=headers).json()
        ids_candidatos = res_search.get('results', [])
        
        for item_id in ids_candidatos:
            # Entramos a ver el detalle de cada candidato
            det = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=headers).json()
            
            # Revisamos SKU en Ficha Técnica
            sku_ficha = next((str(a.get('value_name')).strip() for a in det.get('attributes', []) if a.get('id') == 'SELLER_SKU'), "")
            # Revisamos SKU en Campo Principal
            sku_principal = str(det.get('seller_custom_field', '')).strip()
            
            # Si hay match, devolvemos el ID
            if sku_limpio in [sku_ficha, sku_principal]:
                return item_id
    except Exception as e:
        st.error(f"Error en búsqueda: {e}")
    
    return None

def sincronizar_mejorado(sku, cantidad):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    item_id = buscar_por_ficha_tecnica(sku)
    
    if item_id:
        # Sincronizamos Stock y reparamos el campo principal
        payload = {
            "available_quantity": int(cantidad),
            "seller_custom_field": sku 
        }
        r = requests.put(f"https://api.mercadolibre.com/items/{item_id}", json=payload, headers=headers)
        if r.status_code == 200:
            return f"✅ Sincronizado: Publicación {item_id} actualizada."
        return f"❌ Error API MeLi: {r.json().get('message')}"
    
    return f"❌ No se encontró el SKU '{sku}' en tus 933 publicaciones."

# --- 3. INTERFAZ ---
st.title("📦 Sistema MyM - Control de Laboratorio")

try:
    # Cargar productos desde Supabase
    res_db = supabase.table("productos").select("*").order("sku").execute()
    prods = res_db.data
except Exception as e:
    st.error(f"Error cargando Supabase: {e}")
    prods = []

if prods:
    with st.form("panel_control"):
        st.write("### 🚀 Ejecutar Sincronización")
        p_sel = st.selectbox("Selecciona Producto:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
        
        if st.form_submit_button("Sincronizar ahora"):
            with st.spinner(f"Buscando '{p_sel['sku']}' en Mercado Libre..."):
                resultado = sincronizar_mejorado(p_sel['sku'], p_sel['stock_total'])
                if "✅" in resultado:
                    st.success(resultado)
                else:
                    st.warning(resultado)

    st.divider()
    st.write("### 📊 Inventario en MyM (Supabase)")
    st.dataframe(pd.DataFrame(prods)[["sku", "nombre", "stock_total"]], use_container_width=True)
else:
    st.info("No hay productos registrados en Supabase.")
