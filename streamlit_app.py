import streamlit as st
from supabase import create_client, Client
import os
import requests
import urllib.parse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="M&M Hogar - Sistema Sincronizado", layout="wide")

# MENSAJE PARA EL EQUIPO
st.warning("⚠️ **PAU - DANY ESTOY HACIENDO PRUEBAS, VUELVAN MAS RATO**")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
MELI_USER_ID = os.getenv("MELI_USER_ID")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def buscar_y_actualizar_meli(sku_objetivo, nueva_cantidad):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    sku_clean = str(sku_objetivo).strip()
    
    try:
        # 1. Búsqueda amplia (Query general)
        url_search = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?q={urllib.parse.quote(sku_clean)}"
        res_search = requests.get(url_search, headers=headers).json()
        ids_encontrados = res_search.get('results', [])
        
        if not ids_encontrados:
            return f"❓ No se encontró ningún producto con el texto '{sku_clean}' en MeLi."

        item_final_id = None
        
        # 2. Buscamos el ID que realmente tenga ese SKU en sus atributos
        for item_id in ids_encontrados:
            det = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=headers).json()
            
            # Solo nos interesan los activos o pausados
            if det.get('status') not in ['active', 'paused']:
                continue
                
            # Revisamos el campo principal Y los atributos
            sku_principal = str(det.get('seller_custom_field', '')).strip()
            sku_en_atributos = next((str(a.get('value_name', '')).strip() for a in det.get('attributes', []) if a.get('id') == 'SELLER_SKU'), "")
            
            if sku_clean == sku_principal or sku_clean == sku_en_atributos:
                item_final_id = item_id
                break
        
        if not item_final_id:
            return f"❌ Se encontraron publicaciones pero ninguna tiene el SKU '{sku_clean}' activo."

        # 3. Actualizar Stock y "Reparar" el campo seller_custom_field para el futuro
        url_upd = f"https://api.mercadolibre.com/items/{item_final_id}"
        payload = {
            "available_quantity": int(nueva_cantidad),
            "seller_custom_field": sku_clean  # Esto lo "arregla" en MeLi para siempre
        }
        r_upd = requests.put(url_upd, json=payload, headers=headers)

        if r_upd.status_code == 200:
            return f"✅ Sincronizado con éxito en {item_final_id} ({nueva_cantidad} uds)."
        else:
            return f"❌ Error al actualizar: {r_upd.json().get('message')}"

    except Exception as e:
        return f"❌ Error técnico: {str(e)}"

# --- INTERFAZ PRINCIPAL ---
st.title("📦 Gestión de Inventario MyM")

# Pestañas para organizar
tab1, tab2 = st.tabs(["🚀 Registrar Venta", "📊 Ver Inventario"])

with tab1:
    try:
        prods = supabase.table("productos").select("*").order("sku").execute().data
        if prods:
            col_a, col_b = st.columns(2)
            with col_a:
                p_sel = st.selectbox("Producto:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
                cant = st.number_input("Cantidad vendida:", min_value=1, value=1)
            
            if st.button("🏁 Finalizar y Sincronizar con Mercado Libre", type="primary"):
                # 1. Descontar en Supabase
                supabase.rpc("registrar_salida", {
                    "p_sku": p_sel['sku'], "p_cantidad": cant,
                    "p_canal": "Venta Web/Local", "p_usuario": "Admin"
                }).execute()
                
                # 2. Obtener Stock Resultante
                stock_actual = supabase.table("productos").select("stock_total").eq("sku", p_sel['sku']).single().execute().data['stock_total']
                
                # 3. Sincronizar con MeLi
                with st.spinner(f"Sincronizando {p_sel['sku']}..."):
                    resultado = buscar_y_actualizar_meli(p_sel['sku'], stock_actual)
                
                if "✅" in resultado:
                    st.success(resultado)
                else:
                    st.error(resultado)
    except Exception as e:
        st.error(f"Error de base de datos: {e}")

with tab2:
    if prods:
        df = pd.DataFrame(prods)[["sku", "nombre", "stock_total"]]
        st.dataframe(df, use_container_width=True)
