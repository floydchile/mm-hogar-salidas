import streamlit as st
from supabase import create_client, Client
import os
import pandas as pd
import requests

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="M&M PRUEBAS - Multi-Tarea", layout="wide")
MELI_USER_ID = "462191513"
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- MOTOR DE BÚSQUEDA ---
def buscar_id(sku):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    sku = str(sku).strip()
    if sku == "EBSP XXXG42": return "MLC2884836674"
    if sku == "COLUN_ENTERA": return "MLC1591426227"
    
    # Si es otro SKU, hace el barrido que ya conocemos
    for offset in [0, 50]:
        url = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?status=active&offset={offset}&limit=50"
        res = requests.get(url, headers=headers).json()
        for item_id in res.get('results', []):
            det = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=headers).json()
            s_f = next((str(a.get('value_name')).strip() for a in det.get('attributes', []) if a.get('id') == 'SELLER_SKU'), "")
            s_p = str(det.get('seller_custom_field', '')).strip()
            if sku in [s_f, s_p]: return item_id
    return None

# --- ACCIONES ---
def enviar_a_meli(sku, cant):
    m_id = buscar_id(sku)
    if m_id:
        r = requests.put(f"https://api.mercadolibre.com/items/{m_id}", 
                         json={"available_quantity": int(cant), "seller_custom_field": sku}, 
                         headers={'Authorization': f'Bearer {MELI_TOKEN}'})
        return r.status_code == 200
    return False

def traer_de_meli(sku):
    m_id = buscar_id(sku)
    if m_id:
        det = requests.get(f"https://api.mercadolibre.com/items/{m_id}", headers={'Authorization': f'Bearer {MELI_TOKEN}'}).json()
        stock = det.get('available_quantity')
        supabase.table("productos").update({"stock_total": stock}).eq("sku", sku).execute()
        return stock
    return None

# --- INTERFAZ ---
st.title("🧪 Laboratorio MyM: Pruebas Simultáneas")

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("⬆️ PRUEBA 1: Enviar a MeLi")
    p_enviar = st.text_input("SKU para subir:", value="EBSP XXXG42")
    c_enviar = st.number_input("Nuevo stock en Supabase:", value=50)
    if st.button("🚀 Subir a MeLi"):
        # Primero actualizamos Supabase
        supabase.table("productos").update({"stock_total": c_enviar}).eq("sku", p_enviar).execute()
        if enviar_a_meli(p_enviar, c_enviar):
            st.success(f"Stock de {p_enviar} subido a MeLi: {c_enviar}")
        else: st.error("Fallo al subir.")

with col_b:
    st.subheader("📥 PRUEBA 2: Traer de MeLi")
    p_traer = st.text_input("SKU para bajar:", value="COLUN_ENTERA")
    st.info("Asegúrate de haber cambiado el stock en la web de MeLi antes.")
    if st.button("🔄 Espejo desde MeLi"):
        nuevo_stk = traer_de_meli(p_traer)
        if nuevo_stk is not None:
            st.success(f"Stock de {p_traer} actualizado en Supabase: {nuevo_stk}")
        else: st.error("No se encontró el producto.")

st.divider()
st.subheader("📊 Vista Rápida Supabase")
data = supabase.table("productos").select("sku, nombre, stock_total").in_("sku", ["EBSP XXXG42", "COLUN_ENTERA"]).execute().data
st.table(data)
