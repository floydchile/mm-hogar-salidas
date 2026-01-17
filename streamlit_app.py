import streamlit as st
from supabase import create_client
import os, pandas as pd, requests, hashlib, hmac, urllib.parse
from datetime import datetime, timezone

st.set_page_config(page_title="MyM Multichannel")
st.title("📦 Centro de Control MyM")

# Conexión
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")

# --- FUNCIÓN FALABELLA (Compacta) ---
def sync_falabella(sku_f, qty):
    key = "bacfa61d25421da20c72872fcc24569266563eb1"
    user = "ext_md.ali@falabella.cl"
    url_base = "https://sellercenter-api.falabella.com/"
    
    # Nueva estructura XML para PostOffers
    xml = '<?xml version="1.0" encoding="UTF-8"?>'
    xml += '<Offers>'
    xml += '  <Offer>'
    xml += '    <SellerSku>' + str(sku_f) + '</SellerSku>'
    xml += '    <Quantity>' + str(int(qty)) + '</Quantity>'
    xml += '  </Offer>'
    xml += '</Offers>'
    
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    # Cambiamos la acción a PostOffers
    params = {"Action": "PostOffers", "Format": "JSON", "Timestamp": ts, "UserID": user, "Version": "1.0"}
    
    query = urllib.parse.urlencode(sorted(params.items()))
    sig = hmac.new(key.encode('utf-8'), query.encode('utf-8'), hashlib.sha256).hexdigest()
    
    try:
        res = requests.post(f"{url_base}?{query}&Signature={sig}", data=xml, headers={'Content-Type': 'application/xml'})
        return res.json()
    except: return {"error": "Fallo de red"}

# --- LÓGICA DE INTERFAZ ---
res_db = supabase.table("productos").select("*").execute()
df = pd.DataFrame(res_db.data)

if not df.empty:
    st.dataframe(df[["sku", "sku_falabella", "nombre", "stock_total"]])
    
    with st.form("update_form"):
        sku_sel = st.selectbox("Producto a sincronizar", df["sku"].tolist())
        stk_val = st.number_input("Nuevo Stock Global", min_value=0, step=1)
        boton = st.form_submit_button("Sincronizar en todos los canales")
        
        if boton:
            p = df[df["sku"] == sku_sel].iloc[0]
            
            # 1. Supabase
            supabase.table("productos").update({"stock_total": stk_val}).eq("sku", sku_sel).execute()
            st.success("✅ Supabase: Actualizado")
            
            # 2. Mercado Libre (Pañal)
            if "XXXG42" in sku_sel:
                requests.put("https://api.mercadolibre.com/items/MLC2884836674", 
                            json={"available_quantity": int(stk_val)}, 
                            headers={'Authorization': f'Bearer {MELI_TOKEN}'})
                st.success("✅ Mercado Libre: Actualizado")
            
            # 3. Falabella
            if p["sku_falabella"] and str(p["sku_falabella"]) != "None":
                res_fala = sync_falabella(p["sku_falabella"], stk_val)
                if "SuccessResponse" in str(res_fala):
                    st.success(f"✅ Falabella: Sincronizado ({p['sku_falabella']})")
                else:
                    st.error(f"❌ Falabella Error: {res_fala}")
            else:
                st.info("ℹ️ Falabella saltado (sin SKU vinculado)")

