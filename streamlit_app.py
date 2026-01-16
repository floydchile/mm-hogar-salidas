import streamlit as st
import os
import requests

st.set_page_config(page_title="Inspector Directo", layout="wide")
st.warning("⚠️ **MODO INSPECCIÓN: REVISANDO PUBLICACIÓN ESPECÍFICA**")

MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
ITEM_ID_OBJETIVO = "MLC2884836674" # La que tú dices que es la buena

def inspeccionar_item_especifico(item_id):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    try:
        # Consultamos directamente por el ID, sin buscar por SKU
        res = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=headers).json()
        
        datos = {
            "ID": res.get('id'),
            "Título": res.get('title'),
            "Estado": res.get('status'),
            "SKU_Principal": res.get('seller_custom_field'),
            "Tiene_Variantes": "Sí" if res.get('variations') else "No",
            "Variantes": []
        }
        
        if res.get('variations'):
            for v in res['variations']:
                datos["Variantes"].append({
                    "ID_Variante": v.get('id'),
                    "SKU_Variante": v.get('seller_custom_field'),
                    "Stock_Actual": v.get('available_quantity')
                })
        return datos
    except Exception as e:
        return {"error": str(e)}

st.title("🕵️ ¿Qué ve Mercado Libre en la publicación correcta?")

if st.button("🔍 Analizar MLC2884836674"):
    resultado = inspeccionar_item_especifico(ITEM_ID_OBJETIVO)
    
    if "error" in resultado:
        st.error(f"No se pudo conectar: {resultado['error']}")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.write("### Datos Generales")
            st.json(resultado)
        with col2:
            st.info("### Comparación Crucial")
            sku_en_meli = resultado["SKU_Principal"]
            st.write(f"Tu Base de Datos busca: `EBSP XXXG42`")
            st.write(f"Mercado Libre tiene: `{sku_en_meli}`")
            
            if not sku_en_meli and not resultado["Variantes"]:
                st.error("❗ ESTA PUBLICACIÓN NO TIENE SKU ASIGNADO EN MELI")
            elif resultado["Variantes"]:
                st.warning("⚠️ ESTA PUBLICACIÓN TIENE VARIANTES. El SKU debe estar dentro de la variante, no en el principal.")
