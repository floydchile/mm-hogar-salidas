import streamlit as st
from supabase import create_client, Client
import os
import pandas as pd
import requests
import urllib.parse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="M&M Hogar - Sincro Robusta", layout="wide")
st.warning("⚠️ **PAU - DANY: MODO RESCATE ACTIVADO**")

# Conexión
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
MELI_USER_ID = os.getenv("MELI_USER_ID")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def sincronizar_producto_final(sku_objetivo, nueva_cantidad):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    sku_clean = str(sku_objetivo).strip()
    
    # 1. INTENTO RAPIDO: Búsqueda por SKU
    url_search = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?q={urllib.parse.quote(sku_clean)}"
    ids_potenciales = requests.get(url_search, headers=headers).json().get('results', [])
    
    # 2. INTENTO DE RESPALDO: Ver últimas 50 publicaciones del vendedor (Barrido)
    if not ids_potenciales:
        url_recent = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?sort=date_desc&limit=50"
        ids_potenciales = requests.get(url_recent, headers=headers).json().get('results', [])

    item_id_final = None
    detalles_encontrados = []

    # 3. INSPECCIÓN EXHAUSTIVA
    for item_id in ids_potenciales:
        det = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=headers).json()
        
        # Guardamos datos para diagnóstico si falla
        sku_attr = next((str(a.get('value_name', '')).strip() for a in det.get('attributes', []) if a.get('id') == 'SELLER_SKU'), "")
        sku_main = str(det.get('seller_custom_field', '')).strip()
        
        status = det.get('status')
        detalles_encontrados.append(f"ID: {item_id} | Status: {status} | SKU_Attr: {sku_attr}")

        if sku_clean in [sku_attr, sku_main] and status in ['active', 'paused']:
            item_id_final = item_id
            break
            
    if not item_id_final:
        st.error("🔍 **Diagnóstico de búsqueda:**")
        for d in detalles_encontrados[:5]: st.write(d) # Mostrar solo los primeros 5
        return f"❌ No se encontró la publicación ACTIVA para '{sku_clean}'."

    # 4. ACTUALIZACIÓN
    url_upd = f"https://api.mercadolibre.com/items/{item_id_final}"
    payload = {"available_quantity": int(nueva_cantidad), "seller_custom_field": sku_clean}
    r_upd = requests.put(url_upd, json=payload, headers=headers)
    
    if r_upd.status_code == 200:
        return f"✅ Sincronizado en {item_id_final} ({nueva_cantidad} uds)."
    else:
        return f"❌ Error MeLi: {r_upd.json().get('message')}"

# --- INTERFAZ ---
st.title("📦 Panel de Control MyM")

tab1, tab2, tab3 = st.tabs(["🚀 Salida Automática", "🛠️ Sincro Manual", "📊 Stock"])

with tab1:
    prods = supabase.table("productos").select("*").order("sku").execute().data
    if prods:
        with st.form("venta_auto"):
            p = st.selectbox("Producto:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
            cant = st.number_input("Cantidad:", min_value=1, value=1)
            if st.form_submit_button("Registrar y Sincronizar"):
                supabase.rpc("registrar_salida", {"p_sku": p['sku'], "p_cantidad": cant, "p_canal": "Venta", "p_usuario": "Admin"}).execute()
                stock_f = supabase.table("productos").select("stock_total").eq("sku", p['sku']).single().execute().data['stock_total']
                res = sincronizar_producto_final(p['sku'], stock_f)
                if "✅" in res: st.success(res)
                else: st.error(res)

with tab2:
    st.subheader("Si el buscador falla, usa esto:")
    col1, col2, col3 = st.columns(3)
    with col1: mlc_manual = st.text_input("ID Publicación (ej: MLC2884836674)")
    with col2: sku_manual = st.text_input("SKU en MyM (ej: EBSP XXXG42)")
    with col3: stock_manual = st.number_input("Stock Real", min_value=0)
    
    if st.button("Forzar Sincronización Manual"):
        headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
        res = requests.put(f"https://api.mercadolibre.com/items/{mlc_manual}", 
                           json={"available_quantity": int(stock_manual), "seller_custom_field": sku_manual}, 
                           headers=headers)
        if res.status_code == 200: st.success("🚀 ¡Forzado con éxito!")
        else: st.error(f"Error: {res.json().get('message')}")

with tab3:
    if prods: st.dataframe(pd.DataFrame(prods)[["sku", "nombre", "stock_total"]], use_container_width=True)
