import streamlit as st
from supabase import create_client
import os, pandas as pd, requests, hashlib, hmac, urllib.parse
from datetime import datetime, timezone

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="MyM Hogar - Omnicanal", layout="wide")

# Carga de variables desde Railway
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_CLIENT_ID = os.getenv("MELI_CLIENT_ID")
MELI_CLIENT_SECRET = os.getenv("MELI_CLIENT_SECRET")
WOO_URL = os.getenv("WOO_URL")
WOO_CK = os.getenv("WOO_CK")
WOO_CS = os.getenv("WOO_CS")

# Datos Falabella (Fijos)
F_API_KEY = "bacfa61d25421da20c72872fcc24569266563eb1"
F_USER_ID = "ext_md.ali@falabella.cl"
F_BASE_URL = "https://sellercenter-api.falabella.com/"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- MOTOR DE TOKENS MERCADO LIBRE ---

def obtener_tokens_db():
    res = supabase.table("config_tokens").select("*").eq("id", "meli").execute()
    return res.data[0] if res.data else None

def renovar_tokens_meli():
    tokens = obtener_tokens_db()
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

# --- MOTORES DE SINCRONIZACIÓN (SALIDA) ---

def sync_meli_stock(qty):
    tokens = obtener_tokens_db()
    if not tokens: return False
    url = "https://api.mercadolibre.com/items/MLC2884836674" # ID Fijo del pañal
    headers = {'Authorization': f'Bearer {tokens["access_token"]}', 'Content-Type': 'application/json'}
    res = requests.put(url, json={"available_quantity": int(qty)}, headers=headers)
    if res.status_code == 401:
        nuevo_token = renovar_tokens_meli()
        if nuevo_token:
            headers['Authorization'] = f'Bearer {nuevo_token}'
            res = requests.put(url, json={"available_quantity": int(qty)}, headers=headers)
    return res.status_code in [200, 201]

def sync_woo_stock(product_id, qty):
    url = f"{WOO_URL}/wp-json/wc/v3/products/{product_id}"
    try:
        res = requests.put(url, json={"manage_stock": True, "stock_quantity": int(qty)}, auth=(WOO_CK, WOO_CS), timeout=10)
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

# --- MOTORES DE BÚSQUEDA (ENTRADA) ---

def obtener_pedidos_fala():
    params = {"Action": "GetOrders", "Format": "JSON", "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"), "UserID": F_USER_ID, "Version": "1.0", "CreatedAfter": "2026-01-10T00:00:00"}
    query = urllib.parse.urlencode(sorted(params.items()))
    sig = hmac.new(F_API_KEY.encode('utf-8'), query.encode('utf-8'), hashlib.sha256).hexdigest()
    try:
        res = requests.get(f"{F_BASE_URL}?{query}&Signature={sig}", timeout=10)
        return res.json()
    except: return None

def obtener_pedidos_woo():
    url = f"{WOO_URL}/wp-json/wc/v3/orders?status=processing"
    try:
        res = requests.get(url, auth=(WOO_CK, WOO_CS), timeout=10)
        return res.json() if res.status_code == 200 else []
    except: return []

# --- LÓGICA DE PROCESAMIENTO ---

def procesar_ventas():
    conteo = 0
    # 1. Falabella
    f_data = obtener_pedidos_fala()
    if f_data and "SuccessResponse" in f_data:
        ordenes = f_data["SuccessResponse"]["Body"].get("Orders", {}).get("Order", [])
        if isinstance(ordenes, dict): ordenes = [ordenes]
        for o in ordenes:
            id_f = f"FAL-{o['OrderId']}"
            if not supabase.table("ventas_procesadas").select("*").eq("id_orden", id_f).execute().data:
                items = o.get("OrderItems", {}).get("OrderItem", [])
                if isinstance(items, dict): items = [items]
                if items:
                    sku_f = items[0].get("SellerSku")
                    p_db = supabase.table("productos").select("*").eq("sku_falabella", sku_f).execute()
                    if p_db.data:
                        p = p_db.data[0]
                        nuevo = max(0, int(p["stock_total"]) - 1)
                        supabase.table("ventas_procesadas").insert({"id_orden": id_f, "marketplace": "falabella", "sku": p["sku"]}).execute()
                        supabase.table("productos").update({"stock_total": nuevo}).eq("sku", p["sku"]).execute()
                        if "XXXG42" in str(p["sku"]): sync_meli_stock(nuevo)
                        if p.get("woo_id"): sync_woo_stock(p["woo_id"], nuevo)
                        conteo += 1

    # 2. WooCommerce
    w_data = obtener_pedidos_woo()
    for pw in w_data:
        id_w = f"WOO-{pw['id']}"
        if not supabase.table("ventas_procesadas").select("*").eq("id_orden", id_w).execute().data:
            for item in pw.get("line_items", []):
                w_id = str(item["product_id"])
                p_db = supabase.table("productos").select("*").eq("woo_id", w_id).execute()
                if p_db.data:
                    p = p_db.data[0]
                    nuevo = max(0, int(p["stock_total"]) - int(item["quantity"]))
                    supabase.table("ventas_procesadas").insert({"id_orden": id_w, "marketplace": "web", "sku": p["sku"]}).execute()
                    supabase.table("productos").update({"stock_total": nuevo}).eq("sku", p["sku"]).execute()
                    if "XXXG42" in str(p["sku"]): sync_meli_stock(nuevo)
                    if p.get("sku_falabella"): sync_fala_stock(p["sku_falabella"], nuevo)
                    conteo += 1
    return conteo

# --- INTERFAZ STREAMLIT ---

st.title("🚀 MyM Hogar - Sistema Omnicanal")

# Cargar tabla de inventario
try:
    res = supabase.table("productos").select("*").order("sku").execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        st.subheader("📊 Inventario Maestro")
        st.dataframe(df[["sku", "sku_falabella", "woo_id", "stock_total"]], use_container_width=True)

        st.divider()
        st.subheader("🔄 Sincronización Manual")
        c1, c2 = st.columns(2)
        with c1:
            sku_sel = st.selectbox("Producto:", df["sku"].tolist())
        with c2:
            stk_val = st.number_input("Nuevo Stock:", min_value=0, step=1)
        
        if st.button("🚀 Actualizar Todo"):
            p = df[df["sku"] == sku_sel].iloc[0]
            supabase.table("productos").update({"stock_total": stk_val}).eq("sku", sku_sel).execute()
            if "XXXG42" in str(sku_sel): sync_meli_stock(stk_val)
            if p.get("sku_falabella"): sync_fala_stock(p["sku_falabella"], stk_val)
            if p.get("woo_id"): sync_woo_stock(p["woo_id"], stk_val)
            st.success("Sincronización manual lista.")

        st.divider()
        st.subheader("🕵️ Detector de Ventas")
        if st.button("🔥 BUSCAR VENTAS NUEVAS"):
            c = procesar_ventas()
            st.success(f"Proceso terminado. Ventas nuevas: {c}")

except Exception as e:
    st.error(f"Error: {e}")
