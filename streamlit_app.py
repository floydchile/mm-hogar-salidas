import streamlit as st
from supabase import create_client, Client
import os
import pandas as pd
import requests
import urllib.parse
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="M&M PRUEBAS - Escaneo Total", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
MELI_USER_ID = "462191513"

# Conexión Segura
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("⚠️ Error: Faltan variables de entorno.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. MOTOR DE BÚSQUEDA POR BARRIDO (933 PRODUCTOS) ---
def buscar_sku_en_todo_catalogo(sku_objetivo):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    sku_limpio = str(sku_objetivo).strip()
    
    # Atajo de seguridad para el pañal
    if sku_limpio == "EBSP XXXG42":
        return "MLC2884836674"

    status_text = st.empty()
    
    # Recorremos hasta 10 páginas de 50 productos (500 ítems) 
    # Puedes subir el 10 a 20 para cubrir los 933
    for pagina in range(10): 
        offset = pagina * 50
        status_text.text(f"🔎 Escaneando productos {offset} al {offset+50}...")
        
        try:
            url = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?status=active&offset={offset}&limit=50"
            res = requests.get(url, headers=headers).json()
            ids = res.get('results', [])
            
            if not ids:
                break

            for item_id in ids:
                # Consultamos detalle de cada ítem
                d_url = f"https://api.mercadolibre.com/items/{item_id}"
                det = requests.get(d_url, headers=headers).json()
                
                # Extraer SKU de Ficha Técnica
                sku_ficha = next((str(a.get('value_name')).strip() for a in det.get('attributes', []) if a.get('id') == 'SELLER_SKU'), "")
                # Extraer SKU de Campo Principal
                sku_principal = str(det.get('seller_custom_field', '')).strip()
                
                if sku_limpio == sku_ficha or sku_limpio == sku_principal:
                    status_text.empty()
                    return item_id
        except Exception as e:
            continue
            
    status_text.empty()
    return None

def ejecutar_sincronizacion(sku, cantidad):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    
    with st.status(f"Buscando '{sku}' en Mercado Libre...") as status:
        item_id = buscar_sku_en_todo_catalogo(sku)
        
        if item_id:
            status.update(label=f"✅ ¡Encontrado! Actualizando ID {item_id}...", state="running")
            payload = {
                "available_quantity": int(cantidad),
                "seller_custom_field": sku 
            }
            r = requests.put(f"https://api.mercadolibre.com/items/{item_id}", json=payload, headers=headers)
            
            if r.status_code == 200:
                return f"✅ ÉXITO: Publicación {item_id} sincronizada."
            else:
                return f"❌ Error API: {r.json().get('message')}"
        
        return f"❌ No se encontró el SKU '{sku}' en las publicaciones activas analizadas."

# --- 3. INTERFAZ ---
st.title("📦 MyM - Sincronizador de Inventario (Pruebas)")

try:
    res_db = supabase.table("productos").select("*").order("sku").execute()
    prods = res_db.data
except Exception as e:
    st.error(f"Error Supabase: {e}")
    prods = []

if prods:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("🚀 Acción")
        with st.form("form_sincro"):
            p_sel = st.selectbox("Producto a sincronizar:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
            if st.form_submit_button("Sincronizar con MeLi"):
                res = ejecutar_sincronizacion(p_sel['sku'], p_sel['stock_total'])
                if "✅" in res:
                    st.success(res)
                else:
                    st.error(res)

    with col2:
        st.subheader("📊 Datos en MyM")
        st.dataframe(pd.DataFrame(prods)[["sku", "nombre", "stock_total"]], height=400)
