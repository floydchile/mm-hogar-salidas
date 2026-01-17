import streamlit as st
from supabase import create_client
import os, pandas as pd, requests, hashlib, hmac, urllib.parse
from datetime import datetime, timezone

# 1. CONFIGURACIÓN E IMPORTS (Esto siempre arriba)
st.set_page_config(page_title="MyM Multichannel", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
F_API_KEY = "bacfa61d25421da20c72872fcc24569266563eb1"
F_USER_ID = "ext_md.ali@falabella.cl"
F_BASE_URL = "https://sellercenter-api.falabella.com/"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. FUNCIONES DE AYUDA (Lógica de firma y envíos)
def firmar_fala(params):
    ordenados = sorted(params.items(), key=lambda x: x[0])
    query_string = urllib.parse.urlencode(ordenados)
    signature = hmac.new(F_API_KEY.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{F_BASE_URL}?{query_string}&Signature={signature}"

def sync_falabella_stock(sku_f, qty):
    xml = f'<?xml version="1.0" encoding="UTF-8" ?><Request><Product><SellerSku>{sku_f}</SellerSku><BusinessUnits><BusinessUnit><OperatorCode>facl</OperatorCode><Stock>{int(qty)}</Stock></BusinessUnit></BusinessUnits></Product></Request>'
    params = {
        "Action": "ProductUpdate",
        "Format": "JSON",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "UserID": F_USER_ID,
        "Version": "1.0"
    }
    try:
        url = firmar_fala(params)
        res = requests.post(url, data=xml, headers={'Content-Type': 'application/xml'})
        return res.json()
    except: return {"error": "Fallo de red"}

def revisar_pedidos_falabella():
    params = {
        "Action": "GetOrders",
        "Format": "JSON",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "UserID": F_USER_ID,
        "Version": "1.0",
        "CreatedAfter": "2026-01-01T00:00:00"
    }
    try:
        url = firmar_fala(params)
        res = requests.get(url)
        return res.json()
    except: return None

# 3. INTERFAZ DE USUARIO (Streamlit)
st.title("📦 MyM Hogar - Centro de Control")

# Sección de Sincronización Manual (Lo que ya funcionaba)
st.subheader("🔄 Sincronización de Stock")
res_db = supabase.table("productos").select("*").execute()
df = pd.DataFrame(res_db.data)

if not df.empty:
    sku_sel = st.selectbox("Seleccionar Producto:", df["sku"].tolist())
    stk_val = st.number_input("Nuevo Stock Global:", min_value=0, step=1)
    
    if st.button("🚀 Sincronizar en MeLi y Falabella"):
        p = df[df["sku"] == sku_sel].iloc[0]
        # Supabase
        supabase.table("productos").update({"stock_total": stk_val}).eq("sku", sku_sel).execute()
        st.success("✅ Supabase: OK")
        # MeLi
        if "XXXG42" in sku_sel:
            requests.put("https://api.mercadolibre.com/items/MLC2884836674", 
                        json={"available_quantity": int(stk_val)}, 
                        headers={'Authorization': f'Bearer {MELI_TOKEN}'})
            st.success("✅ MeLi: OK")
        # Falabella
        if p["sku_falabella"]:
            res_f = sync_falabella_stock(p["sku_falabella"], stk_val)
            st.success(f"✅ Falabella: Enviado ({p['sku_falabella']})")

st.divider()

# Sección de Ventas (Lo nuevo)
st.subheader("🕵️ Detector de Ventas - Falabella")
if st.button("🔍 Ver Ventas Recientes"):
    with st.spinner("Buscando pedidos..."):
        ventas = revisar_pedidos_falabella()
        if ventas and "SuccessResponse" in ventas:
            ordenes = ventas["SuccessResponse"]["Body"].get("Orders", [])
            if ordenes:
                st.write(f"Se encontraron **{len(ordenes)}** pedidos.")
                st.json(ordenes)
            else:
                st.info("No hay pedidos nuevos.")
        else:
            st.error(f"Error al conectar con Falabella: {ventas}")
