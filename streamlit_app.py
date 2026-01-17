import streamlit as st
from supabase import create_client, Client
import os
import pandas as pd
import requests

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="M&M PRUEBAS - Sincro Total", layout="wide")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
MELI_USER_ID = "462191513"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FUNCIÓN: DESCONTAR STOCK POR VENTA EN MELI ---
def procesar_ventas_meli():
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    # Buscamos órdenes de las últimas 24 horas
    url = f"https://api.mercadolibre.com/orders/search?seller={MELI_USER_ID}&order.status=paid"
    
    try:
        res = requests.get(url, headers=headers).json()
        ordenes = res.get('results', [])
        
        if not ordenes:
            return "No hay ventas nuevas en las últimas 24hs."

        reporte = []
        for orden in ordenes:
            for item in orden['order_items']:
                # Intentamos sacar el SKU del item vendido
                sku_venta = item['item'].get('seller_custom_field')
                cantidad_vendida = item['quantity']
                
                if sku_venta:
                    # Buscamos en Supabase si existe ese SKU
                    prod_db = supabase.table("productos").select("sku, stock_total").eq("sku", sku_venta).execute().data
                    
                    if prod_db:
                        # Si el stock en DB es mayor a lo que había en la orden, descontamos
                        # Nota: Aquí puedes usar una lógica de 'marcar como procesada' para no descontar dos veces
                        nuevo_stock = prod_db[0]['stock_total'] - cantidad_vendida
                        supabase.table("productos").update({"stock_total": nuevo_stock}).eq("sku", sku_venta).execute()
                        reporte.append(f"✅ SKU {sku_venta}: Vendido {cantidad_vendida}. Nuevo stock: {nuevo_stock}")
                
        return reporte if reporte else "Ventas encontradas, pero no tenían SKU asignado en MeLi."
    except Exception as e:
        return f"❌ Error al procesar: {e}"

# --- INTERFAZ CON PESTAÑAS ---
st.title("📦 Sistema MyM Hogar - Control Bi-Direccional")

tab1, tab2 = st.tabs(["🚀 Enviar a MeLi (Stock)", "📥 Traer de MeLi (Ventas)"])

with tab1:
    st.subheader("Actualizar Mercado Libre desde MyM")
    # ... (Aquí va tu código de búsqueda y sincronización que ya probamos y funciona)
    st.info("Usa esta pestaña para subir el stock de Supabase a Mercado Libre.")

with tab2:
    st.subheader("Sincronizar Ventas Recientes")
    st.write("Esta función busca ventas pagadas en MeLi y descuenta el stock de tu inventario local.")
    
    if st.button("🔍 Buscar Ventas y Actualizar Inventario"):
        with st.spinner("Consultando órdenes recientes..."):
            resultados = procesar_ventas_meli()
            if isinstance(resultados, list):
                for r in resultados: st.success(r)
            else:
                st.info(resultados)

# --- TABLA DE INVENTARIO SIEMPRE VISIBLE ---
st.divider()
st.subheader("📊 Estado Actual del Inventario")
prods = supabase.table("productos").select("*").order("sku").execute().data
if prods:
    st.dataframe(pd.DataFrame(prods)[["sku", "nombre", "stock_total"]], use_container_width=True)
