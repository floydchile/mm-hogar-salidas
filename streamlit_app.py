import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os

st.set_page_config(page_title="M&M Hogar", page_icon="📦", layout="wide")

# Configurar Supabase desde variables de entorno
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://nijzonhfxyihpgozinge.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_KEY:
    st.error("⚠️ Error: No hay configuración de base de datos")
    st.stop()

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase: Client = init_supabase()
except Exception as e:
    st.error(f"Error conectando a base de datos: {str(e)}")
    st.stop()


if 'usuario' not in st.session_state:
    st.session_state.usuario = None

def cargar_productos():
    try:
        response = supabase.table('productos').select('*').execute()
        return response.data if response.data else []
    except:
        return []

def cargar_salidas():
    try:
        response = supabase.table('salidas').select('*').execute()
        return response.data if response.data else []
    except:
        return []

def agregar_producto(sku, nombre):
    try:
        supabase.table('productos').insert({
            'sku': sku,
            'nombre': nombre,
            'creado_en': datetime.now().isoformat()
        }).execute()
        return True
    except:
        return False

def agregar_salida(sku, cantidad, canal, usuario):
    try:
        supabase.table('salidas').insert({
            'sku': sku,
            'cantidad': int(cantidad),
            'canal': canal,
            'usuario': usuario,
            'fecha': datetime.now().isoformat()
        }).execute()
        return True
    except:
        return False

# Sidebar con usuario
with st.sidebar:
    st.markdown("### 👤 Usuario")
    usuario = st.text_input("Ingresa tu nombre:", placeholder="Tu nombre aquí")
    if usuario:
        st.session_state.usuario = usuario
        st.success(f"✅ Bienvenido {usuario}!")

# Título responsive
col1, col2 = st.columns([3, 1])
with col1:
    st.markdown("# 📦 M&M Hogar")
    st.markdown("**Sistema de Salidas**")
with col2:
    st.write("")

st.markdown("Sistema de registro de ventas con base de datos")
st.divider()

# Tabs
tab1, tab2, tab3 = st.tabs(["📦 Productos", "📤 Registrar Venta", "📊 Historial"])

with tab1:
    st.subheader("Gestión de Productos")
    
    col1, col2 = st.columns(2)
    with col1:
        sku = st.text_input("SKU", placeholder="BS-001")
    with col2:
        nombre = st.text_input("Nombre del Producto", placeholder="Babysec Premium")
    
    if st.button("✅ Agregar Producto", use_container_width=True):
        if sku and nombre:
            if agregar_producto(sku, nombre):
                st.success("✅ Producto agregado correctamente")
                st.rerun()
            else:
                st.error("❌ Error al agregar el producto")
        else:
            st.warning("⚠️ Completa todos los campos")
    
    st.divider()
    productos = cargar_productos()
    st.info(f"📊 Total productos: **{len(productos)}**")
    
    if productos:
        for p in productos:
            st.write(f"• **{p['sku']}** - {p['nombre']}")
    else:
        st.write("Sin productos registrados")

with tab2:
    st.subheader("Registrar Venta")
    productos = cargar_productos()
    
    if productos:
        opciones = [f"{p['sku']} - {p['nombre']}" for p in productos]
        
        col1, col2 = st.columns(2)
        with col1:
            producto_sel = st.selectbox("Selecciona Producto:", opciones, key="producto")
        with col2:
            cantidad = st.number_input("Cantidad:", min_value=1, value=1)
        
        canal = st.selectbox("Canal de Venta:", ["Mercadolibre", "Falabella", "Walmart", "Hites", "Paris", "Ripley", "Directo - Web", "Directo - WS", "Directo - Retilo"])
        
        if st.button("💾 Guardar Venta", use_container_width=True, type="primary"):
            if st.session_state.usuario:
                sku = producto_sel.split(" - ")[0]
                if agregar_salida(sku, cantidad, canal, st.session_state.usuario):
                    st.success(f"✅ Venta registrada por {st.session_state.usuario}")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("❌ Error al registrar la venta")
            else:
                st.warning("⚠️ Ingresa tu nombre en la barra lateral primero")
    else:
        st.warning("⚠️ Agrega productos primero en la pestaña 'Productos'")

with tab3:
    st.subheader("Historial de Ventas")
    salidas = cargar_salidas()
    
    st.info(f"📊 Total ventas: **{len(salidas)}**")
    
    if salidas:
        st.divider()
        for venta in reversed(salidas):
            st.write(f"📅 **{venta['fecha'][:10]}** | 📦 {venta['sku']} x{venta['cantidad']} | 🏪 {venta['canal']} | 👤 {venta['usuario']}")
        
        st.divider()
        csv_data = "fecha,sku,cantidad,canal,usuario\n"
        for venta in salidas:
            csv_data += f"{venta['fecha']},{venta['sku']},{venta['cantidad']},{venta['canal']},{venta['usuario']}\n"
        
        st.download_button(
            "📥 Descargar CSV",
            csv_data,
            file_name=f"salidas_{datetime.now().strftime('%Y%m%d')}.csv",
            use_container_width=True
        )
    else:
        st.write("Sin ventas registradas")
