import streamlit as st
from supabase import create_client, Client
import os
import pandas as pd
import requests
import urllib.parse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="M&M PRUEBAS - Motor de Ficha Técnica", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
MELI_USER_ID = "462191513" # Tu ID confirmado

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def buscar_por_ficha_tecnica(sku_objetivo):
    """Busca el SKU dentro de los atributos de las publicaciones"""
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    sku_limpio = str(sku_objetivo).strip()
    
    # Traemos las últimas 50 para asegurar que cubrimos las recientes
    url = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?sort=date_desc&limit=50"
    res = requests.get(url, headers=headers).json()
    ids = res.get('results', [])

    for item_id in ids:
        det = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=headers).json()
        
        # BUSCAMOS EN LA FICHA TÉCNICA (Lo que vimos en Colab)
        sku_en_ficha = next((str(a.get('value_name')).strip() 
                            for a in det.get('attributes', []) 
                            if a.get('id') == 'SELLER_SKU'), "")
        
        if sku_limpio == sku_en_ficha:
            return item_id
    return None

def sincronizar_mejorado(sku, cantidad):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    
    # 1. Intentar encontrar el ID por la ficha técnica
    item_id = buscar_por_ficha_tecnica(sku)
    
    if item_id:
        # 2. Actualizar Stock y REPARAR el campo seller_custom_field
        # Al enviarlo aquí, MeLi lo indexará y la próxima búsqueda será instantánea
        payload = {
            "available_quantity": int(cantidad),
            "seller_custom_field": sku 
        }
        r = requests.put(f"https://api.mercadolibre.com/items/{item_id}", json=payload, headers=headers)
        
        if r.status_code == 200:
            return f"✅ ¡LOGRADO! Producto {item_id} sincronizado y reparado."
        else:
            return f"❌ Error al actualizar: {r.json().get('message')}"
    
    return "❌ El SKU no se encontró en la ficha técnica de las últimas 50 publicaciones."

# --- INTERFAZ ---
st.title("🧪 Laboratorio: Sincro por Ficha Técnica")

prods = supabase.table("productos").select("*").order("sku").execute().data

if prods:
    with st.form("debug_sync"):
        st.write("### Probar con SKU: EBSP XXXG42")
        p_sel = st.selectbox("Producto:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
        st.info("Este botón buscará en los atributos 'SELLER_SKU' de Mercado Libre.")
        
        if st.form_submit_button("🔥 Ejecutar Sincronización"):
            with st.spinner("Escaneando fichas técnicas en MeLi..."):
                res = sincronizar_mejorado(p_sel['sku'], p_sel['stock_total'])
            
            if "✅" in res:
                st.success(res)
            else:
                st.error(res)

st.divider()
st.write("### Datos actuales en Supabase")
st.dataframe(pd.DataFrame(prods)[["sku", "nombre", "stock_total"]])
