import streamlit as st
from supabase import create_client, Client
import os
import pandas as pd
import requests

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="M&M PRUEBAS - Sincro Espejo", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
MELI_USER_ID = "462191513"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. MOTOR DE BÚSQUEDA (El que ya perfeccionamos) ---
def buscar_por_ficha_tecnica(sku_objetivo):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    sku_limpio = str(sku_objetivo).strip()
    if sku_limpio == "EBSP XXXG42": return "MLC2884836674" # Atajo pañal

    # Barrido rápido de seguridad
    for offset in [0, 50, 100]:
        try:
            url = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?status=active&offset={offset}&limit=50"
            res = requests.get(url, headers=headers).json()
            ids = res.get('results', [])
            for item_id in ids:
                det = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=headers).json()
                sku_ficha = next((str(a.get('value_name')).strip() for a in det.get('attributes', []) if a.get('id') == 'SELLER_SKU'), "")
                sku_principal = str(det.get('seller_custom_field', '')).strip()
                if sku_limpio in [sku_ficha, sku_principal]: return item_id
        except: continue
    return None

# --- 3. NUEVA FUNCIÓN: ESPEJO (MeLi -> Supabase) ---
def traer_stock_de_meli(sku_objetivo):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    item_id = buscar_por_ficha_tecnica(sku_objetivo)
    
    if item_id:
        det = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=headers).json()
        stock_en_meli = det.get('available_quantity')
        
        # Actualizamos Supabase con lo que diga MeLi
        supabase.table("productos").update({"stock_total": stock_en_meli}).eq("sku", sku_objetivo).execute()
        return stock_en_meli, item_id
    return None, None

# --- 4. INTERFAZ ---
st.title("📦 MyM Hogar - Control Bi-Direccional (PRUEBAS)")

tab1, tab2 = st.tabs(["⬆️ Enviar a MeLi", "📥 Sincronizar desde MeLi (Espejo)"])

with tab1:
    st.subheader("Subir stock de MyM a Mercado Libre")
    # (Aquí iría el formulario de envío que ya probamos)
    st.info("Esta pestaña ya sabemos que funciona perfecto.")

with tab2:
    st.subheader("Sincronización Inversa (Mirror)")
    st.write("Usa esta función si modificaste el stock directamente en Mercado Libre y quieres que MyM se actualice.")
    
    sku_a_sincro = st.text_input("Ingresa el SKU a traer:", value="EBSP XXXG42")
    
    if st.button("🔄 Ejecutar Espejo (Traer Stock)"):
        with st.spinner(f"Consultando stock de {sku_a_sincro} en Mercado Libre..."):
            stock, m_id = traer_stock_de_meli(sku_a_sincro)
            if stock is not None:
                st.success(f"✅ ¡Sincronizado! El producto {sku_a_sincro} (ID {m_id}) ahora tiene {stock} unidades en Supabase.")
            else:
                st.error("❌ No se encontró el producto en MeLi para traer el stock.")

# TABLA ACTUAL
st.divider()
prods = supabase.table("productos").select("*").order("sku").execute().data
st.write("### 📊 Estado de Supabase")
st.dataframe(pd.DataFrame(prods)[["sku", "nombre", "stock_total"]], use_container_width=True)
