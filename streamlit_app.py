import streamlit as st
from supabase import create_client
import os, pandas as pd, requests, hashlib, hmac, urllib.parse
from datetime import datetime, timezone

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="M&M Sincro Total", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
F_API_KEY = "bacfa61d25421da20c72872fcc24569266563eb1"
F_USER_ID = "ext_md.ali@falabella.cl"
F_BASE_URL = "https://sellercenter-api.falabella.com/"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- MOTOR FALABELLA (FIRMA) ---
def firmar_falabella(params):
    ordenados = sorted(params.items(), key=lambda x: x[0])
    query_string = urllib.parse.urlencode(ordenados)
    signature = hmac.new(F_API_KEY.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"{F_BASE_URL}?{query_string}&Signature={signature}"

# --- FUNCIÓN ACTUALIZAR FALABELLA ---
def actualizar_stock_falabella(sku_fala, cantidad):
    # Usamos formato .format() para evitar errores de llaves en f-strings
    xml_template = """<?xml version="1.0" encoding="UTF-8"?>
<Request>
    <Product>
        <SellerSku>{sku}</SellerSku>
        <Quantity>{qty}</Quantity>
    </Product>
</Request>"""
    payload_xml = xml_template.format(sku=sku_fala, qty=int(cantidad))
    
    params = {
        "Action": "UpdatePriceQuantity",
        "Format": "JSON",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "UserID": F_USER_ID,
        "Version": "1.0"
    }
    
    url = firmar_falabella(params)
    try:
        # Falabella requiere que el XML se envíe como texto plano o x-www-form-urlencoded
        res = requests.post(url, data=payload_xml, headers={'Content-Type': 'application/xml'})
        
        # Si devuelve FeedId, Falabella lo puso en cola
        data = res.json()
        if "SuccessResponse" in data:
            feed_id = data["SuccessResponse"]["Head"].get("RequestId", "En cola")
            return True, feed_id
        return False, data.get("ErrorResponse", {}).get("Head", {}).get("ErrorMessage", "Error desconocido")
    except Exception as e:
        return False, str(e)

# --- INTERFAZ ---
st.title("🚀 MyM Hogar - Sincronizador Multichannel")

try:
    prods = supabase.table("productos").select("*").order("sku").execute().data
except:
    prods = []

if prods:
    # Selector de producto
    p = st.selectbox("Selecciona producto:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Stock en MyM", p['stock_total'])
        nuevo_stock = st.number_input("Nuevo Stock Global:", value=int(p['stock_total']))
    
    with col2:
        st.info(f"🔗 **Mapeo:**\n- MeLi: {p['sku']}\n- Falabella: {p.get('sku_falabella', 'No vinculado')}")

    if st.button("🔥 EJECUTAR SINCRONIZACIÓN TRIPLE"):
        # 1. Supabase
        supabase.table("productos").update({"stock_total": nuevo_stock}).eq("sku", p['sku']).execute()
        st.success("✅ Supabase: Actualizado.")

        # 2. Mercado Libre (Atajo para el pañal)
        if "XXXG42" in p['sku']:
            headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
            requests.put(f"https://api.mercadolibre.com/items/MLC2884836674", 
                        json={"available_quantity": int(nuevo_stock)}, headers=headers)
            st.success("✅ Mercado Libre: Actualizado.")

        # 3. Falabella
        sku_f = p.get('sku_falabella')
        if sku_f and sku_f != "None":
            ok, msg = actualizar_stock_falabella(sku_f, nuevo_stock)
            if ok:
                st.success(f"✅ Falabella: Recibido (ID Proceso: {msg})")
                st.caption("Nota: Falabella tarda ~5 min en reflejar el cambio en su panel.")
            else:
                st.error(f"❌ Falabella: {msg}")
        else:
            st.warning("⚠️ Falabella: Saltado (Sin SKU vinculado en Supabase)")

    st.divider()
    st.write("### 📊 Vista previa de la base de datos")
    st.dataframe(pd.DataFrame(prods)[["sku", "sku_falabella", "nombre", "stock_total"]])
