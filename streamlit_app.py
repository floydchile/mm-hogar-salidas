import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os
import pandas as pd
from PIL import Image
import requests
import urllib.parse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="M&M Hogar - Sincro", page_icon="📦", layout="wide")

# Conexión con variables de Railway
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
MELI_USER_ID = os.getenv("MELI_USER_ID")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FUNCIÓN MAESTRA DE SINCRONIZACIÓN ---
def sincronizar_meli(sku, cantidad):
    """ Esta función es la que hace el trabajo sucio con la API de MeLi """
    if not MELI_TOKEN:
        return "❌ Error: No hay Token de MeLi configurado."
    
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    sku_limpio = str(sku).strip()
    
    try:
        # 1. Buscar el producto por SKU
        url_busqueda = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?sku={urllib.parse.quote(sku_limpio)}"
        r_search = requests.get(url_busqueda, headers=headers).json()
        
        if not r_search.get('results'):
            return f"❓ SKU '{sku_limpio}' no encontrado en tus publicaciones de MeLi."
        
        item_id = r_search['results'][0]
        
        # 2. Actualizar el stock
        url_upd = f"https://api.mercadolibre.com/items/{item_id}"
        data_upd = {"available_quantity": int(cantidad)}
        r_upd = requests.put(url_upd, json=data_upd, headers=headers)
        
        if r_upd.status_code == 200:
            return f"✅ MeLi Sincronizado: {sku_limpio} ahora tiene {cantidad} unidades."
        else:
            return f"❌ Error API MeLi: {r_upd.json().get('message')}"
            
    except Exception as e:
        return f"❌ Error de conexión: {str(e)}"

# --- LÓGICA DE WEBHOOK (RECIBIR VENTAS DE MELI) ---
# Si MeLi nos avisa de una venta, este bloque la procesa antes de mostrar la web
params = st.query_params
if "topic" in params and "resource" in params:
    if params.get("topic") == "orders_v2":
        try:
            res_path = params.get("resource")
            headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
            order = requests.get(f"https://api.mercadolibre.com{res_path}", headers=headers).json()
            
            for item in order.get('order_items', []):
                sku_vta = item.get('item', {}).get('seller_custom_field')
                cant_vta = item.get('quantity')
                if sku_vta:
                    supabase.rpc("registrar_salida", {
                        "p_sku": sku_vta.strip(), "p_cantidad": int(cant_vta),
                        "p_canal": "Mercadolibre", "p_usuario": "SISTEMA_MELI"
                    }).execute()
        except: pass
    st.stop()

# --- INTERFAZ ORIGINAL (RESUMIDA PARA PRUEBAS) ---
st.title("📦 MyM + Mercado Libre")

# Pestañas
tab_mov, tab_stock = st.tabs(["🛒 Movimientos", "📈 Stock"])

with tab_mov:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Registrar Venta Manual")
        # Selector de producto (traído de Supabase)
        prods = supabase.table("productos").select("*").execute().data
        if prods:
            p_sel = st.selectbox("Producto:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
            cant = st.number_input("Cantidad vendida:", min_value=1, value=1)
            
            if st.button("Finalizar Venta y Sincronizar", type="primary"):
                # 1. Registrar en Supabase
                res = supabase.rpc("registrar_salida", {
                    "p_sku": p_sel['sku'], "p_cantidad": cant,
                    "p_canal": "Venta Manual", "p_usuario": "Admin"
                }).execute()
                
                # 2. Obtener nuevo stock total
                nuevo_stock = supabase.table("productos").select("stock_total").eq("sku", p_sel['sku']).single().execute().data['stock_total']
                
                # 3. SINCRONIZAR CON MELI
                with st.spinner("Sincronizando con Mercado Libre..."):
                    resultado = sincronizar_meli(p_sel['sku'], nuevo_stock)
                
                if "✅" in resultado:
                    st.success(resultado)
                else:
                    st.warning(resultado)

with tab_stock:
    # Mostrar tabla de stock actual
    st.subheader("Estado actual en Base de Datos")
    st.dataframe(pd.DataFrame(prods)[["sku", "nombre", "stock_total"]], use_container_width=True)
