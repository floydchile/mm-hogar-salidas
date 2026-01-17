import streamlit as st
from supabase import create_client
import os, pandas as pd, requests, hashlib, hmac, urllib.parse
from datetime import datetime, timezone

# --- CONFIGURACIÓN TOTAL ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
F_API_KEY = "bacfa61d25421da20c72872fcc24569266563eb1"
F_USER_ID = "ext_md.ali@falabella.cl"
F_BASE_URL = "https://sellercenter-api.falabella.com/"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- MOTOR FALABELLA ---
def firmar_falabella(params):
    ordenados = sorted(params.items(), key=lambda x: x[0])
    query_string = urllib.parse.urlencode(ordenados)
    signature = hmac.new(F_API_KEY.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{F_BASE_URL}?{query_string}&Signature={signature}"

def actualizar_stock_falabella(sku_fala, cantidad):
    payload_xml = f'<?xml version="1.0" encoding="UTF-8"?><Request><Product><SellerSku>{sku_fala}</SellerSku><Quantity>{int(cantidad)}</Quantity></Product></Request>'
    params = {
        "Action": "UpdatePriceQuantity",
        "Format": "JSON",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "UserID": F_USER_ID,
        "Version": "1.0"
    }
    url = firmar_falabella(params)
    try:
        res = requests.post(url, data=payload_xml, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        return res.status_code == 200
    except: return False

# --- MOTOR MERCADO LIBRE --- (Simplificado para el test)
def actualizar_stock_meli(sku_db, cantidad):
    # Aquí usamos tu función de búsqueda que ya probamos (ID MLC2884836674 para el pañal)
    item_id = "MLC2884836674" if "XXXG42" in sku_db else None
    if item_id:
        headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
        res = requests.put(f"https://api.mercadolibre.com/items/{item_id}", 
                           json={"available_quantity": int(cantidad)}, headers=headers)
        return res.status_code == 200
    return False

# --- INTERFAZ ---
st.title("🚀 MyM Hogar - Sincronizador Multichannel")

# Cargar productos con las nuevas columnas
prods = supabase.table("productos").select("*").order("sku").execute().data

if prods:
    p = st.selectbox("Selecciona producto para SINCRONIZACIÓN TOTAL:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
    
    st.write(f"**Mapeo actual:** MeLi ({p['sku']}) | Falabella ({p.get('sku_falabella', 'No vinculado')})")
    
    nuevo_stock = st.number_input("Nuevo Stock Global:", value=int(p['stock_total']))

    if st.button("🔥 EJECUTAR SINCRONIZACIÓN TRIPLE"):
        # 1. Actualizar Supabase
        supabase.table("productos").update({"stock_total": nuevo_stock}).eq("sku", p['sku']).execute()
        st.success("✅ Supabase actualizado.")

        # 2. Actualizar MeLi
        if actualizar_stock_meli(p['sku'], nuevo_stock):
            st.success("✅ Mercado Libre actualizado.")
        else: st.warning("⚠️ MeLi no actualizado (Verifica ID).")

        # 3. Actualizar Falabella
        if p.get('sku_falabella'):
            if actualizar_stock_falabella(p['sku_falabella'], nuevo_stock):
                st.success(f"✅ Falabella actualizado (SKU: {p['sku_falabella']}).")
            else: st.error("❌ Error en Falabella.")
        else:
            st.info("ℹ️ Falabella saltado (Sin SKU vinculado).")

    st.divider()
    st.dataframe(pd.DataFrame(prods)[["sku", "sku_falabella", "nombre", "stock_total"]])
