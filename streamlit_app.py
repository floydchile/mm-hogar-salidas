import streamlit as st
from supabase import create_client, Client
import os
import pandas as pd
import requests
import urllib.parse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="M&M Hogar - Sincronización Total", layout="wide")

# MENSAJE PARA EL EQUIPO
st.warning("⚠️ **PAU - DANY ESTOY HACIENDO PRUEBAS, VUELVAN MAS RATO**")

# Conexión
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
MELI_USER_ID = os.getenv("MELI_USER_ID")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def buscar_en_meli_exhaustivo(sku_objetivo):
    """Intenta 3 métodos diferentes para encontrar el producto en MeLi"""
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    sku_clean = str(sku_objetivo).strip()
    encoded_sku = urllib.parse.quote(sku_clean)
    
    # MÉTODO 1: Por parámetro oficial de SKU
    url1 = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?seller_custom_field={encoded_sku}"
    res1 = requests.get(url1, headers=headers).json()
    ids = res1.get('results', [])
    
    # MÉTODO 2: Por búsqueda de texto general (si el 1 falló)
    if not ids:
        url2 = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?q={encoded_sku}"
        res2 = requests.get(url2, headers=headers).json()
        ids = res2.get('results', [])
        
    # MÉTODO 3: Búsqueda por SKU en el filtro de ítems
    if not ids:
        url3 = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?sku={encoded_sku}"
        res3 = requests.get(url3, headers=headers).json()
        ids = res3.get('results', [])

    return list(set(ids)) # Devolvemos IDs únicos

def sincronizar_producto(sku_objetivo, nueva_cantidad):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    sku_clean = str(sku_objetivo).strip()
    
    # 1. Buscar IDs potenciales
    ids_potenciales = buscar_en_meli_exhaustivo(sku_clean)
    
    if not ids_potenciales:
        return f"❓ No se encontró el SKU '{sku_clean}' por ningún método de búsqueda."

    item_id_final = None
    
    # 2. Inspeccionar cada ID para confirmar el SKU en atributos
    for item_id in ids_potenciales:
        det = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=headers).json()
        
        # Verificamos estado
        if det.get('status') not in ['active', 'paused']:
            continue
            
        # Revisamos SKU en campo principal y en atributos (lo que vimos en el JSON anterior)
        sku_main = str(det.get('seller_custom_field', '')).strip()
        sku_attr = next((str(a.get('value_name', '')).strip() for a in det.get('attributes', []) if a.get('id') == 'SELLER_SKU'), "")
        
        if sku_clean == sku_main or sku_clean == sku_attr:
            item_id_final = item_id
            break
            
    if not item_id_final:
        return f"❌ SKU '{sku_clean}' hallado en registros pero ninguna publicación está ACTIVA."

    # 3. ACTUALIZACIÓN Y "REPARACIÓN"
    # Al enviar seller_custom_field aquí, "arreglamos" el producto para que MeLi lo encuentre más rápido la próxima vez
    url_upd = f"https://api.mercadolibre.com/items/{item_id_final}"
    payload = {
        "available_quantity": int(nueva_cantidad),
        "seller_custom_field": sku_clean 
    }
    r_upd = requests.put(url_upd, json=payload, headers=headers)
    
    if r_upd.status_code == 200:
        return f"✅ Sincronizado con éxito en {item_id_final} ({nueva_cantidad} uds)."
    else:
        return f"❌ Error MeLi: {r_upd.json().get('message')}"

# --- INTERFAZ STREAMLIT ---
st.title("📦 Sistema de Gestión MyM Hogar")

tab1, tab2 = st.tabs(["🚀 Salida de Stock", "📊 Inventario"])

with tab1:
    try:
        prods = supabase.table("productos").select("*").order("sku").execute().data
        if prods:
            with st.form("venta_form"):
                p_sel = st.selectbox("Producto:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']} (Stock: {x['stock_total']})")
                cant = st.number_input("Cantidad a descontar:", min_value=1, value=1)
                submit = st.form_submit_button("Finalizar y Sincronizar", use_container_width=True)
                
                if submit:
                    # 1. Supabase
                    supabase.rpc("registrar_salida", {
                        "p_sku": p_sel['sku'], "p_cantidad": cant,
                        "p_canal": "Venta Manual", "p_usuario": "Admin"
                    }).execute()
                    
                    # 2. Stock final
                    stock_f = supabase.table("productos").select("stock_total").eq("sku", p_sel['sku']).single().execute().data['stock_total']
                    
                    # 3. MeLi
                    with st.spinner("Sincronizando con Mercado Libre..."):
                        res_meli = sincronizar_producto(p_sel['sku'], stock_f)
                    
                    if "✅" in res_meli: st.success(res_meli)
                    else: st.error(res_meli)
                    
    except Exception as e:
        st.error(f"Error: {e}")

with tab2:
    if 'prods' in locals() and prods:
        st.dataframe(pd.DataFrame(prods)[["sku", "nombre", "stock_total"]], use_container_width=True)
