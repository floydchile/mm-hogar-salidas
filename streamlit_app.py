import streamlit as st
from supabase import create_client
import os, pandas as pd, requests, hashlib, hmac, urllib.parse
from datetime import datetime, timezone

# 1. CONFIGURACIÓN E IDENTIFICACIÓN
st.set_page_config(page_title="MyM Hogar - Omnicanal", layout="wide")

# Credenciales (Si no usas Secrets, cámbialos aquí directamente)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")

# WooCommerce Config
WOO_URL = "https://mymhogar.com/" # <--- CAMBIA ESTO
WOO_CK = "ck_1aefecde4415b41abdb3ebed3ee7e1e8e34bc008"         # <--- CAMBIA ESTO
WOO_CS = "cs_f5b973b59a7fd8dfb27cf4c64e5478ddcf33eaec"         # <--- CAMBIA ESTO

# Falabella Config
F_API_KEY = "bacfa61d25421da20c72872fcc24569266563eb1"
F_USER_ID = "ext_md.ali@falabella.cl"
F_BASE_URL = "https://sellercenter-api.falabella.com/"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. FUNCIONES DE ACTUALIZACIÓN (EL MOTOR)

def sync_woo_stock(product_id, qty):
    """Actualiza el stock en WooCommerce vía REST API"""
    url = f"{WOO_URL}/wp-json/wc/v3/products/{product_id}"
    data = {"manage_stock": True, "stock_quantity": int(qty)}
    try:
        res = requests.put(url, json=data, auth=(WOO_CK, WOO_CS))
        return res.status_code == 200
    except: return False

def sync_falabella_stock(sku_f, qty):
    piezas = [
        '<?xml version="1.0" encoding="UTF-8" ?>',
        '<Request><Product><SellerSku>', str(sku_f), '</SellerSku>',
        '<BusinessUnits><BusinessUnit><OperatorCode>facl</OperatorCode>',
        '<Stock>', str(int(qty)), '</Stock></BusinessUnit></BusinessUnits>',
        '</Product></Request>'
    ]
    xml_data = "".join(piezas)
    params = {"Action": "ProductUpdate", "Format": "JSON", "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"), "UserID": F_USER_ID, "Version": "1.0"}
    query = urllib.parse.urlencode(sorted(params.items()))
    sig = hmac.new(F_API_KEY.encode('utf-8'), query.encode('utf-8'), hashlib.sha256).hexdigest()
    try:
        requests.post(f"{F_BASE_URL}?{query}&Signature={sig}", data=xml_data, headers={'Content-Type': 'application/xml'})
        return True
    except: return False

# 3. INTERFAZ Y LÓGICA
st.title("🚀 MyM Hogar - Control Omnicanal")

res_db = supabase.table("productos").select("*").execute()
df = pd.DataFrame(res_db.data)

if not df.empty:
    st.subheader("🔄 Sincronización Global (Manual)")
    c1, c2 = st.columns(2)
    with c1:
        sku_sel = st.selectbox("Producto a actualizar:", df["sku"].tolist())
    with c2:
        stk_val = st.number_input("Nuevo Stock Global:", min_value=0, step=1)

    if st.button("Sincronizar en TODOS los canales"):
        p = df[df["sku"] == sku_sel].iloc[0]
        
        # A. Supabase
        supabase.table("productos").update({"stock_total": stk_val}).eq("sku", sku_sel).execute()
        st.write("✅ Supabase actualizado.")

        # B. Mercado Libre (Pañal)
        if "XXXG42" in sku_sel:
            requests.put("https://api.mercadolibre.com/items/MLC2884836674", 
                        json={"available_quantity": int(stk_val)}, 
                        headers={'Authorization': f'Bearer {MELI_TOKEN}'})
            st.write("✅ Mercado Libre actualizado.")

        # C. Falabella
        if p.get("sku_falabella"):
            sync_falabella_stock(p["sku_falabella"], stk_val)
            st.write(f"✅ Falabella ({p['sku_falabella']}) actualizado.")

        # D. WooCommerce (NUEVO)
        if p.get("woo_id"):
            exito_woo = sync_woo_stock(p["woo_id"], stk_val)
            if exito_woo:
                st.write(f"✅ WooCommerce (ID: {p['woo_id']}) actualizado.")
            else:
                st.error("❌ Error al actualizar WooCommerce.")

        st.success("¡Sincronización terminada!")

# Sección de ventas (la que ya tenías)
st.divider()
st.subheader("🕵️ Detector de Ventas Falabella")
# ... (aquí sigue el código del botón de ventas que ya teníamos)

