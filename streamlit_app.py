import streamlit as st
from supabase import create_client, Client
import os
import requests
import urllib.parse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="M&M Hogar - Sincro Corregida", layout="wide")

# MENSAJE PARA EL EQUIPO
st.warning("⚠️ **PAU - DANY ESTOY HACIENDO PRUEBAS, VUELVAN MAS RATO**")

# Conexión
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
MELI_USER_ID = os.getenv("MELI_USER_ID")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def actualizar_stock_meli_seguro(sku_buscado, nueva_cantidad):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    sku_clean = str(sku_buscado).strip()
    
    try:
        # BUSQUEDA FILTRADA: Solo productos activos o pausados para evitar el error de 'closed'
        # Buscamos primero por seller_custom_field
        url_search = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?seller_custom_field={urllib.parse.quote(sku_clean)}"
        res_search = requests.get(url_search, headers=headers).json()
        
        items_encontrados = res_search.get('results', [])
        
        if not items_encontrados:
            return f"❓ SKU {sku_clean} no existe en MeLi."

        # Buscamos cuál de los resultados está ACTIVO
        item_final = None
        for item_id in items_encontrados:
            det = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=headers).json()
            if det.get('status') in ['active', 'paused']:
                item_final = det
                break
        
        if not item_final:
            return f"❌ El SKU {sku_clean} solo existe en publicaciones CERRADAS."

        target_id = item_final['id']
        
        # Verificar si tiene variantes
        variantes = item_final.get('variations', [])
        if variantes:
            id_v = next((v['id'] for v in variantes if str(v.get('seller_custom_field')).strip() == sku_clean), None)
            if id_v:
                url_upd = f"https://api.mercadolibre.com/items/{target_id}/variations/{id_v}"
                r_upd = requests.put(url_upd, json={"available_quantity": int(nueva_cantidad)}, headers=headers)
            else:
                return f"❌ No se halló la variante {sku_clean} dentro de {target_id}."
        else:
            url_upd = f"https://api.mercadolibre.com/items/{target_id}"
            r_upd = requests.put(url_upd, json={"available_quantity": int(nueva_cantidad)}, headers=headers)

        if r_upd.status_code == 200:
            return f"✅ Sincronizado en {target_id} ({nueva_cantidad} uds)."
        else:
            return f"❌ Error MeLi: {r_upd.json().get('message')}"
            
    except Exception as e:
        return f"❌ Error de conexión: {str(e)}"

# --- INTERFAZ ---
st.title("🛒 Gestión MyM + MeLi (Sincronización)")

try:
    prods = supabase.table("productos").select("*").order("sku").execute().data
    if prods:
        p_sel = st.selectbox("Selecciona Producto:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
        
        if st.button("🚀 Registrar Venta y Sincronizar"):
            # 1. Descontar en Supabase (Simulando una venta de 1 para la prueba)
            res = supabase.rpc("registrar_salida", {
                "p_sku": p_sel['sku'], "p_cantidad": 1,
                "p_canal": "Prueba", "p_usuario": "Admin"
            }).execute()
            
            # 2. Obtener Stock Final
            stock_f = supabase.table("productos").select("stock_total").eq("sku", p_sel['sku']).single().execute().data['stock_total']
            
            # 3. Sincronizar
            with st.spinner("Buscando publicación activa..."):
                msg = actualizar_stock_meli_seguro(p_sel['sku'], stock_f)
            
            if "✅" in msg: st.success(msg)
            else: st.error(msg)
except Exception as e:
    st.error(f"Error: {e}")
