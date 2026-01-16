import streamlit as st
from supabase import create_client, Client
import os
import requests
import urllib.parse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="M&M Hogar - Sincro Variantes", layout="wide")

# MENSAJE DE ADVERTENCIA SOLICITADO
st.warning("⚠️ **PAU - DANY ESTOY HACIENDO PRUEBAS, VUELVAN MAS RATO**")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def actualizar_stock_meli_variante(sku_buscado, nueva_cantidad):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    sku_clean = str(sku_buscado).strip()
    
    # 1. Buscar la publicación que contiene ese SKU (sea madre o variante)
    url_search = f"https://api.mercadolibre.com/users/{os.getenv('MELI_USER_ID')}/items/search?seller_custom_field={urllib.parse.quote(sku_clean)}"
    res_search = requests.get(url_search, headers=headers).json()
    
    if not res_search.get('results'):
        return f"❓ SKU {sku_clean} no encontrado en MeLi."

    item_id = res_search['results'][0] # Ejemplo: MLC1869578802
    
    # 2. Entrar a la publicación para buscar la variante correcta
    item_details = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=headers).json()
    
    variantes = item_details.get('variations', [])
    
    if variantes:
        # ES UNA PUBLICACIÓN CON VARIANTES
        id_variante = None
        for v in variantes:
            if str(v.get('seller_custom_field')).strip() == sku_clean:
                id_variante = v.get('id')
                break
        
        if id_variante:
            # Actualizar la variante específica
            url_upd = f"https://api.mercadolibre.com/items/{item_id}/variations/{id_variante}"
            payload = {"available_quantity": int(nueva_cantidad)}
            r_upd = requests.put(url_upd, json=payload, headers=headers)
        else:
            return f"❌ Se halló la publicación {item_id}, pero no la variante con SKU {sku_clean}."
    else:
        # ES UNA PUBLICACIÓN SIMPLE (SIN VARIANTES)
        url_upd = f"https://api.mercadolibre.com/items/{item_id}"
        payload = {"available_quantity": int(nueva_cantidad)}
        r_upd = requests.put(url_upd, json=payload, headers=headers)

    if r_upd.status_code == 200:
        return f"✅ Sincronizado: {sku_clean} -> {nueva_cantidad} uds."
    else:
        return f"❌ Error MeLi: {r_upd.json().get('message')}"

# --- INTERFAZ DE PRUEBA ---
st.title("🛒 Prueba de Sincronización por Variantes")

try:
    prods = supabase.table("productos").select("*").order("sku").execute().data
    if prods:
        p_sel = st.selectbox("Producto MyM:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
        stock_test = st.number_input("Nuevo Stock para MeLi:", value=int(p_sel['stock_total']))
        
        if st.button("🚀 Sincronizar Stock"):
            with st.spinner("Buscando variante y actualizando..."):
                resultado = actualizar_stock_meli_variante(p_sel['sku'], stock_test)
                
            if "✅" in resultado:
                st.success(resultado)
            else:
                st.error(resultado)
                
except Exception as e:
    st.error(f"Error: {e}")
