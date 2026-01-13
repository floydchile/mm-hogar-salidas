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
    logo = None

st.set_page_config(page_title="M&M Hogar", page_icon="📦", layout="wide")

# Configurar Supabase desde variables de entorno
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://nijzonhfxyihpgozinge.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_KEY:
    st.error("Error: No hay configuración de base de datos")
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

if 'query_buscar' not in st.session_state:
    st.session_state.query_buscar = ""

# ============= FUNCIONES =============

def producto_existe(sku):
    try:
        response = supabase.table("productos").select("*").eq("sku", sku.upper()).execute()
        return len(response.data) > 0
    except:
        return False

def cargar_productos_sin_cache():
    """Carga productos SIN CACHE para búsqueda en tiempo real"""
    try:
        response = supabase.table("productos").select("*").order("creado_en", desc=True).execute()
        return response.data if response.data else []
    except:
        return []

def crear_producto(sku, nombre, und_x_embalaje):
    try:
        supabase.table("productos").insert({
            "sku": sku.upper(),
            "nombre": nombre,
            "und_x_embalaje": int(und_x_embalaje),
            "stock_total": 0,
            "creado_en": datetime.now().isoformat(),
            "actualizado_en": datetime.now().isoformat()
        }).execute()
        return True, "Producto creado exitosamente"
    except Exception as e:
        return False, f"Error: {str(e)}"

def agregar_stock(sku, cantidad, und_x_embalaje):
    try:
        response = supabase.table("productos").select("stock_total").eq("sku", sku.upper()).execute()
        stock_actual = response.data[0]["stock_total"] if response.data else 0
        nuevo_stock = stock_actual + cantidad
        
        supabase.table("productos").update({
            "stock_total": nuevo_stock,
            "actualizado_en": datetime.now().isoformat()
        }).eq("sku", sku.upper()).execute()
        
        supabase.table("entradas").insert({
            "sku": sku.upper(),
            "cantidad": int(cantidad),
            "und_x_embalaje": int(und_x_embalaje),
            "usuario": st.session_state.usuario,
            "fecha": datetime.now().isoformat()
        }).execute()
        
        return True, f"Stock actualizado: +{cantidad} UND"
    except Exception as e:
        return False, f"Error: {str(e)}"

def cargar_salidas():
    try:
        response = supabase.table("salidas").select("*").order("fecha", desc=True).execute()
        return response.data if response.data else []
    except:
        return []

def agregar_salida(sku, cantidad, canal, usuario):
    try:
        response = supabase.table("productos").select("stock_total").eq("sku", sku.upper()).execute()
        stock_actual = response.data[0]["stock_total"] if response.data else 0
        
        if stock_actual < cantidad:
            return False, f"Stock insuficiente. Disponible: {stock_actual}"
        
        nuevo_stock = stock_actual - cantidad
        
        supabase.table("productos").update({
            "stock_total": nuevo_stock,
            "actualizado_en": datetime.now().isoformat()
        }).eq("sku", sku.upper()).execute()
        
        supabase.table("salidas").insert({
            "sku": sku.upper(),
            "cantidad": int(cantidad),
            "canal": canal,
            "usuario": usuario,
            "fecha": datetime.now().isoformat()
        }).execute()
        
        return True, "Venta registrada"
    except Exception as e:
        return False, f"Error: {str(e)}"

def cargar_entradas():
    try:
        response = supabase.table("entradas").select("*").order("fecha", desc=True).execute()
        return response.data if response.data else []
    except:
        return []

# ============= SIDEBAR =============

with st.sidebar:
    st.markdown("### Usuario")
    usuario = st.text_input("Ingresa tu nombre:", placeholder="Tu nombre aqui")
    
    if usuario:
        st.session_state.usuario = usuario
        st.success(f"Bienvenido {usuario}!")

# ============= HEADER =============

col1, col2 = st.columns([1, 4])

with col1:
    if logo:
        st.image(logo, width=70)
    else:
        st.markdown("📦")

with col2:
    st.markdown("### M&M Hogar")
    st.markdown("**Sistema de Inventario y Salidas**")

st.divider()

# ============= TABS =============

tab1, tab2, tab3, tab4, tab5 = st.tabs(["Inventario", "Registrar Venta", "Historial Ventas", "Historial Entradas", "Stock"])

# ============= TAB 1: INVENTARIO =============

with tab1:
    st.subheader("Gestion de Inventario")
    
    # Callback para actualizar búsqueda en tiempo real
    def actualizar_buscar():
        st.session_state.query_buscar = st.session_state.buscador_input
    
    # Buscador con callback - sin key para forzar re-render
    query_input = st.text_input("Buscar SKU o nombre:", 
                 placeholder="Escribe SKU o parte del nombre...", 
                 key="buscador_input",
                 on_change=actualizar_buscar)
    
    # Cargar productos SIN CACHE para búsqueda en tiempo real
    productos = cargar_productos_sin_cache()
    
    # Filtrar productos usando la búsqueda actual
    query_buscar = st.session_state.query_buscar
    if query_buscar:
        productos_filtrados = [p for p in productos if query_buscar.upper() in p["sku"].upper() or query_buscar.lower() in p["nombre"].lower()]
    else:
        productos_filtrados = []
    
    # Mostrar resultados EN TIEMPO REAL
    if query_buscar:
        if productos_filtrados:
            st.markdown(f"**✅ {len(productos_filtrados)} resultado(s) encontrado(s):**")
            for p in productos_filtrados[:10]:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{p['sku']}** - {p['nombre']}")
                with col2:
                    st.caption(f"Stock: {p.get('stock_total', 0)}")
                
                if st.button(f"Seleccionar {p['sku']}", key=f"sel_{p['sku']}", use_container_width=True):
                    st.session_state.sku_seleccionado = p['sku']
                    st.session_state.nombre_seleccionado = p['nombre']
                    st.session_state.und_seleccionado = p.get('und_x_embalaje', 1)
                    st.session_state.stock_actual_seleccionado = p.get('stock_total', 0)
                    st.session_state.buscador_input = ""
                    st.session_state.query_buscar = ""
                    st.success(f"Seleccionado: {p['sku']}")
                    st.rerun()
        else:
            st.warning("❌ Producto no encontrado. Puedes agregarlo en el formulario de abajo como nuevo producto.")
    
    st.divider()
    
    # Formulario principal
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sku = st.text_input("SKU", value=st.session_state.get('sku_seleccionado', ''), placeholder="BS-001", key="sku_input").upper()
    
    with col2:
        nombre = st.text_input("Nombre del Producto", value=st.session_state.get('nombre_seleccionado', ''), placeholder="Babysec Premium P - 20 UND", key="nombre_input")
    
    # Determinar si el producto existe
    producto_existe_ahora = producto_existe(sku) if sku else False
    
    with col3:
        und_x_embalaje = st.number_input("UND x Embalaje", min_value=1, value=st.session_state.get('und_seleccionado', 1), key="und_input", disabled=producto_existe_ahora)
    
    # Stock actual y cantidad a agregar
    col1_stock, col2_stock = st.columns(2)
    
    with col1_stock:
        st.number_input("Stock Actual", min_value=0, value=st.session_state.get('stock_actual_seleccionado', 0), key="stock_actual_input")
    
    with col2_stock:
        cantidad = st.number_input("Cantidad a Agregar", min_value=1, value=1, key="cantidad_input")
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("Agregar/Actualizar Producto", use_container_width=True, type="primary"):
            if not sku or not nombre:
                st.error("SKU y Nombre son obligatorios")
            else:
                existe = producto_existe(sku)
                if existe:
                    success, msg = agregar_stock(sku, cantidad, und_x_embalaje)
                    if success:
                        st.success(msg)
                        # Limpiar sesion y formulario
                        for key in ['sku_seleccionado', 'nombre_seleccionado', 'und_seleccionado', 'stock_actual_seleccionado']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    success, msg = crear_producto(sku, nombre, und_x_embalaje)
                    if success:
                        agregar_stock(sku, cantidad, und_x_embalaje)
                        st.success(f"{msg} - Stock inicial: {cantidad} UND")
                        # Limpiar sesion y formulario
                        for key in ['sku_seleccionado', 'nombre_seleccionado', 'und_seleccionado', 'stock_actual_seleccionado']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()
                    else:
                        st.error(msg)
    
    with col_btn2:
        if st.button("Limpiar", use_container_width=True):
            for key in ['sku_seleccionado', 'nombre_seleccionado', 'und_seleccionado', 'stock_actual_seleccionado']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    st.divider()
    
    # Tabla de productos
    productos = cargar_productos_sin_cache()
    
    if productos:
        st.info(f"Total productos: **{len(productos)}**")
        df_productos = pd.DataFrame([
            {
                "SKU": p["sku"],
                "Nombre": p["nombre"],
                "UND x Emb": p.get("und_x_embalaje", 1),
                "Stock Total": p.get("stock_total", 0),
                "Ultima Actualizacion": p.get("actualizado_en", "")[:10] if p.get("actualizado_en") else "N/A"
            }
            for p in productos
        ])
        st.dataframe(df_productos, use_container_width=True, hide_index=True)
    else:
        st.info("No hay productos registrados")

# ============= TAB 2: REGISTRAR VENTA =============

with tab2:
    st.subheader("Registrar Venta")
    productos = cargar_productos_sin_cache()
    
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
        
        if st.button("Guardar Venta", use_container_width=True, type="primary"):
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
                st.warning("Ingresa tu nombre en la barra lateral primero")
    else:
        st.warning("Agrega productos primero en la pestana 'Inventario'")

# ============= TAB 3: HISTORIAL VENTAS =============

with tab3:
    st.subheader("Historial de Ventas")
    salidas = cargar_salidas()
    
    if salidas:
        st.info(f"Total ventas: **{len(salidas)}**")
        df_salidas = pd.DataFrame([
            {
                "Fecha": v["fecha"][:10],
                "SKU": v["sku"],
                "Cantidad": v["cantidad"],
                "Canal": v["canal"],
                "Usuario": v["usuario"]
            }
            for v in salidas
        ])
        st.dataframe(df_salidas, use_container_width=True, hide_index=True)
        
        st.divider()
        
        csv_data = df_salidas.to_csv(index=False)
        st.download_button(
            "Descargar CSV",
            csv_data,
            file_name=f"ventas_{datetime.now().strftime('%Y%m%d')}.csv",
            use_container_width=True
        )
    else:
        st.info("Sin ventas registradas")

# ============= TAB 4: HISTORIAL ENTRADAS =============

with tab4:
    st.subheader("Historial de Entradas de Stock")
    entradas = cargar_entradas()
    
    if entradas:
        st.info(f"Total ingresos: **{len(entradas)}**")
        df_entradas = pd.DataFrame([
            {
                "Fecha": e["fecha"][:10],
                "SKU": e["sku"],
                "Cantidad": e["cantidad"],
                "UND x Emb": e.get("und_x_embalaje", 1),
                "Usuario": e.get("usuario", "Sistema")
            }
            for e in entradas
        ])
        st.dataframe(df_entradas, use_container_width=True, hide_index=True)
        
        st.divider()
        
        csv_data = df_entradas.to_csv(index=False)
        st.download_button(
            "Descargar CSV",
            csv_data,
            file_name=f"entradas_{datetime.now().strftime('%Y%m%d')}.csv",
            use_container_width=True
        )
    else:
        st.info("Sin ingresos registrados")

# ============= TAB 5: RESUMEN DE STOCK =============

with tab5:
    st.subheader("Resumen de Stock Actual")
    productos = cargar_productos_sin_cache()
    
    if productos:
        total_productos = len(productos)
        stock_total = sum(p.get("stock_total", 0) for p in productos)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Productos", total_productos)
        
        with col2:
            st.metric("Stock Total (UND)", stock_total)
        
        with col3:
            productos_sin_stock = len([p for p in productos if p.get("stock_total", 0) == 0])
            st.metric("Sin Stock", productos_sin_stock)
        
        st.divider()
        
        df_stock = pd.DataFrame([
            {
                "SKU": p["sku"],
                "Nombre": p["nombre"],
                "Stock": p.get("stock_total", 0),
                "UND x Emb": p.get("und_x_embalaje", 1),
                "Estado": "OK" if p.get("stock_total", 0) > 0 else "SIN STOCK"
            }
            for p in productos
        ])
        st.dataframe(df_stock, use_container_width=True, hide_index=True)
        
        st.divider()
        
        csv_data = df_stock.to_csv(index=False)
        st.download_button(
            "Descargar CSV",
            csv_data,
            file_name=f"stock_{datetime.now().strftime('%Y%m%d')}.csv",
            use_container_width=True
        )
    else:
        st.info("No hay productos registrados")
