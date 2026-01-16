import streamlit as st
from supabase import create_client, Client
import os
import pandas as pd
import requests
import urllib.parse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="M&M Hogar - Debug", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
MELI_USER_ID = os.getenv("MELI_USER_ID")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def buscar_en_meli_debug(sku_buscado):
    """Busca el producto y devuelve detalles técnicos si falla"""
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    sku_clean = str(sku_buscado).strip()
    
    # 1. Intentar búsqueda por seller_custom_field (SKU)
    url = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?seller_custom_field={urllib.parse.quote(sku_clean)}"
    r = requests.get(url, headers=headers).json()
    
    if r.get('results'):
        return {"status": "ok", "id": r['results'][0]}
    
    # 2. Si falló, intentar búsqueda general para ver qué existe
    url_all = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?limit=5"
    r_all = requests.get(url_all, headers=headers).json()
    
    return {
        "status": "error",
        "msg": f"SKU '{sku_clean}' no encontrado.",
        "debug": r_all.get('results', []) # Traemos IDs de otros productos para ver si el token funciona
    }

st.title("📦 Sistema de Gestión + Debug MeLi")

# Placeholder para mensajes (esto evita que desaparezcan al recargar)
mensaje_log = st.empty()

try:
    prods = supabase.table("productos").select("*").order("sku").execute().data
    if prods:
        p_sel = st.selectbox("Producto:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
        cant = st.number_input("Cantidad:", min_value=1, value=1)
        
        if st.button("🚀 Ejecutar Venta y Sincronizar"):
            # 1. Registro en Supabase
            supabase.rpc("registrar_salida", {
                "p_sku": p_sel['sku'], "p_cantidad": cant,
                "p_canal": "Mercadolibre", "p_usuario": "Admin"
            }).execute()
            
            stock_f = supabase.table("productos").select("stock_total").eq("sku", p_sel['sku']).single().execute().data['stock_total']
            
            # 2. Sincronización con MeLi
            res_debug = buscar_en_meli_debug(p_sel['sku'])
            
            if res_debug["status"] == "ok":
                item_id = res_debug["id"]
                upd = requests.put(f"https://api.mercadolibre.com/items/{item_id}", 
                                   json={"available_quantity": int(stock_f)}, 
                                   headers={'Authorization': f'Bearer {MELI_TOKEN}'})
                if upd.status_code == 200:
                    mensaje_log.success(f"✅ ¡Sincronizado! {p_sel['sku']} actualizado a {stock_f} en MeLi.")
                else:
                    mensaje_log.error(f"❌ Error al subir stock: {upd.json().get('message')}")
            else:
                mensaje_log.warning(f"❓ {res_debug['msg']}")
                with st.expander("Ver detalles técnicos del error"):
                    st.write("Tu Token parece estar funcionando porque veo estos otros productos en tu cuenta:")
                    st.write(res_debug["debug"])
                    st.write("Pero ninguno coincide con el SKU que enviaste.")

except Exception as e:
    st.error(f"Error general: {e}")
