import streamlit as st
from supabase import create_client
import os, pandas as pd, requests, hashlib, hmac, urllib.parse
from datetime import datetime, timezone

# --- CONFIGURACIÓN SEGURA (RAILWAY VARIABLES) ---
# Usamos os.getenv para leer las variables que pusiste en el panel de Railway
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")

WOO_URL = os.getenv("WOO_URL")
WOO_CK = os.getenv("WOO_CK")
WOO_CS = os.getenv("WOO_CS")

# Falabella (puedes pasarlas a Railway también para máxima seguridad)
F_API_KEY = os.getenv("F_API_KEY", "bacfa61d25421da20c72872fcc24569266563eb1")
F_USER_ID = os.getenv("F_USER_ID", "ext_md.ali@falabella.cl")
F_BASE_URL = "https://sellercenter-api.falabella.com/"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
