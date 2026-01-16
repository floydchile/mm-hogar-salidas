import streamlit as st
from supabase import create_client, Client
import os
import requests
import urllib.parse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="M&M Hogar - Ajuste Fino", layout="wide")

# MENSAJE PARA EL EQUIPO (HEADER)
st.warning("⚠️ **PAU - DANY ESTOY HACIENDO PRUEBAS, VUELVAN MAS RATO**")

# Conexión
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
MELI_USER_ID = os.getenv("MELI_USER_ID")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def buscar_todas_las_publicaciones(sku_buscado):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    sku_clean = str(sku_buscado).strip()
    
    # Buscamos todas las publicaciones que tengan este SKU
    url = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?seller_custom_field={urllib.parse.quote(sku_clean)}"
    r = requests.get(url, headers=headers).json()
    ids = r.get('results', [])
    
    detalles = []
    for item_id in ids:
        item = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=headers).json()
        detalles.append({
            "id": item_id,
            "titulo": item.get('title'),
            "status": item.get('status'),
            "permalink": item.get('permalink')
        })
    return detalles

st.title("🔍 Investigador de Publicaciones MeLi")

try:
    prods = supabase.table("productos").select("*").order("sku").execute().data
    if prods:
        p_sel = st.selectbox("Selecciona el producto para revisar:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
        
        if st.button("🔎 ¿A qué publicaciones apunta este SKU en MeLi?"):
            with st.spinner("Consultando a Mercado Libre..."):
                resultados = buscar_todas_las_publicaciones(p_sel['sku'])
            
            if resultados:
                st.write(f"### Se encontraron {len(resultados)} publicaciones para el SKU: `{p_sel['sku']}`")
                for res in resultados:
                    with st.expander(f"Publicación: {res['id']} ({res['status']})"):
                        st.write(f"**Título:** {res['titulo']}")
                        st.write(f"**Link:** [Ver en MeLi]({res['permalink']})")
                        st.write(f"**Estado:** {res['status']}")
                        if res['id'] == "MLC2884836674":
                            st.success("⭐ ESTA ES LA CORRECTA QUE MENCIONASTE")
                        elif res['id'] == "MLC522473073":
                            st.error("🚫 ESTA ES LA QUE SE SINCRONIZÓ POR ERROR")
            else:
                st.error("No se encontró ninguna publicación con ese SKU.")

except Exception as e:
    st.error(f"Error: {e}")
