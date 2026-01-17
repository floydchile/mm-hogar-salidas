import streamlit as st
from supabase import create_client
import os, pandas as pd, requests, hashlib, hmac, urllib.parse, uuid, base64
from datetime import datetime, timezone

# 1. CONFIGURACIÓN E IDENTIDADES
st.set_page_config(page_title="MyM Hogar - Central Omnicanal PRO", layout="wide")

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

# Conexión Supabase
if not SUPABASE_URL:
    st.error("❌ Error: No se encuentran las variables de entorno.")
    st.stop()
    
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- MOTOR DE TOKENS MERCADO LIBRE ---
def obtener_tokens_meli_db():
    try:
        res = supabase.table("config_tokens").select("*").eq("id", "meli").execute()
        return res.data[0] if res.data else None
    except: return None

def renovar_tokens_meli():
    tokens = obtener_tokens_meli_db()
    if not tokens: return None
    url = "https://api.mercadolibre.com/oauth/token"
    payload = {
        'grant_type': 'refresh_token', 
        'client_id': MELI_CLIENT_ID, 
        'client_secret': MELI_CLIENT_SECRET, 
        'refresh_token': tokens['refresh_token']
    }
    res = requests.post(url, data=payload)
    if res.status_code == 200:
        data = res.json()
        supabase.table("config_tokens").update({
            "access_token": data['access_token'], 
            "refresh_token": data['refresh_token'], 
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", "meli").execute()
        return data['access_token']
    return None

# --- MOTOR WALMART CHILE (CONFIGURACIÓN FINAL) ---
def obtener_token_walmart():
    # Usamos la URL global que encontraste como puerta de entrada
    url = "https://marketplace.walmartapis.com/v3/token"
    
    # Formato requerido: Basic Base64(clientId:clientSecret)
    auth_str = f"{WAL_CLIENT_ID}:{WAL_CLIENT_SECRET}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "WM_SVC.NAME": "MyM_Hogar",
        "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    
    try:
        res = requests.post(url, data=data, headers=headers, timeout=15)
        if res.status_code == 200:
            return res.json().get("access_token")
        else:
            # Reintento por la ruta de Chile directa si la global falla
            url_cl = "https://v3.walmartchile.cl/api/v3/token"
            res_cl = requests.post(url_cl, data=data, headers=headers, timeout=15)
            if res_cl.status_code == 200:
                return res_cl.json().get("access_token")
            return None
    except:
        return None

def sync_walmart_stock(sku_w, qty):
    token = obtener_token_walmart()
    if not token: return False
    
    # URL de Inventario Global para Chile
    url = f"https://marketplace.walmartapis.com/v3/inventory?sku={sku_w}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "WM_SEC.ACCESS_TOKEN": token,
        "WM_MARKET": "cl",
        "WM_SVC.NAME": "MyM_Hogar",
        "WM_QOS.CORRELATION_ID": str(uuid.uuid4()),
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    
    payload = {
        "sku": sku_w,
        "quantity": {"unit": "EACH", "amount": int(qty)}
    }
    
    try:
        res = requests.put(url, json=payload, headers=headers, timeout=15)
        if res.status_code in [200, 201]:
            return True
        else:
            # Intento final con la URL de Chile
            url_cl = f"https://v3.walmartchile.cl/api/v3/inventory?sku={sku_w}"
            res_cl = requests.put(url_cl, json=payload, headers=headers, timeout=15)
            return res_cl.status_code in [200, 201]
    except:
        return False

# --- MOTORES DE SINCRONIZACIÓN ADICIONALES ---

def sync_meli_stock(qty):
    tokens = obtener_tokens_meli_db()
    if not tokens: return False
    url = "https://api.mercadolibre.com/items/MLC2884836674"
    headers = {'Authorization': f'Bearer {tokens["access_token"]}', 'Content-Type': 'application/json'}
    res = requests.put(url, json={"available_quantity": int(qty)}, headers=headers)
    if res.status_code == 401:
        nuevo = renovar_tokens_meli()
        if nuevo:
            headers['Authorization'] = f'Bearer {nuevo}'
            res = requests.put(url, json={"available_quantity": int(qty)}, headers=headers)
    return res.status_code in [200, 201]

def sync_woo_stock(p_id, qty):
    try:
        res = requests.put(f"{WOO_URL}/wp-json/wc/v3/products/{p_id}", json={"stock_quantity": int(qty)}, auth=(WOO_CK, WOO_CS), timeout=10)
        return res.status_code == 200
    except: return False

def sync_fala_stock(sku_f, qty):
    xml = f'<?xml version="1.0" encoding="UTF-8" ?><Request><Product><SellerSku>{sku_f}</SellerSku><BusinessUnits><BusinessUnit><OperatorCode>facl</OperatorCode><Stock>{int(qty)}</Stock></BusinessUnit></BusinessUnits></Product></Request>'
    params = {"Action": "ProductUpdate", "Format": "JSON", "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"), "UserID": F_USER_ID, "Version": "1.0"}
    query = urllib.parse.urlencode(sorted(params.items()))
    sig = hmac.new(F_API_KEY.encode('utf-8'), query.encode('utf-8'), hashlib.sha256).hexdigest()
    try:
        res = requests.post(f"{F_BASE_URL}?{query}&Signature={sig}", data=xml, headers={'Content-Type': 'application/xml'}, timeout=10)
        return res.status_code == 200
    except: return False

# --- INTERFAZ STREAMLIT ---
st.title("🚀 MyM Hogar - Central Omnicanal")

try:
    res_db = supabase.table("productos").select("*").order("sku").execute()
    df = pd.DataFrame(res_db.data)

    if not df.empty:
        st.subheader("📊 Inventario Maestro")
        st.dataframe(df[["sku", "sku_falabella", "sku_walmart", "woo_id", "stock_total"]], use_container_width=True)
        st.divider()

        st.subheader("🔄 Sincronización Manual")
        c1, c2 = st.columns(2)
        with c1:
            sku_sel = st.selectbox("Producto:", df["sku"].tolist())
        with c2:
            stk_val = st.number_input("Nuevo Stock Global:", min_value=0, step=1)

        if st.button("🚀 Actualizar en TODOS los Canales"):
            p = df[df["sku"] == sku_sel].iloc[0]
            
            # 1. Base de Datos
            supabase.table("productos").update({"stock_total": stk_val}).eq("sku", sku_sel).execute()
            st.success("✅ Supabase: Actualizado")

            # 2. Mercado Libre
            if "XXXG42" in str(sku_sel):
                if sync_meli_stock(stk_val): st.success("✅ MeLi: Sincronizado")
                else: st.error("❌ MeLi: Error")

            # 3. Walmart
            if p.get("sku_walmart"):
                if sync_walmart_stock(p["sku_walmart"], stk_val): st.success(f"✅ Walmart ({p['sku_walmart']}): Sincronizado")
                else: st.error("❌ Walmart: Error")

            # 4. Falabella
            if p.get("sku_falabella"):
                if sync_fala_stock(p["sku_falabella"], stk_val): st.success(f"✅ Falabella: Sincronizado")

            # 5. Web (Woo)
            if p.get("woo_id"):
                if sync_woo_stock(p["woo_id"], stk_val): st.success(f"✅ Web: Sincronizado")
    else:
        st.warning("Carga productos en la tabla 'productos' de Supabase.")
except Exception as e:
    st.error(f"Error de conexión: {e}")
