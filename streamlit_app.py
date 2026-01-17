import streamlit as st
from supabase import create_client
import os, pandas as pd, requests, hashlib, hmac, urllib.parse
from datetime import datetime, timezone

# --- CONFIGURACIÓN CON REVISIÓN DE ERRORES ---
st.set_page_config(page_title="MyM Hogar - Omnicanal", layout="wide")

# Intentamos leer las variables de Railway
try:
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    MELI_TOKEN = os.getenv("MELI_TOKEN") # Verifica que en Railway se llame igual
    WOO_URL = os.getenv("WOO_URL")
    WOO_CK = os.getenv("WOO_CK")
    WOO_CS = os.getenv("WOO_CS")
    
    # Datos de Falabella (Hardcoded por ahora para asegurar arranque)
    F_API_KEY = "bacfa61d25421da20c72872fcc24569266563eb1"
    F_USER_ID = "ext_md.ali@falabella.cl"
    F_BASE_URL = "https://sellercenter-api.falabella.com/"

    # Verificación de que no falte nada crítico
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("❌ Faltan las variables de Supabase en Railway.")
        st.stop()

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
except Exception as e:
    st.error(f"⚠️ Error al cargar las variables de entorno: {e}")
    st.stop()

# --- SI LLEGA AQUÍ, EL CÓDIGO ARRANCARÁ ---
st.title("🚀 MyM Hogar - Control Omnicanal")
# ... resto de tu código ...
