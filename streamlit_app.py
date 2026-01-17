import streamlit as st
from supabase import create_client, Client
import os
import pandas as pd
from PIL import Image
import requests
import urllib.parse

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="M&M PRUEBAS - Sincro", page_icon="🧪", layout="wide")

# Estilos visuales
st.markdown("""<style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    .stMetric {background-color: #f0f2f6; border-radius: 10px; padding: 10px;}
</style>""", unsafe_allow_html=True)

# Variables de Entorno (Railway las toma de tu config)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
MELI_USER_ID = os.getenv("MELI_USER_ID")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
USUARIOS_VALIDOS = ["pau", "dany", "miguel"]

# --- LÓGICA DE BÚSQUEDA PROFUNDA ---
def encontrar_id_meli_exhaustivo(sku_objetivo):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    sku_buscado = str(sku_objetivo).strip()
    
    # 1. Intento rápido: Búsqueda por texto (query q)
    url_q = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?q={urllib.parse.quote(sku_buscado)}"
    ids = requests.get(url_q, headers=headers).json().get('results', [])

    # 2. Intento profundo: Si falló, revisamos las últimas 50 publicaciones (barrido manual)
    if not ids:
        url_rec = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?sort=date_desc&limit=50"
        ids = requests.get(url_rec, headers=headers).json().get('results', [])

    for item_id in ids:
        # Consultamos el detalle real de cada producto candidato
        det = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=headers).json()
        
        # Solo nos interesan los que están para vender
        if det.get('status') not in ['active', 'paused']: continue
        
        # Extraemos el SKU de los dos lugares posibles
        sku_en_campo_principal = str(det.get('seller_custom_field', '')).strip()
        sku_en_atributos = next((str(a.get('value_name', '')).strip() 
                                for a in det.get('attributes', []) 
                                if a.get('id') == 'SELLER_SKU'), "")
        
        # Si coincide en cualquiera de los dos, ¡LO TENEMOS!
        if sku_buscado in [sku_en_campo_principal, sku_en_atributos]:
            return item_id
    return None

def sincronizar_meli(sku, cantidad):
    item_id = encontrar_id_meli_exhaustivo(sku)
    if item_id:
        headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
        # IMPORTANTE: Aquí actualizamos stock Y corregimos el SKU para el futuro
        payload = {
            "available_quantity": int(cantidad),
            "seller_custom_field": sku  # Esto arregla el problema de raíz
        }
        res = requests.put(f"https://api.mercadolibre.com/items/{item_id}", json=payload, headers=headers)
        if res.status_code == 200:
            return f"✅ Sincronizado en {item_id}"
        return f"❌ Error API: {res.status_code}"
    return "❌ No se encontró el SKU en tus publicaciones activas."

# --- INTERFAZ DE USUARIO ---
if 'user' not in st.session_state: st.session_state.user = None

with st.sidebar:
    st.header("🔑 Acceso")
    if st.session_state.user:
        st.write(f"Conectado como: **{st.session_state.user.upper()}**")
        if st.button("Cerrar Sesión"):
            st.session_state.user = None
            st.rerun()
    else:
        u = st.text_input("Usuario:").lower().strip()
        if st.button("Entrar"):
            if u in USUARIOS_VALIDOS:
                st.session_state.user = u
                st.rerun()

if not st.session_state.user:
    st.warning("🔒 Ingresa tu usuario para continuar.")
    st.stop()

# --- CUERPO DE LA APP ---
st.title("🧪 Laboratorio de Sincronización MyM")
t1, t2 = st.tabs(["🚀 Probar Sincro", "📊 Ver Inventario"])

with t1:
    prods = supabase.table("productos").select("*").order("sku").execute().data
    if prods:
        with st.form("test_sync"):
            p = st.selectbox("Selecciona un producto para probar:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
            cant_test = st.number_input("Cantidad de prueba (stock real):", min_value=0, value=int(p['stock_total']))
            if st.form_submit_button("🔥 Ejecutar Búsqueda Profunda y Sincro"):
                with st.spinner("Buscando en Mercado Libre (esto puede tardar unos segundos)..."):
                    resultado = sincronizar_meli(p['sku'], cant_test)
                
                if "✅" in resultado:
                    st.success(resultado)
                    st.balloons()
                else:
                    st.error(resultado)

with t2:
    if prods:
        st.dataframe(pd.DataFrame(prods)[["sku", "nombre", "stock_total"]], use_container_width=True)
