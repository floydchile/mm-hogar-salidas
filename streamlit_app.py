import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import os
import pandas as pd
from PIL import Image

# Configurar página
st.set_page_config(page_title="M&M Hogar", page_icon="📦", layout="wide", initial_sidebar_state="collapsed")

# Logo
try:
    logo = Image.open("assets/mym_hogar.png")
except:
    logo = None

# Configurar Supabase
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

# ============= CREDENCIALES (DESDE RAILWAY - VARIABLES PRIVADAS) =============
USUARIOS_AUTORIZADOS = {
    "dany": os.getenv("PASS_DANY", "dany123"),
    "pau": os.getenv("PASS_PAU", "pau123"),
    "miguel": os.getenv("PASS_MIGUEL", "miguel123")
}

# ============= FUNCIONES DE AUTENTICACIÓN =============

def verificar_credenciales(usuario, contraseña):
    """Verifica usuario y contraseña"""
    return usuario in USUARIOS_AUTORIZADOS and USUARIOS_AUTORIZADOS[usuario] == contraseña

def crear_token_sesion(usuario):
    """Crea un token de sesión con expiración 24h"""
    return {
        "usuario": usuario,
        "timestamp": datetime.now(),
        "expiracion": datetime.now() + timedelta(hours=24)
    }

def sesion_activa():
    """Verifica si la sesión sigue siendo válida"""
    if 'sesion' not in st.session_state or st.session_state.sesion is None:
        return False
    
    sesion = st.session_state.sesion
    if datetime.now() > sesion['expiracion']:
        del st.session_state.sesion
        return False
    
    return True

# ============= INICIALIZAR SESSION STATE =============

if 'sesion' not in st.session_state:
    st.session_state.sesion = None

if 'selected_tab' not in st.session_state:
    st.session_state.selected_tab = 0

# ============= FUNCIONES DE NEGOCIO =============

def producto_existe(sku):
    try:
        response = supabase.table("productos").select("*").eq("sku", sku.upper()).execute()
        return len(response.data) > 0
    except:
        return False

def cargar_productos():
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

def agregar_stock(sku, cantidad, und_x_embalaje, usuario):
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
            "usuario": usuario,
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

# ============= PANTALLA DE LOGIN =============

if not sesion_activa():
    try:
        epitafio_guardia = Image.open("assets/epitafio_guardia.png")
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.image(epitafio_guardia, width=200)
    except:
        st.markdown("<div style='text-align: center;'><h1 style='font-size: 4rem;'>👮</h1></div>", unsafe_allow_html=True)
    
    st.markdown("<div style='text-align: center;'><h1>M&M Hogar</h1></div>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center;'><p>Sistema de Inventario - Acceso Restringido</p></div>", unsafe_allow_html=True)
    
    st.divider()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Inicia Sesión")
        
        usuario_input = st.text_input("👤 Usuario:", placeholder="Ingresa tu usuario")
        contraseña_input = st.text_input("🔑 Contraseña:", type="password", placeholder="Tu contraseña")
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("✅ Ingresar", use_container_width=True, type="primary"):
                if verificar_credenciales(usuario_input, contraseña_input):
                    st.session_state.sesion = crear_token_sesion(usuario_input)
                    st.success(f"✅ ¡Bienvenido {usuario_input}!")
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
        
        with col_btn2:
            if st.button("🗑️ Limpiar", use_container_width=True):
                st.rerun()
    
    st.stop()

# ============= SESIÓN ACTIVA - MOSTRAR APLICACIÓN =============

usuario_logueado = st.session_state.sesion['usuario']

# ============= HEADER ULTRA COMPACTO =============

col1, col2, col3 = st.columns([0.2, 2.5, 0.3])

with col1:
    if logo:
        st.image(logo, width=35)
    else:
        st.markdown("📦")

with col2:
    st.markdown("<h3 style='margin: 0; padding: 0;'>M&M Hogar</h3>", unsafe_allow_html=True)

with col3:
    if st.button("🚪 Salir", use_container_width=True):
        del st.session_state.sesion
        st.rerun()

st.divider()

# ============= BARRA DE USUARIO =============

st.markdown(f"<p style='text-align: center; color: #666;'>👤 Sesión activa: <b>{usuario_logueado}</b> | ⏰ Válida por 24h</p>", unsafe_allow_html=True)

st.divider()

# ============= NAVEGACIÓN =============

tab_names = ["📦 Inventario", "💳 Venta", "📊 Ventas", "📥 Entradas", "📈 Stock"]

selected_tab = st.selectbox(
    "Selecciona sección:",
    range(5),
    format_func=lambda x: tab_names[x],
    index=st.session_state.selected_tab,
    key="nav_selectbox",
    label_visibility="collapsed"
)
st.session_state.selected_tab = selected_tab

st.divider()

# ============= CONTENIDO DE PESTAÑAS =============

# TAB 0: INVENTARIO
if selected_tab == 0:
    st.subheader("📦 Gestión de Inventario")
    
    productos = cargar_productos()
    
    query = st.text_input("🔍 Buscar SKU o nombre:", 
                         placeholder="Escribe SKU o parte del nombre...", 
                         key="buscador_simple")
    
    if query:
        productos_filtrados = [p for p in productos if query.upper() in p["sku"].upper() or query.lower() in p["nombre"].lower()]
    else:
        productos_filtrados = []
    
    if query:
        if productos_filtrados:
            st.markdown(f"### ✅ {len(productos_filtrados)} resultado(s)")
            
            for idx, p in enumerate(productos_filtrados[:10]):
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.markdown(f"**SKU:** {p['sku']}")
                        st.markdown(f"**Producto:** {p['nombre']}")
                    
                    with col2:
                        st.metric("Stock", p.get('stock_total', 0))
                    
                    with col3:
                        if st.button("✅ Usar", key=f"btn_usar_{p['sku']}", use_container_width=True):
                            st.session_state.sku_seleccionado = p['sku']
                            st.session_state.nombre_seleccionado = p['nombre']
                            st.session_state.und_seleccionado = p.get('und_x_embalaje', 1)
                            st.session_state.stock_actual_seleccionado = p.get('stock_total', 0)
                            st.rerun()
        else:
            st.warning(f"❌ No hay productos que coincidan con '{query}'")
    
    st.divider()
    
    st.subheader("📝 Agregar o Actualizar")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sku = st.text_input("SKU", value=st.session_state.get('sku_seleccionado', ''), placeholder="BS-001", key="sku_input").upper()
    
    with col2:
        nombre = st.text_input("Nombre", value=st.session_state.get('nombre_seleccionado', ''), placeholder="Producto...", key="nombre_input")
    
    producto_existe_ahora = producto_existe(sku) if sku else False
    
    with col3:
        und_x_embalaje = st.number_input("UND x Emb", min_value=1, value=st.session_state.get('und_seleccionado', 1), key="und_input", disabled=producto_existe_ahora)
    
    col1_stock, col2_stock = st.columns(2)
    
    with col1_stock:
        st.number_input("Stock Actual", min_value=0, value=st.session_state.get('stock_actual_seleccionado', 0), key="stock_actual_input")
    
    with col2_stock:
        cantidad = st.number_input("Cantidad", min_value=1, value=1, key="cantidad_input")
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("💾 Guardar", use_container_width=True, type="primary"):
            if not sku or not nombre:
                st.error("SKU y Nombre obligatorios")
            else:
                existe = producto_existe(sku)
                if existe:
                    success, msg = agregar_stock(sku, cantidad, und_x_embalaje, usuario_logueado)
                    if success:
                        st.success(msg)
                        for key in ['sku_seleccionado', 'nombre_seleccionado', 'und_seleccionado', 'stock_actual_seleccionado']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    success, msg = crear_producto(sku, nombre, und_x_embalaje)
                    if success:
                        agregar_stock(sku, cantidad, und_x_embalaje, usuario_logueado)
                        st.success(f"{msg} ✅")
                        for key in ['sku_seleccionado', 'nombre_seleccionado', 'und_seleccionado', 'stock_actual_seleccionado']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()
                    else:
                        st.error(msg)
    
    with col_btn2:
        if st.button("🗑️ Limpiar", use_container_width=True):
            for key in ['sku_seleccionado', 'nombre_seleccionado', 'und_seleccionado', 'stock_actual_seleccionado']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    st.divider()
    
    st.subheader("📊 Todos los Productos")
    
    if productos:
        st.info(f"Total: **{len(productos)}** productos")
        df_productos = pd.DataFrame([
            {
                "SKU": p["sku"],
                "Nombre": p["nombre"],
                "UND x Emb": p.get("und_x_embalaje", 1),
                "Stock": p.get("stock_total", 0),
                "Actualizado": p.get("actualizado_en", "")[:10] if p.get("actualizado_en") else "N/A"
            }
            for p in productos
        ])
        st.dataframe(df_productos, use_container_width=True, hide_index=True)
    else:
        st.info("No hay productos")

# TAB 1: REGISTRAR VENTA
elif selected_tab == 1:
    st.subheader("💳 Registrar Venta")
    productos = cargar_productos()
    
    if productos:
        opciones = [f"{p['sku']} - {p['nombre']}" for p in productos]
        
        col1, col2 = st.columns(2)
        
        with col1:
            producto_sel = st.selectbox("Producto:", opciones, key="producto_venta")
        
        with col2:
            cantidad_venta = st.number_input("Cantidad:", min_value=1, value=1, key="cantidad_venta")
        
        canal = st.selectbox("Canal:",
            ["Mercadolibre", "Falabella", "Walmart", "Hites", "Paris", "Ripley",
             "Directo - Web", "Directo - WhatsApp", "Directo - Retiro"],
            key="canal_venta")
        
        if st.button("✅ Guardar Venta", use_container_width=True, type="primary"):
            sku = producto_sel.split(" - ")[0]
            success, msg = agregar_salida(sku, cantidad_venta, canal, usuario_logueado)
            if success:
                st.success(msg)
                st.balloons()
                st.rerun()
            else:
                st.error(msg)
    else:
        st.warning("Agrega productos primero")

# TAB 2: HISTORIAL VENTAS
elif selected_tab == 2:
    st.subheader("📊 Historial de Ventas")
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
            "📥 Descargar CSV",
            csv_data,
            file_name=f"ventas_{datetime.now().strftime('%Y%m%d')}.csv",
            use_container_width=True
        )
    else:
        st.info("Sin ventas registradas")

# TAB 3: HISTORIAL ENTRADAS
elif selected_tab == 3:
    st.subheader("📥 Historial de Entradas")
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
            "📥 Descargar CSV",
            csv_data,
            file_name=f"entradas_{datetime.now().strftime('%Y%m%d')}.csv",
            use_container_width=True
        )
    else:
        st.info("Sin ingresos registrados")

# TAB 4: CONSULTA DE STOCK
elif selected_tab == 4:
    st.subheader("📦 Consultar Stock")
    
    productos = cargar_productos()
    
    # Buscador
    query_stock = st.text_input("🔍 Buscar producto (SKU o nombre):", 
                               placeholder="Escribe SKU o parte del nombre...", 
                               key="buscador_stock")
    
    if query_stock:
        productos_filtrados = [p for p in productos if query_stock.upper() in p["sku"].upper() or query_stock.lower() in p["nombre"].lower()]
    else:
        productos_filtrados = []
    
    # Mostrar resultados
    if query_stock:
        if productos_filtrados:
            st.markdown(f"### ✅ {len(productos_filtrados)} resultado(s)")
            
            # Tabla compacta con solo SKU, Nombre y Stock
            df_resultados = pd.DataFrame([
                {
                    "SKU": p["sku"],
                    "Nombre": p["nombre"],
                    "Stock": p.get("stock_total", 0)
                }
                for p in productos_filtrados
            ])
            st.dataframe(df_resultados, use_container_width=True, hide_index=True)
        else:
            st.warning(f"❌ No hay productos que coincidan con '{query_stock}'")
    else:
        st.info("🔎 Usa el buscador arriba para consultar el stock de tus productos")
