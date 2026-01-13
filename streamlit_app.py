import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os
import pandas as pd
from PIL import Image

# Logo
try:
    logo = Image.open("assets/mym_hogar.png")
except:
    logo = "📦"

st.set_page_config(page_title="M&M Hogar", page_icon=logo, layout="wide")

# Configurar Supabase
SUPABASE_URL
