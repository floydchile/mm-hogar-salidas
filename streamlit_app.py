import streamlit as st
from supabase import create_client
import os, pandas as pd, requests, hashlib, hmac, urllib.parse, uuid
from datetime import datetime, timezone

# 1. CONFIGURACIÓN E IDENTIDADES
st.set_page_config(page_title="MyM Hogar - Omnicanal PRO", layout="wide")

# Variables desde Railway
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_CLIENT_ID = os.getenv("MELI_APP_ID")
MELI_CLIENT_SECRET = os.getenv("MELI_CLIENT_SECRET")
WAL_CLIENT_ID = os.getenv("WAL_CLIENT_ID")
WAL_CLIENT_SECRET = os.getenv("WAL_CLIENT_SECRET")
WOO_URL = os.getenv("WOO_URL")
WOO_CK = os.getenv("WOO_CK")
WOO_CS = os.getenv("WOO_CS")

# Datos Falabella (Fijos)
F_API_KEY = "bacfa61d25421da20c72872fcc24569266563eb1"
F_USER_ID = "ext_md.ali@falabella.cl"
F_BASE_URL = "https://sellercenter-api.falabella.com/"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- MOTOR DE TOKENS MERCADO LIBRE ---
def obtener_tokens_meli_db():
    res = supabase.table("config_tokens").select("*").eq("id", "meli").execute()
    return res.data[0] if res.data else None

def renovar_tokens_meli():
    tokens = obtener_tokens_meli_db()
    if not tokens: return None
    url = "https://api.mercadolibre.com/oauth/token"
    payload = {'grant_type': 'refresh_token', 'client_id': MELI_CLIENT_ID, 'client_secret': MELI_CLIENT_SECRET, 'refresh_token': tokens['refresh_token']}
    res = requests.post(url, data=payload)
    if res.status_code == 200:
        data = res.json()
        supabase.table("config_tokens").update({"access_token": data['access_token'], "refresh_token": data['refresh_token'], "updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", "meli").execute()
        return data['access_token']
    return None

# --- MOTOR WALMART (TOKEN TEMPORAL) ---
def obtener_token_walmart():
    # URL oficial según la documentación de Walmart Chile Marketplace
    url = "https://v3.walmartchile.cl/api/v3/token"
    
    headers = {
        "WM_SVC.NAME": "Walmart Marketplace",
        "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    
    try:
        # Importante: Walmart Chile espera Auth Basic con Client ID y Secret
        res = requests.post(url, data=data, auth=(WAL_CLIENT_ID, WAL_CLIENT_SECRET), headers=headers, timeout=15)
        if res.status_code == 200:
            return res.json().get("access_token")
        else:
            st.error(f"❌ Error Auth Walmart: {res.status_code} - {res.text}")
            return None
    except Exception as e:
        # Si v3 falla, intentamos la ruta directa de Mirakl como respaldo
        try:
            url_alt = "https://walmartchile-prod.mirakl.net/api/v3/token"
            res = requests.post(url_alt, data=data, auth=(WAL_CLIENT_ID, WAL_CLIENT_SECRET), headers=headers, timeout=15)
            if res.status_code == 200:
                return res.json().get("access_token")
        except: pass
        st.error(f"❌ Error de conexión Walmart: {e}")
        return None

def sync_walmart_stock(sku_w, qty):
    token = obtener_token_walmart()
    if not token: return False
    
    # Endpoint oficial de Inventario para Chile
    url = "https://v3.walmartchile.cl/api/v3/inventory"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "WM_SEC.ACCESS_TOKEN": token,
        "WM_SVC.NAME": "Walmart Marketplace",
        "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    # Estructura del JSON según Walmart Chile Inventory API
    payload = {
        "sku": sku_w,
        "quantity": {
            "unit": "EACH",
            "amount": int(qty)
        }
    }
    
    try:
        # Nota: La doc de Walmart dice que se usa PUT para actualizar
        res = requests.put(url, json=payload, headers=headers, timeout=15)
        if res.status_code in [200, 201]:
            return True
        else:
            st.error(f"❌ Walmart Stock Error: {res.status_code} - {res.text}")
            return False
    except Exception as e:
        st.error(f"❌ Excepción Walmart: {e}")
        return False

# --- INTERFAZ ---
st.title("🚀 MyM Hogar - Central Omnicanal")

try:
    res = supabase.table("productos").select("*").order("sku").execute()
    df = pd.DataFrame(res.data)

    if not df.empty:
        st.subheader("📊 Inventario Maestro")
        st.dataframe(df[["sku", "sku_falabella", "sku_walmart", "woo_id", "stock_total"]], use_container_width=True)

        st.divider()
        st.subheader("🔄 Sincronización Manual")
        c1, c2 = st.columns(2)
        with c1:
            sku_sel = st.selectbox("Producto:", df["sku"].tolist())
        with c2:
            stk_val = st.number_input("Nuevo Stock:", min_value=0, step=1)

        if st.button("🚀 Actualizar en TODOS los Canales"):
            p = df[df["sku"] == sku_sel].iloc[0]
            
            # 1. Supabase
            supabase.table("productos").update({"stock_total": stk_val}).eq("sku", sku_sel).execute()
            st.success("✅ Supabase")

            # 2. Mercado Libre
            if "XXXG42" in str(sku_sel):
                if sync_meli_stock(stk_val): st.success("✅ MeLi")
                else: st.error("❌ MeLi")

            # 3. Walmart
            if p.get("sku_walmart"):
                if sync_walmart_stock(p["sku_walmart"], stk_val): st.success(f"✅ Walmart ({p['sku_walmart']})")
                else: st.error("❌ Walmart")

            # 4. Falabella
            if p.get("sku_falabella"):
                if sync_fala_stock(p["sku_falabella"], stk_val): st.success("✅ Falabella")

            # 5. Web
            if p.get("woo_id"):
                if sync_woo_stock(p["woo_id"], stk_val): st.success("✅ Web")
    else:
        st.warning("Carga productos en Supabase primero.")
except Exception as e:
    st.error(f"Error: {e}")




