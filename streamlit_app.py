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
    st.error("❌ Error: Faltan las credenciales de Supabase en Railway.")
    st.stop()

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()
USUARIOS_VALIDOS = ["pau", "dany", "miguel"]

# --- LÓGICA DE WEBHOOK (MERCADO LIBRE -> MYM) ---
# Se ejecuta SOLO si la URL tiene los parámetros de MeLi
q_params = st.query_params
if "topic" in q_params and "resource" in q_params:
    topic = q_params.get("topic")
    resource = q_params.get("resource")
    if topic == "orders_v2" and MELI_TOKEN:
        try:
            headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
            order_res = requests.get(f"https://api.mercadolibre.com{resource}", headers=headers).json()
            for item in order_res.get('order_items', []):
                sku = item.get('item', {}).get('seller_custom_field')
                cant = item.get('quantity')
                if sku:
                    supabase.rpc("registrar_salida", {
                        "p_sku": sku, "p_cantidad": int(cant), 
                        "p_canal": "Mercadolibre", "p_usuario": "BOT_MELI"
                    }).execute()
        except:
            pass
    st.stop()

# --- FUNCIONES DE APOYO ---
def formato_clp(valor):
    return f"${int(valor):,}".replace(",", ".")

def buscar_productos(query: str = ""):
    try:
        db_query = supabase.table("productos").select("*")
        if query:
            db_query = db_query.or_(f"sku.ilike.%{query}%,nombre.ilike.%{query}%")
        return db_query.order("sku").execute().data
    except:
        return []

def sincronizar_stock_meli(sku, nuevo_stock):
    if not MELI_TOKEN or not MELI_USER_ID: return False
    try:
        sku_encoded = urllib.parse.quote(sku)
        search_url = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?sku={sku_encoded}"
        headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
        search_res = requests.get(search_url, headers=headers).json()
        if search_res.get('results'):
            item_id = search_res['results'][0]
            requests.put(f"https://api.mercadolibre.com/items/{item_id}", 
                         json={"available_quantity": int(nuevo_stock)}, headers=headers)
            return True
    except:
        pass
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
        
        # Sincronizar MeLi
        p_data = supabase.table("productos").select("stock_total").eq("sku", sku).single().execute()
        if p_data.data:
            sincronizar_stock_meli(sku, p_data.data['stock_total'])
        return True, "Ok"
    except Exception as e:
        return False, str(e)

# --- INTERFAZ ---
try:
    logo = Image.open("assets/mym_hogar.png")
except:
    logo = None

if 'usuario_ingresado' not in st.session_state: st.session_state.usuario_ingresado = None
if 'form_count' not in st.session_state: st.session_state.form_count = 0

with st.sidebar:
    if logo: st.image(logo, width=150)
    if st.session_state.usuario_ingresado:
        st.write(f"Usuario: {st.session_state.usuario_ingresado.upper()}")
        if st.button("🚪 Salir", width="stretch"):
            st.session_state.usuario_ingresado = None
            st.rerun()
    else:
        u = st.text_input("Usuario:").lower().strip()
        if st.button("✅ Entrar", type="primary", width="stretch"):
            if u in USUARIOS_VALIDOS:
                st.session_state.usuario_ingresado = u
                st.rerun()

if not st.session_state.usuario_ingresado:
    st.info("👋 Ingresa para continuar")
    st.stop()

st.title("📦 M&M Hogar - Inventario")
t1, t2, t3, t4 = st.tabs(["🛒 Movimientos", "📋 Historial", "📈 Stock", "⚙️ Configuración"])

with t1:
    c_v, c_e = st.columns(2)
    with c_v:
        st.subheader("Venta")
        sk_v = st.text_input("Buscar SKU:", key=f"v_{st.session_state.form_count}").upper()
        if sk_v:
            prods = buscar_productos(sk_v)
            if prods:
                p = st.selectbox("Seleccionar:", prods, format_func=lambda x: f"{x['sku']} - {x['nombre']} ({x['stock_total']})")
                cant = st.number_input("Cantidad:", min_value=1, key=f"cv_{st.session_state.form_count}")
                can = st.selectbox("Canal:", ["Mercadolibre", "WhatsApp", "Web", "Retiro"])
                if st.button("🚀 Vender", type="primary", width="stretch"):
                    ok, m = registrar_movimiento("salida", p['sku'], cant, can, st.session_state.usuario_ingresado)
                    if ok: st.success("Vendido!"); st.session_state.form_count += 1; st.rerun()

    with c_e:
        st.subheader("Entrada")
        sk_e = st.text_input("Buscar SKU Entrada:", key=f"e_{st.session_state.form_count}").upper()
        if sk_e:
            prods_e = buscar_productos(sk_e)
            if prods_e:
                p_e = st.selectbox("Seleccionar:", prods_e, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
                cant_e = st.number_input("Cantidad:", min_value=1, key=f"ce_{st.session_state.form_count}")
                if st.button("📥 Cargar", type="primary", width="stretch"):
                    ok, m = registrar_movimiento("entrada", p_e['sku'], cant_e, p_e['und_x_embalaje'], st.session_state.usuario_ingresado)
                    if ok: st.success("Cargado!"); st.session_state.form_count += 1; st.rerun()

with t2:
    st.subheader("Historial")
    h = supabase.table("salidas").select("*").order("fecha", desc=True).limit(20).execute().data
    if h: st.table(pd.DataFrame(h)[["fecha", "sku", "cantidad", "canal", "usuario"]])

with t3:
    st.subheader("Stock")
    s = buscar_productos()
    if s: st.dataframe(pd.DataFrame(s)[["sku", "nombre", "stock_total"]], width="stretch")

with t4:
    with st.form("nuevo"):
        st.write("Nuevo Producto")
        n_s = st.text_input("SKU").upper()
        n_n = st.text_input("Nombre")
        if st.form_submit_button("Crear"):
            supabase.table("productos").insert({"sku": n_s, "nombre": n_n, "stock_total": 0}).execute()
            st.rerun()
