import streamlit as st
from supabase import create_client
import os, pandas as pd, requests, hashlib, hmac, urllib.parse
from datetime import datetime, timezone

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="MyM Hogar - Control Total", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
F_API_KEY = "bacfa61d25421da20c72872fcc24569266563eb1"
F_USER_ID = "ext_md.ali@falabella.cl"
F_BASE_URL = "https://sellercenter-api.falabella.com/"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. MOTORES DE COMUNICACIÓN (APIs)
def firmar_fala(params):
    ordenados = sorted(params.items(), key=lambda x: x[0])
    query_string = urllib.parse.urlencode(ordenados)
    signature = hmac.new(F_API_KEY.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{F_BASE_URL}?{query_string}&Signature={signature}"

def enviar_stock_falabella(sku_f, qty):
    """Envía stock a Falabella usando el formato v500/ProductUpdate"""
    piezas = [
        '<?xml version="1.0" encoding="UTF-8" ?>',
        '<Request><Product><SellerSku>', str(sku_f), '</SellerSku>',
        '<BusinessUnits><BusinessUnit><OperatorCode>facl</OperatorCode>',
        '<Stock>', str(int(qty)), '</Stock></BusinessUnit></BusinessUnits>',
        '</Product></Request>'
    ]
    xml_data = "".join(piezas)
    params = {
        "Action": "ProductUpdate",
        "Format": "JSON",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "UserID": F_USER_ID,
        "Version": "1.0"
    }
    try:
        url = firmar_fala(params)
        res = requests.post(url, data=xml_data, headers={'Content-Type': 'application/xml'})
        return res.json()
    except: return None

def obtener_pedidos_falabella():
    """Consulta órdenes recientes en Falabella"""
    params = {
        "Action": "GetOrders",
        "Format": "JSON",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "UserID": F_USER_ID,
        "Version": "1.0",
        "CreatedAfter": "2026-01-10T00:00:00" # Filtro de fecha para el test
    }
    try:
        url = firmar_fala(params)
        res = requests.get(url)
        return res.json()
    except: return None

# 3. INTERFAZ STREAMLIT
st.title("🚀 MyM Hogar - Sincronizador Multicanal")

# --- BLOQUE 1: VISTA DE INVENTARIO ---
try:
    res_db = supabase.table("productos").select("*").order("sku").execute()
    df = pd.DataFrame(res_db.data)
except:
    df = pd.DataFrame()

if not df.empty:
    st.subheader("📊 Inventario Actual")
    st.dataframe(df[["sku", "sku_falabella", "nombre", "stock_total"]], use_container_width=True)

    # --- BLOQUE 2: ACTUALIZACIÓN MANUAL ---
    st.divider()
    st.subheader("🔄 Actualización de Stock Manual")
    c1, c2 = st.columns(2)
    with c1:
        prod_sel = st.selectbox("Elegir Producto:", df["sku"].tolist())
    with c2:
        nuevo_stk = st.number_input("Nuevo Stock Global:", min_value=0, step=1)
    
    if st.button("Sincronizar Manualmente"):
        p = df[df["sku"] == prod_sel].iloc[0]
        # 1. Supabase
        supabase.table("productos").update({"stock_total": nuevo_stk}).eq("sku", prod_sel).execute()
        # 2. Mercado Libre (Atajo Pañal)
        if "XXXG42" in prod_sel:
            requests.put("https://api.mercadolibre.com/items/MLC2884836674", 
                        json={"available_quantity": int(nuevo_stk)}, 
                        headers={'Authorization': f'Bearer {MELI_TOKEN}'})
        # 3. Falabella
        if p["sku_falabella"]:
            enviar_stock_falabella(p["sku_falabella"], nuevo_stk)
        st.success(f"Stock actualizado a {nuevo_stk} en todos los canales.")

# --- BLOQUE 3: DETECTOR DE VENTAS ---
st.divider()
st.subheader("🕵️ Detector de Ventas Inverso (Falabella -> MeLi)")
st.info("Este botón busca ventas nuevas en Falabella y descuenta el stock en Mercado Libre automáticamente.")

if st.button("🔥 PROCESAR VENTAS NUEVAS"):
    with st.spinner("Leyendo órdenes de Falabella..."):
        data = obtener_pedidos_falabella()
        if data and "SuccessResponse" in data:
            ordenes = data["SuccessResponse"]["Body"].get("Orders", [])
            conteo = 0
            
            for orden in ordenes:
                id_fala = str(orden["OrderId"])
                
                # Verificar si ya procesamos esta orden
                check = supabase.table("ventas_procesadas").select("*").eq("id_orden", id_fala).execute()
                
                if not check.data:
                    # Buscamos el SKU dentro de la orden
                    items = orden.get("OrderItems", [])
                    if not items: continue
                    
                    # Extraemos el SKU de Falabella
                    sku_f_vendido = items[0].get("SellerSku")
                    
                    # Buscamos en nuestra base de datos quién es el dueño de ese SKU
                    p_db = supabase.table("productos").select("*").eq("sku_falabella", sku_f_vendido).execute()
                    
                    if p_db.data:
                        p = p_db.data[0]
                        stk_actual = int(p["stock_total"])
                        nuevo_stk = stk_actual - 1 if stk_actual > 0 else 0
                        
                        # 1. Registrar para no repetir
                        supabase.table("ventas_procesadas").insert({
                            "id_orden": id_fala, "marketplace": "falabella", "sku": p["sku"]
                        }).execute()
                        
                        # 2. Actualizar Supabase
                        supabase.table("productos").update({"stock_total": nuevo_stk}).eq("sku", p["sku"]).execute()
                        
                        # 3. Actualizar Mercado Libre (Pañal)
                        if "XXXG42" in p["sku"]:
                            requests.put("https://api.mercadolibre.com/items/MLC2884836674", 
                                        json={"available_quantity": nuevo_stk}, 
                                        headers={'Authorization': f'Bearer {MELI_TOKEN}'})
                        
                        # 4. Actualizar Falabella (para que el stock baje también allá)
                        if p["sku_falabella"]:
                            enviar_stock_falabella(p["sku_falabella"], nuevo_stk)
                        
                        st.warning(f"🚨 ¡Venta Detectada! Orden {id_fala}. SKU {p['sku']} bajó de {stk_actual} a {nuevo_stk}")
                        conteo += 1
            
            if conteo == 0:
                st.info("No se encontraron ventas nuevas.")
            else:
                st.success(f"Proceso terminado. {conteo} ventas sincronizadas.")
        else:
            st.error("No se pudo conectar con la API de Falabella.")
