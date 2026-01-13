import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os
import pandas as pd

from PIL import Image

logo = Image.open("assets/mym_hogar.png")
st.set_page_config(page_title="M&M Hogar", page_icon=logo, layout="wide")


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

# ============= FUNCIONES PRODUCTOS =============

def producto_existe(sku):
    """Verifica si un producto existe"""
    try:
        response = supabase.table('productos').select('*').eq('sku', sku).execute()
        return len(response.data) > 0
    except:
        return False

def cargar_productos():
    """Carga todos los productos"""
    try:
        response = supabase.table('productos').select('*').order('creado_en', desc=True).execute()
        return response.data if response.data else []
    except:
        return []

def crear_producto(sku, nombre, und_x_embalaje):
    """Crea un nuevo producto"""
    try:
        supabase.table('productos').insert({
            'sku': sku,
            'nombre': nombre,
            'und_x_embalaje': int(und_x_embalaje),
            'stock_total': 0,
            'creado_en': datetime.now().isoformat(),
            'actualizado_en': datetime.now().isoformat()
        }).execute()
        return True, "✅ Producto creado exitosamente"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def agregar_stock(sku, cantidad, und_x_embalaje):
    """Agrega stock a un producto existente"""
    try:
        # Actualizar stock en productos
        response = supabase.table('productos').select('stock_total').eq('sku', sku).execute()
        stock_actual = response.data[0]['stock_total'] if response.data else 0
        nuevo_stock = stock_actual + cantidad
        
        supabase.table('productos').update({
            'stock_total': nuevo_stock,
            'actualizado_en': datetime.now().isoformat()
        }).eq('sku', sku).execute()
        
        # Registrar en tabla entradas
        supabase.table('entradas').insert({
            'sku': sku,
            'cantidad': int(cantidad),
            'und_x_embalaje': int(und_x_embalaje),
            'usuario': st.session_state.usuario,
            'fecha': datetime.now().isoformat()
        }).execute()
        
        return True, f"⬆️ Stock actualizado: +{cantidad} UND"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def cargar_salidas():
    """Carga todas las salidas (ventas)"""
    try:
        response = supabase.table('salidas').select('*').order('fecha', desc=True).execute()
        return response.data if response.data else []
    except:
        return []

def agregar_salida(sku, cantidad, canal, usuario):
    """Registra una venta"""
    try:
        # Obtener stock actual
        response = supabase.table('productos').select('stock_total').eq('sku', sku).execute()
        stock_actual = response.data[0]['stock_total'] if response.data else 0
        
        if stock_actual < cantidad:
            return False, f"❌ Stock insuficiente. Disponible: {stock_actual}"
        
        # Descontar del stock
        nuevo_stock = stock_actual - cantidad
        supabase.table('productos').update({
            'stock_total': nuevo_stock,
            'actualizado_en': datetime.now().isoformat()
        }).eq('sku', sku).execute()
        
        # Registrar salida
        supabase.table('salidas').insert({
            'sku': sku,
            'cantidad': int(cantidad),
            'canal': canal,
            'usuario': usuario,
            'fecha': datetime.now().isoformat()
        }).execute()
        
        return True, f"✅ Venta registrada"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def cargar_entradas():
    """Carga todos los ingresos de stock"""
    try:
        response = supabase.table('entradas').select('*').order('fecha', desc=True).execute()
        return response.data if response.data else []
    except:
        return []

# ============= SIDEBAR =============

with st.sidebar:
    st.markdown("### 👤 Usuario")
    usuario = st.text_input("Ingresa tu nombre:", placeholder="Tu nombre aquí")
    if usuario:
        st.session_state.usuario = usuario
        st.success(f"✅ Bienvenido {usuario}!")

# ============= HEADER =============

col1, col2 = st.columns([1, 4])
with col1:
    st.image(logo, width=70)
with col2:
    st.markdown("### M&M Hogar")
    st.markdown("**Sistema de Inventario y Salidas By Epi**")

with col2:
    st.write("")

st.divider()

# ============= TABS =============

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📦 Inventario", "📤 Registrar Venta", "📊 Historial Ventas", "📥 Historial Entradas", "💾 Stock"])

# ============= TAB 1: INVENTARIO (GESTIÓN DE PRODUCTOS) =============

with tab1:
    st.subheader("Gestión de Inventario")
    
    # Buscador en tiempo real
    query = st.text_input("🔍 Buscar SKU o nombre:", placeholder="Escribe SKU o parte del nombre...", key="buscador")
    
    productos = cargar_productos()
    
    # Filtrar productos en tiempo real
    if query:
        productos_filtrados = [p for p in productos if query.upper() in p['sku'].upper() or query.lower() in p['nombre'].lower()]
    else:
        productos_filtrados = []
    
    # Mostrar resultados del buscador
    if query and productos_filtrados:
        st.markdown("**Resultados encontrados:**")
        for p in productos_filtrados[:10]:  # Máximo 10 resultados
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{p['sku']}** - {p['nombre']}")
            with col2:
                st.caption(f"Stock: {p.get('stock_total', 0)}")
            if st.button(f"📦 Seleccionar {p['sku']}", key=f"sel_{p['sku']}", use_container_width=True):
                # Auto-rellenar formulario
                st.session_state.sku_seleccionado = p['sku']
                st.session_state.nombre_seleccionado = p['nombre']
                st.session_state.und_seleccionado = p.get('und_x_embalaje', 1)
                st.success(f"✅ Seleccionado: {p['sku']}")
                st.rerun()
    
    st.divider()
    
    # Formulario principal
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sku = st.text_input("SKU", value=st.session_state.get('sku_seleccionado', ''), placeholder="BS-001", key="sku_input").upper()
    with col2:
        nombre = st.text_input("Nombre del Producto", value=st.session_state.get('nombre_seleccionado', ''), placeholder="Babysec Premium P - 20

# ============= TAB 2: REGISTRAR VENTA =============

with tab2:
    st.subheader("Registrar Venta")
    productos = cargar_productos()
    
    if productos:
        opciones = [f"{p['sku']} - {p['nombre']}" for p in productos]
        
        col1, col2 = st.columns(2)
        with col1:
            producto_sel = st.selectbox("Selecciona Producto:", opciones, key="producto_venta")
        with col2:
            cantidad_venta = st.number_input("Cantidad:", min_value=1, value=1, key="cantidad_venta")
        
        canal = st.selectbox("Canal de Venta:", 
            ["Mercadolibre", "Falabella", "Walmart", "Hites", "Paris", "Ripley", 
             "Directo - Web", "Directo - WhatsApp", "Directo - Retiro"], 
            key="canal_venta")
        
        if st.button("💾 Guardar Venta", use_container_width=True, type="primary"):
            if st.session_state.usuario:
                sku = producto_sel.split(" - ")[0]
                success, msg = agregar_salida(sku, cantidad_venta, canal, st.session_state.usuario)
                if success:
                    st.success(msg)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("⚠️ Ingresa tu nombre en la barra lateral primero")
    else:
        st.warning("⚠️ Agrega productos primero en la pestaña 'Inventario'")

# ============= TAB 3: HISTORIAL VENTAS =============

with tab3:
    st.subheader("Historial de Ventas")
    salidas = cargar_salidas()
    
    if salidas:
        st.info(f"📊 Total ventas: **{len(salidas)}**")
        
        df_salidas = pd.DataFrame([
            {
                'Fecha': v['fecha'][:10],
                'SKU': v['sku'],
                'Cantidad': v['cantidad'],
                'Canal': v['canal'],
                'Usuario': v['usuario']
            }
            for v in salidas
        ])
        
        st.dataframe(df_salidas, use_container_width=True, hide_index=True)
        
        st.divider()
        csv_data = df_salidas.to_csv(index=False)
        st.download_button(
            "📥 Descargar CSV",
            csv_data,
            file_name=f"ventas_{datetime.now().strftime('%Y%m%d')}.csv",
            use_container_width=True
        )
    else:
        st.info("📭 Sin ventas registradas")

# ============= TAB 4: HISTORIAL ENTRADAS =============

with tab4:
    st.subheader("Historial de Entradas de Stock")
    entradas = cargar_entradas()
    
    if entradas:
        st.info(f"📊 Total ingresos: **{len(entradas)}**")
        
        df_entradas = pd.DataFrame([
            {
                'Fecha': e['fecha'][:10],
                'SKU': e['sku'],
                'Cantidad': e['cantidad'],
                'UND x Emb': e.get('und_x_embalaje', 1),
                'Usuario': e.get('usuario', 'Sistema')
            }
            for e in entradas
        ])
        
        st.dataframe(df_entradas, use_container_width=True, hide_index=True)
        
        st.divider()
        csv_data = df_entradas.to_csv(index=False)
        st.download_button(
            "📥 Descargar CSV",
            csv_data,
            file_name=f"entradas_{datetime.now().strftime('%Y%m%d')}.csv",
            use_container_width=True
        )
    else:
        st.info("📭 Sin ingresos registrados")

# ============= TAB 5: RESUMEN DE STOCK =============

with tab5:
    st.subheader("Resumen de Stock Actual")
    productos = cargar_productos()
    
    if productos:
        # Calcular totales
        total_productos = len(productos)
        stock_total = sum(p.get('stock_total', 0) for p in productos)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📦 Total Productos", total_productos)
        with col2:
            st.metric("📊 Stock Total (UND)", stock_total)
        with col3:
            productos_sin_stock = len([p for p in productos if p.get('stock_total', 0) == 0])
            st.metric("⚠️ Sin Stock", productos_sin_stock)
        
        st.divider()
        
        # Tabla de stock
        df_stock = pd.DataFrame([
            {
                'SKU': p['sku'],
                'Nombre': p['nombre'],
                'Stock': p.get('stock_total', 0),
                'UND x Emb': p.get('und_x_embalaje', 1),
                'Estado': '✅ OK' if p.get('stock_total', 0) > 0 else '⚠️ SIN STOCK'
            }
            for p in productos
        ])
        
        st.dataframe(df_stock, use_container_width=True, hide_index=True)
        
        st.divider()
        csv_data = df_stock.to_csv(index=False)
        st.download_button(
            "📥 Descargar CSV",
            csv_data,
            file_name=f"stock_{datetime.now().strftime('%Y%m%d')}.csv",
            use_container_width=True
        )
    else:
        st.info("📭 No hay productos registrados")




