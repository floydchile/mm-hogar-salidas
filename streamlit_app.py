import streamlit as st
from supabase import create_client
import os, pandas as pd, requests, hashlib, hmac, urllib.parse
from datetime import datetime, timezone

# 1. Configuración mínima
st.set_page_config(page_title="MyM Rescate")
st.title("📦 Centro de Control MyM")

# 2. Conexión simple
try:
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    prods = supabase.table("productos").select("*").execute().data
    st.success("Conectado a la base de datos")
except Exception as e:
    st.error(f"Error de conexión: {e}")
    prods = []

# 3. Interfaz ultra-limpia
if prods:
    df = pd.DataFrame(prods)
    st.dataframe(df[["sku", "nombre", "stock_total"]])
    
    with st.form("update_form"):
        st.write("### Actualizar Stock")
        sku_input = st.selectbox("Producto", df["sku"].tolist())
        nuevo_stock = st.number_input("Cantidad", value=0)
        enviar = st.form_submit_state = st.form_submit_button("Sincronizar")
        
        if enviar:
            st.info(f"Intentando actualizar {sku_input} a {nuevo_stock}...")
            # Aquí agregaremos Falabella una vez que veas que esto funciona
