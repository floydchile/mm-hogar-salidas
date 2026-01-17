import streamlit as st
from supabase import create_client
import os, pandas as pd, requests, hashlib, hmac, urllib.parse
from datetime import datetime, timezone

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="MyM Sincro Multicanal", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
F_API_KEY = "bacfa61d25421da20c72872fcc24569266563eb1"
F_USER_ID = "ext_md.ali@falabella.cl"
F_BASE_URL = "https://sellercenter-api.falabella.com/"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FUNCIÓN FIRMA FALABELLA ---
def firmar_fala(params):
    ordenados = sorted(params.items(), key=lambda x: x[0])
    query_string = urllib.parse.urlencode(ordenados)
    signature = hmac.new(F_API_KEY.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return F_BASE_URL + "?" + query_string + "&Signature=" + signature

# --- FUNCIÓN ACTUALIZAR FALABELLA ---
def enviar_stock_fala(sku, qty):
    # XML sin f-strings ni llaves para evitar errores de Streamlit
    xml_data = '<?xml version="1.0" encoding="UTF-8"?><Offers><Offer><SellerSku>' + str(sku) + '</SellerSku><Quantity>' + str(int(qty)) + '</Quantity></Offer></Offers>'
    
    params = {
        "Action": "UpdateOffers",
        "Format": "JSON",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "UserID": F_USER_ID,
        "Version": "1.0"
    }
    
    try:
        url = firmar_fala(params)
        res = requests.post(url, data=xml_data, headers={'Content-Type': 'application/xml'})
        data = res.json()
        
        if "SuccessResponse" in data:
            return True, "OK"
        return False, str(data)
    except Exception as e:
        return False, str(e)

# --- INTERFAZ ---
st.title("📦 MyM Hogar - Sincronizador Global")

# Cargar datos
try:
    res_db = supabase.table("productos").select("*").order("sku").execute()
    prods = res_db.data
except Exception as e:
    st.error(f"Error Supabase: {e}")
    prods = []

if prods:
    # Selector
    lista_nombres = [p['sku'] + " - " + p['nombre'] for p in prods]
    seleccion = st.selectbox("Elegir producto:", lista_nombres)
    sku_elegido = seleccion.split(" - ")[0]
    
    # Obtener datos del producto elegido
    p_data = next(item for item in prods if item["sku"] == sku_elegido)
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**SKU Interno:** {p_data['sku']}")
        st.write(f"**SKU Falabella:** {p_data.get('sku_falabella', 'No definido')}")
        nuevo_stk = st.number_input("Nuevo Stock:", value=int(p_data['stock_total']))

    if st.button("🚀 SINCRONIZAR TODO"):
        # 1. Supabase
        supabase.table("productos").update({"stock_total": nuevo_stk}).eq("sku", sku_elegido).execute()
        st.success("✅ Supabase actualizado")

        # 2. Mercado Libre (Atajo pañal)
        if "XXXG42" in sku_elegido:
            h_meli = {'Authorization': 'Bearer ' + MELI_TOKEN}
            requests.put("https://api.mercadolibre.com/items/MLC2884836674", 
                        json={"available_quantity": int(nuevo_stk)}, headers=h_meli)
            st.success("✅ Mercado Libre actualizado")

        # 3. Falabella
        sku_f = p_data.get('sku_falabella')
        if sku_f and sku_f != "None":
            ok, info = enviar_stock_fala(sku_f, nuevo_stk)
            if ok:
                st.success("✅ Falabella: Información enviada con éxito")
            else:
                st.error(f"❌ Falabella error: {info}")
        else:
            st.info("ℹ️ Falabella: Saltado (Sin SKU vinculado)")

    st.divider()
    st.dataframe(pd.DataFrame(prods)[["sku", "sku_falabella", "nombre", "stock_total"]])
