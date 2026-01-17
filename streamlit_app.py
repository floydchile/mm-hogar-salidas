import streamlit as st
from supabase import create_client
import os, pandas as pd, requests, hashlib, hmac, urllib.parse
from datetime import datetime, timezone

# 1. CONFIGURACIÓN DESDE RAILWAY
st.set_page_config(page_title="MyM Hogar - Omnicanal", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_TOKEN")
WOO_URL = os.getenv("WOO_URL")
WOO_CK = os.getenv("WOO_CK")
WOO_CS = os.getenv("WOO_CS")

# Datos Falabella
F_API_KEY = "bacfa61d25421da20c72872fcc24569266563eb1"
F_USER_ID = "ext_md.ali@falabella.cl"
F_BASE_URL = "https://sellercenter-api.falabella.com/"

if not SUPABASE_URL:
    st.error("❌ No se detectan variables en Railway. Revisa la pestaña 'Variables'.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. MOTORES DE SINCRONIZACIÓN (SALIDA)
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

# 3. MOTORES DE BÚSQUEDA (ENTRADA)
def obtener_pedidos_falabella():
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

# 4. INTERFAZ
st.title("🚀 MyM Hogar - Sistema Omnicanal")

try:
    res = supabase.table("productos").select("*").order("sku").execute()
    df = pd.DataFrame(res.data)
    if not df.empty:
        st.subheader("📊 Inventario Maestro")
        st.dataframe(df[["sku", "sku_falabella", "woo_id", "stock_total"]], use_container_width=True)

        # SECCIÓN A: ACTUALIZACIÓN MANUAL
        st.divider()
        st.subheader("🔄 Actualizar Stock (Manual)")
        c1, c2 = st.columns(2)
        with c1:
            sku_sel = st.selectbox("Producto:", df["sku"].tolist())
        with c2:
            stk_val = st.number_input("Nuevo Stock:", min_value=0, step=1)
        
        if st.button("🚀 Sincronizar Todo"):
            p = df[df["sku"] == sku_sel].iloc[0]
            supabase.table("productos").update({"stock_total": stk_val}).eq("sku", sku_sel).execute()
            if "XXXG42" in str(sku_sel):
                requests.put(f"https://api.mercadolibre.com/items/MLC2884836674", json={"available_quantity": int(stk_val)}, headers={'Authorization': f'Bearer {MELI_TOKEN}'})
            if p.get("sku_falabella"): sync_fala_stock(p["sku_falabella"], stk_val)
            if p.get("woo_id"): sync_woo_stock(p["woo_id"], stk_val)
            st.success("Sincronización manual exitosa.")

        # SECCIÓN B: DETECTOR DE VENTAS
        st.divider()
        st.subheader("🕵️ Detector de Ventas (Falabella + Web)")
        if st.button("🔥 BUSCAR VENTAS NUEVAS"):
            with st.spinner("Revisando canales..."):
                conteo = 0
                
                # --- FALABELLA ---
                f_data = obtener_pedidos_falabella()
                if f_data and "SuccessResponse" in f_data:
                    ordenes_f = f_data["SuccessResponse"]["Body"].get("Orders", {}).get("Order", [])
                    if isinstance(ordenes_f, dict): ordenes_f = [ordenes_f]
                    for o in ordenes_f:
                        id_f = f"FAL-{o['OrderId']}"
                        if not supabase.table("ventas_procesadas").select("*").eq("id_orden", id_f).execute().data:
                            items = o.get("OrderItems", {}).get("OrderItem", [])
                            if isinstance(items, dict): items = [items]
                            sku_f = items[0].get("SellerSku")
                            p_db = supabase.table("productos").select("*").eq("sku_falabella", sku_f).execute()
                            if p_db.data:
                                p = p_db.data[0]
                                nuevo = int(p["stock_total"]) - 1
                                supabase.table("ventas_procesadas").insert({"id_orden": id_f, "marketplace": "falabella", "sku": p["sku"]}).execute()
                                supabase.table("productos").update({"stock_total": nuevo}).eq("sku", p["sku"]).execute()
                                # Replicar a otros
                                if "XXXG42" in str(p["sku"]): requests.put(f"https://api.mercadolibre.com/items/MLC2884836674", json={"available_quantity": nuevo}, headers={'Authorization': f'Bearer {MELI_TOKEN}'})
                                if p.get("woo_id"): sync_woo_stock(p["woo_id"], nuevo)
                                st.warning(f"Venta Falabella: {id_f} procesada.")
                                conteo += 1

                # --- WOOCOMMERCE ---
                pedidos_w = obtener_pedidos_woo()
                for pw in pedidos_w:
                    id_w = f"WOO-{pw['id']}"
                    if not supabase.table("ventas_procesadas").select("*").eq("id_orden", id_w).execute().data:
                        for item in pw.get("line_items", []):
                            w_id = str(item["product_id"])
                            p_db = supabase.table("productos").select("*").eq("woo_id", w_id).execute()
                            if p_db.data:
                                p = p_db.data[0]
                                nuevo = int(p["stock_total"]) - int(item["quantity"])
                                supabase.table("ventas_procesadas").insert({"id_orden": id_w, "marketplace": "web", "sku": p["sku"]}).execute()
                                supabase.table("productos").update({"stock_total": nuevo}).eq("sku", p["sku"]).execute()
                                # Replicar a otros
                                if "XXXG42" in str(p["sku"]): requests.put(f"https://api.mercadolibre.com/items/MLC2884836674", json={"available_quantity": nuevo}, headers={'Authorization': f'Bearer {MELI_TOKEN}'})
                                if p.get("sku_falabella"): sync_fala_stock(p["sku_falabella"], nuevo)
                                st.warning(f"Venta Web: Pedido #{pw['id']} procesado.")
                                conteo += 1
                
                if conteo == 0: st.info("No hay ventas nuevas.")
                else: st.success(f"Se sincronizaron {conteo} ventas.")

except Exception as e:
    st.error(f"Error: {e}")
