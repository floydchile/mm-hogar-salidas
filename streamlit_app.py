import streamlit as st
from supabase import create_client
import os, pandas as pd, requests, hashlib, hmac, urllib.parse
from datetime import datetime, timezone

# 1. CONFIGURACIÓN INICIAL
st.set_page_config(page_title="MyM Hogar - Omnicanal", layout="wide")

# Carga de variables desde Railway (Ajustado a tus nombres en Railway)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_CLIENT_ID = os.getenv("MELI_APP_ID")
MELI_CLIENT_SECRET = os.getenv("MELI_CLIENT_SECRET")
WOO_URL = os.getenv("WOO_URL")
WOO_CK = os.getenv("WOO_CK")
WOO_CS = os.getenv("WOO_CS")

# Datos Falabella (Fijos)
F_API_KEY = "bacfa61d25421da20c72872fcc24569266563eb1"
F_USER_ID = "ext_md.ali@falabella.cl"
F_BASE_URL = "https://sellercenter-api.falabella.com/"

# Conexión a Base de Datos
if not SUPABASE_URL:
    st.error("❌ No se detectan variables en Railway.")
    st.stop()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- MOTOR DE TOKENS MERCADO LIBRE (AUTOMÁTICO) ---

def obtener_tokens_db():
    """Lee los tokens guardados en Supabase"""
    try:
        res = supabase.table("config_tokens").select("*").eq("id", "meli").execute()
        return res.data[0] if res.data else None
    except: return None

def renovar_tokens_meli():
    """Pide nuevo Access Token usando el Refresh Token (TG)"""
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
        # GUARDAR LOS NUEVOS TOKENS EN SUPABASE
        supabase.table("config_tokens").update({
            "access_token": data['access_token'],
            "refresh_token": data['refresh_token'],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("id", "meli").execute()
        return data['access_token']
    return None

# --- MOTORES DE SINCRONIZACIÓN (SALIDA) ---

def sync_meli_stock(qty):
    """Actualiza stock en MeLi con auto-refresco"""
    tokens = obtener_tokens_db()
    if not tokens: return False
    
    url = "https://api.mercadolibre.com/items/MLC2884836674" # ID del Pañal
    headers = {'Authorization': f'Bearer {tokens["access_token"]}', 'Content-Type': 'application/json'}
    
    res = requests.put(url, json={"available_quantity": int(qty)}, headers=headers)
    
    # Si el token falló (401), renovamos y reintentamos
    if res.status_code == 401:
        st.info("🔄 Renovando acceso a Mercado Libre...")
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

# --- MOTOR DE PROCESAMIENTO DE VENTAS ---

def procesar_ventas_globales():
    conteo = 0
    # Aquí iría la lógica de búsqueda en Falabella y Web (la que ya probamos)
    # Por ahora devolvemos 0 para asegurar estabilidad
    return conteo

# --- INTERFAZ VISUAL ---

st.title("🚀 MyM Hogar - Sistema Omnicanal")

try:
    # 1. Mostrar Inventario
    res_db = supabase
