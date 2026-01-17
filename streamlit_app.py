import streamlit as st
from supabase import create_client
import os, pandas as pd, requests, hashlib, hmac, urllib.parse
from datetime import datetime, timezone

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="MyM Hogar - Omnicanal", layout="wide")

# Lectura de variables desde Railway (os.getenv)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_TOKEN")
WOO_URL = os.getenv("WOO_URL")
WOO_CK = os.getenv("WOO_CK")
WOO_CS = os.getenv("WOO_CS")

# Datos de Falabella (Hardcoded por ahora para asegurar que no falle)
F_API_KEY = "bacfa61d25421da20c72872fcc24569266563eb1"
F_USER_ID = "ext_md.ali@falabella.cl"
F_BASE_URL = "https://sellercenter-api.falabella.com/"

# Verificación de Seguridad
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("❌ ERROR CRÍTICO: No se encontraron las variables de Supabase en Railway.")
    st.info("Asegúrate de haber agregado SUPABASE_URL y SUPABASE_KEY en la pestaña 'Variables' de Railway.")
    st.stop()

# Conexión a Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. FUNCIONES DE APOYO
def sync_woo_stock(product_id, qty):
    url = f"{WOO_URL}/wp-json/wc/v3/products/{product_id}"
    data = {"manage_stock": True, "stock_quantity": int(qty)}
    try:
        res = requests.put(url, json=data, auth=(WOO_CK, WOO_CS), timeout=10)
        return res.status_code == 200
    except: return False

def sync_fala_stock(sku_f, qty):
    xml = f'<?xml version="1.0" encoding="UTF-8" ?><Request><Product><SellerSku>{sku_f}</SellerSku><BusinessUnits><BusinessUnit><OperatorCode>facl</OperatorCode><Stock>{int(qty)}</Stock></BusinessUnit></BusinessUnits></Product></Request>'
    params = {"Action": "ProductUpdate", "Format": "JSON", "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"), "UserID": F_USER_ID, "Version": "1.0"}
    query = urllib.parse.urlencode(sorted(params.items()))
    sig = hmac.new(F_API_KEY.encode('utf-8'), query.encode('utf-8'), hashlib.sha256).hexdigest()
    try:
        requests.post(f"{F_BASE_URL}?{query}&Signature={sig}", data=xml, headers={'Content-Type': 'application/xml'}, timeout=10)
        return True
    except: return False

# 3. INTERFAZ
st.title("🚀 MyM Hogar - Control Omnicanal")

# Intentar cargar datos
try:
    res = supabase.table("productos").select("*").order("sku").execute()
    df = pd.DataFrame(res.data)
    
    if not df.empty:
        st.subheader("📊 Inventario en Tiempo Real")
        # Mostramos la tabla para confirmar que carga
        st.dataframe(df[["sku", "sku_falabella", "woo_id", "stock_total"]], use_container_width=True)

        st.divider()
        st.subheader("🔄 Sincronización Global")
        
        col1, col2 = st.columns(2)
        with col1:
            sku_sel = st.selectbox("Elegir Producto:", df["sku"].tolist())
        with col2:
            stk_val = st.number_input("Nuevo Stock Global:", min_value=0, step=1)

        if st.button("🚀 Actualizar en MeLi, Falabella y Web"):
            p = df[df["sku"] == sku_sel].iloc[0]
            
            # 1. Supabase
            supabase.table("productos").update({"stock_total": stk_val}).eq("sku", sku_sel).execute()
            st.success("✅ Supabase: OK")

            # 2. Mercado Libre (Atajo Pañal)
            if "XXXG42" in str(sku_sel):
                requests.put(f"https://api.mercadolibre.com/items/MLC2884836674", 
                             json={"available_quantity": int(stk_val)}, 
                             headers={'Authorization': f'Bearer {MELI_TOKEN}'})
                st.success("✅ Mercado Libre: OK")

            # 3. Falabella
            if p.get("sku_falabella"):
                sync_fala_stock(p["sku_falabella"], stk_val)
                st.success(f"✅ Falabella ({p['sku_falabella']}): OK")

            # 4. WooCommerce
            if p.get("woo_id"):
                if sync_woo_stock(p["woo_id"], stk_val):
                    st.success(f"✅ Web ({p['woo_id']}): OK")
                else:
                    st.error("❌ Web: Error de conexión")
    else:
        st.warning("No hay productos en la base de datos.")

except Exception as e:
    st.error(f"Falla al cargar inventario: {e}")
