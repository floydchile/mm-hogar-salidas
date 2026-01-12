import streamlit as st
from supabase import create_client, Client
from datetime import datetime

st.set_page_config(page_title="M&M Hogar", page_icon="📦", layout="wide")

# Configurar Supabase
SUPABASE_URL = "https://nijzonhfxyihpgozinge.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5pamp6b25oZnh5aWhwZ296aW5nZSIsInJvbGUiOiJhbm9uIiwiaWF0IjoxNzAyNDAwMDAwLCJleHAiOjE3MzM5MzYwMDB9.DUMMY"

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    supabase: Client = init_supabase()
except:
    st.error("Error conectando a base de datos")
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

with st.sidebar:
    st.title("👤 Usuario")
    usuario = st.text_input("Tu nombre:")
    if usuario:
        st.session_state.usuario = usuario
        st.success(f"¡Bienvenido {usuario}!")

st.title("📦 M&M Hogar - Sistema de Salidas")
st.write("Sistema de registro de ventas con base de datos")

tab1, tab2, tab3 = st.tabs(["Productos", "Registrar Venta", "Historial"])

with tab1:
    st.header("Gestión de Productos")
    sku = st.text_input("SKU", placeholder="BS-001")
    nombre = st.text_input("Nombre", placeholder="Babysec Premium")
    
    if st.button("Agregar Producto"):
        if sku and nombre:
            if agregar_producto(sku, nombre):
                st.success("✅ Producto agregado")
                st.rerun()
            else:
                st.error("Error al agregar")
        else:
            st.warning("Completa todos los campos")
    
    productos = cargar_productos()
    st.write(f"**Total productos: {len(productos)}**")
    for p in productos:
        st.write(f"- {p['sku']}: {p['nombre']}")

with tab2:
    st.header("Registrar Venta")
    productos = cargar_productos()
    
    if productos:
        opciones = [f"{p['sku']} - {p['nombre']}" for p in productos]
        producto_sel = st.selectbox("Producto:", opciones)
        cantidad = st.number_input("Cantidad:", min_value=1, value=1)
        canal = st.selectbox("Canal:", ["Mercadolibre", "Falabella", "Walmart", "Hites", "Paris", "Ripley", "Directo - Web", "Directo - WS", "Directo - Retiro"])
        
        if st.button("Guardar Venta"):
            if st.session_state.usuario:
                sku = producto_sel.split(" - ")[0]
                if agregar_salida(sku, cantidad, canal, st.session_state.usuario):
                    st.success(f"✅ Venta registrada")
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Error al registrar")
            else:
                st.warning("Ingresa tu nombre primero")
    else:
        st.warning("Agrega productos primero")

with tab3:
    st.header("Historial de Ventas")
    salidas = cargar_salidas()
    
    st.write(f"**Total ventas: {len(salidas)}**")
    
    if salidas:
        for venta in reversed(salidas):
            st.write(f"**{venta['fecha'][:10]}** | {venta['sku']} x{venta['cantidad']} | {venta['canal']} | {venta['usuario']}")
        
        csv_data = "fecha,sku,cantidad,canal,usuario\n"
        for venta in salidas:
            csv_data += f"{venta['fecha']},{venta['sku']},{venta['cantidad']},{venta['canal']},{venta['usuario']}\n"
        
        st.download_button(
            "📥 Descargar CSV",
            csv_data,
            file_name=f"salidas_{datetime.now().strftime('%Y%m%d')}.csv"
        )
    else:
        st.write("Sin ventas registradas")
