import streamlit as st
from supabase import create_client, Client
import os
import pandas as pd
import requests
import urllib.parse

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="M&M Hogar - MODO PRUEBA", layout="wide")

# --- MENSAJE PARA EL EQUIPO (HEADER) ---
st.warning("⚠️ **PAU - DANY ESTOY HACIENDO PRUEBAS, VUELVAN MAS RATO**")

# Conexión
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
MELI_USER_ID = os.getenv("MELI_USER_ID")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def investigar_item_meli(item_id):
    """Obtiene los detalles reales de una publicación para ver su SKU interno"""
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    try:
        res = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=headers).json()
        # Buscamos el SKU en el campo correcto de MeLi
        sku_real = res.get('seller_custom_field', 'SIN SKU')
        return f"ID: {item_id} | SKU detectado en MeLi: {sku_real}"
    except:
        return f"ID: {item_id} | No se pudo obtener detalle"

st.title("📦 Diagnóstico de Sincronización")

try:
    prods = supabase.table("productos").select("*").order("sku").execute().data
    if prods:
        p_sel = st.selectbox("Selecciona el producto que falló:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
        
        if st.button("🔍 Rastrear en Mercado Libre"):
            headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
            sku_target = p_sel['sku'].strip()
            
            st.info(f"Buscando SKU: `{sku_target}`...")
            
            # 1. Intentar búsqueda directa
            url = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?seller_custom_field={urllib.parse.quote(sku_target)}"
            r = requests.get(url, headers=headers).json()
            
            # 2. Mostrar resultados encontrados
            results = r.get('results', [])
            if results:
                st.success(f"¡Encontrado! MeLi dice que este SKU pertenece a la publicación: `{results[0]}`")
                # Aquí es donde actualizaremos el stock en el siguiente paso
            else:
                st.error("❌ Mercado Libre no reconoce ese SKU con una búsqueda directa.")
                
                # 3. MODO INVESTIGACIÓN: Ver qué publicaciones tienes activas realmente
                st.write("---")
                st.write("### 🕵️ Analizando tus últimas publicaciones:")
                url_recientes = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?limit=10"
                r_recientes = requests.get(url_recientes, headers=headers).json()
                
                items_recientes = r_recientes.get('results', [])
                for idx, item_id in enumerate(items_recientes):
                    detalle = investigar_item_meli(item_id)
                    st.write(f"{idx+1}. {detalle}")
                
                st.info("Compara el 'SKU detectado' arriba con el de tu base de datos. Si hay una diferencia (aunque sea un espacio), la sincronización fallará.")

except Exception as e:
    st.error(f"Error de conexión: {e}")
