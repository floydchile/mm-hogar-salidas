import streamlit as st
import os
import requests

st.set_page_config(page_title="Analizador de Atributos", layout="wide")
st.warning("⚠️ **BUSCANDO EL CAMPO SKU OCULTO**")

MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
ITEM_ID = "MLC2884836674"

def obtener_json_crudo(item_id):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    url = f"https://api.mercadolibre.com/items/{item_id}"
    res = requests.get(url, headers=headers).json()
    return res

st.title("🕵️ Buscador de Atributos MeLi")

if st.button(f"🔍 Analizar {ITEM_ID} a fondo"):
    raw_data = obtener_json_crudo(ITEM_ID)
    
    if "id" in raw_data:
        st.success("¡Datos obtenidos!")
        
        # Buscador manual en el JSON
        st.write("### 1. Búsqueda Directa del texto 'EBSP XXXG42'")
        # Convertimos todo a string para buscar
        raw_str = str(raw_data)
        if "EBSP XXXG42" in raw_str:
            st.balloons()
            st.info("🎯 ¡El texto existe en alguna parte del JSON! Vamos a ver dónde:")
        else:
            st.error("❌ El texto 'EBSP XXXG42' NO existe en la respuesta de la API. Está en la web, pero no en la API.")

        # Mostramos los atributos para ver si está ahí
        st.write("### 2. Revisando la 'Ficha Técnica' (Attributes)")
        atributos = raw_data.get('attributes', [])
        for attr in atributos:
            if attr.get('value_name') == "EBSP XXXG42" or attr.get('id') == "SELLER_SKU":
                st.write(f"✅ **Encontrado en atributo:** ID: `{attr.get('id')}` | Valor: `{attr.get('value_name')}`")

        st.write("### 3. JSON Completo (Para inspección visual)")
        st.json(raw_data)
    else:
        st.error("No se pudo obtener el ítem. Revisa el Token.")
