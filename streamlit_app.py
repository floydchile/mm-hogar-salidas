import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os
import pandas as pd
from PIL import Image
import requests
import urllib.parse

# --- CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="M&M Hogar", page_icon="📦", layout="wide")

st.markdown("""<style>
    .block-container {padding-top: 1rem; padding-bottom: 0rem;}
    .stMetric {background-color: #f8f9fa; border-radius: 10px; padding: 10px; border: 1px solid #eee;}
    [data-testid="stMetricValue"] {font-size: 1.8rem;}
    input[type=number]::-webkit-inner-spin-button, 
    input[type=number]::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
    input[type=number] { -moz-appearance: textfield; }
</style>""", unsafe_allow_html=True)

# --- CONEXIÓN ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
MELI_USER_ID = os.getenv("MELI_USER_ID")

if not SUPABASE_KEY or not SUPABASE_URL:
    st.error("❌ Error: Faltan las credenciales de Supabase.")
    st.stop()

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()
USUARIOS_VALIDOS = ["pau", "dany", "miguel"]

# --- LÓGICA DE WEBHOOK (MERCADO LIBRE -> MYM) ---
# Se activa solo si Mercado Libre envía una notificación
params = st.query_params
if "topic" in params and "resource" in params:
    if params.get("topic") == "orders_v2":
        try:
            headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
            res = requests.get(f"https://api.mercadolibre.com{params.get('resource')}", headers=headers).json()
            for item in res.get('order_items', []):
                sku_meli = item.get('item', {}).get('seller_custom_field')
                cantidad = item.get('quantity')
                if sku_meli:
                    supabase.rpc("registrar_salida", {
                        "p_sku": sku_meli, "p_cantidad": int(cantidad), 
                        "p_canal": "Mercadolibre", "p_usuario": "BOT_MELI"
                    }).execute()
        except: pass
    st.stop()

# --- FUNCIONES DE INTEGRACIÓN ---
def sincronizar_stock_meli(sku, nuevo_stock):
    if not MELI_TOKEN: return False
    try:
        sku_enc = urllib.parse.quote(sku)
        headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
        url_busca = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?sku={sku_enc}"
        r_busca = requests.get(url_busca, headers=headers).json()
        if r_busca.get('results'):
            item_id = r_busca['results'][0]
            requests.put(f"https://api.mercadolibre.com/items/{item_id}", 
                         json={"available_quantity": int(nuevo_stock)}, headers=headers)
            return True
    except: pass
    return False

def registrar_movimiento(tipo, sku, cantidad, extra_val, usuario, precio=None):
    try:
        if tipo == "entrada":
            if precio is not None:
                supabase.table("productos").update({"precio_costo_contenedor": float(precio)}).eq("sku", sku).execute()
            supabase.rpc("registrar_entrada", {"p_sku": sku, "p_cantidad": int(cantidad), "p_und_x_embalaje": extra_val, "p_usuario": usuario}).execute()
        else:
            res = supabase.rpc("registrar_salida", {"p_sku": sku, "p_cantidad": int(cantidad), "p_canal": extra_val, "p_usuario": usuario}).execute()
            if "ERROR" in res.data: return False, res.data
        
        # Sincronizar con MeLi
        p_data = supabase.table("productos").select("stock_total").eq("sku", sku).single().execute()
        if p_data.data:
            sincronizar_stock_meli(sku, p_data.data['stock_total'])
        return True, "Ok"
    except Exception as e: return False, str(e)

def buscar_productos(query: str = ""):
    try:
        db = supabase.table("productos").select("*")
        if query: db = db.or_(f"sku.ilike.%{query}%,nombre.ilike.%{query}%")
        return db.order("sku").execute().data
    except: return []

def formato_clp(valor):
    return f"${int(valor):,}".replace(",", ".")

# --- INTERFAZ ---
try:
    logo = Image.open("assets/mym_hogar.png")
except:
    logo = None

if 'user' not in st.session_state: st.session_state.user = None
if 'f_count' not in st.session_state: st.session_state.f_count = 0

with st.sidebar:
    if logo: st.image(logo, width=150)
    if st.session_state.user:
        st.write(f"Sesión: {st.session_state.user.upper()}")
        if st.button("Salir", width="stretch"): 
            st.session_state.user = None
            st.rerun()
    else:
        u = st.text_input("Usuario:").lower().strip()
        if st.button("Ingresar", type="primary", width="stretch"):
            if u in USUARIOS_VALIDOS:
                st.session_state.user = u
                st.rerun()

if not st.session_state.user:
    st.info("Ingresa para continuar")
    st.stop()

st.title("📦 M&M Hogar - Gestión")
t1, t2, t3, t4 = st.tabs(["🛒 Movimientos", "📋 Historial", "📈 Stock", "⚙️ Configuración"])

with t1:
    col_v, col_e = st.columns(2)
    with col_v:
        st.subheader("🚀 Venta")
        sk_v = st.text_input("SKU Venta:", key=f"v_{st.session_state.f_count}").upper()
        if sk_v:
            ps_v = buscar_productos(sk_v)
            if ps_v:
                sel_v = st.selectbox("Prod:", ps_v, format_func=lambda x: f"{x['sku']} - {x['nombre']} ({x['stock_total']})")
                cant_v = st.number_input("Cant:", min_value=1, key=f"cv_{st.session_state.f_count}")
                can = st.selectbox("Canal:", ["Mercadolibre", "WhatsApp", "Web", "Retiro"])
                if st.button("Finalizar Venta", type="primary", width="stretch"):
                    ok, m = registrar_movimiento("salida", sel_v['sku'], cant_v, can, st.session_state.user)
                    if ok: st.success("Ok!"); st.session_state.f_count+=1; st.rerun()

    with col_e:
        st.subheader("📥 Entrada")
        sk_e = st.text_input("SKU Entrada:", key=f"e_{st.session_state.f_count}").upper()
        if sk_e:
            ps_e = buscar_productos(sk_e)
            if ps_e:
                sel_e = st.selectbox("Prod:", ps_e, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
                cant_e = st.number_input("Cant:", min_value=1, key=f"ce_{st.session_state.f_count}")
                costo = st.number_input("Costo:", value=int(sel_e['precio_costo_contenedor']))
                if st.button("Confirmar Entrada", type="primary", width="stretch"):
                    ok, m = registrar_movimiento("entrada", sel_e['sku'], cant_e, sel_e['und_x_embalaje'], st.session_state.user, costo)
                    if ok: st.success("Ok!"); st.session_state.f_count+=1; st.rerun()

with t2:
    st.subheader("Historial")
    h_s = supabase.table("salidas").select("*").order("fecha", desc=True).limit(20).execute().data
    if h_s: st.dataframe(pd.DataFrame(h_s)[["fecha", "sku", "cantidad", "canal", "usuario"]], width="stretch")

with t3:
    st.subheader("Inventario")
    prods = buscar_productos()
    if prods: st.dataframe(pd.DataFrame(prods)[["sku", "nombre", "stock_total", "und_x_embalaje"]], width="stretch")

with t4:
    with st.form("np"):
        st.subheader("Nuevo Producto")
        n_s = st.text_input("SKU").upper()
        n_n = st.text_input("Nombre")
        n_u = st.number_input("Und x Emb", min_value=1)
        if st.form_submit_button("Crear"):
            supabase.table("productos").insert({"sku": n_s, "nombre": n_n, "und_x_embalaje": n_u, "stock_total": 0}).execute()
            st.rerun()
