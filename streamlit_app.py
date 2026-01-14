import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import os
import pandas as pd
from PIL import Image
import secrets
import re

# ============= CONFIGURAR PÁGINA PRIMERO =============
st.set_page_config(
    page_title="M&M Hogar",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============= ESTILOS CSS =============
st.markdown("""
    <style>
        .block-container {
            padding-top: 0.5rem;
            padding-bottom: 0rem;
        }
        .stMetric {
            background-color: transparent;
        }
        .success-box {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        .error-box {
            padding: 1rem;
            border-radius: 0.5rem;
            background-color: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
    </style>
""", unsafe_allow_html=True)

# ============= CARGAR LOGO =============
try:
    logo = Image.open("assets/mym_hogar.png")
except FileNotFoundError:
    logo = None

# ============= CONFIGURAR SUPABASE =============
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://nijzonhfxyihpgozinge.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_KEY:
    st.error("❌ Error: No hay configuración de base de datos (SUPABASE_KEY)")
    st.stop()

@st.cache_resource
def init_supabase():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"❌ Error inicializando Supabase: {str(e)}")
        st.stop()

supabase: Client = init_supabase()

# ============= CREDENCIALES =============
USUARIOS_AUTORIZADOS = {
    "dany": os.getenv("PASS_DANY", "dany123"),
    "pau": os.getenv("PASS_PAU", "pau123"),
    "miguel": os.getenv("PASS_MIGUEL", "miguel123")
}

# ============= FUNCIONES DE VALIDACIÓN =============

def validar_sku(sku: str) -> bool:
    """Validar formato de SKU"""
    return bool(re.match(r'^[A-Z0-9\-]{3,20}$', sku.upper()))

def validar_nombre(nombre: str) -> bool:
    """Validar nombre del producto"""
    return len(nombre.strip()) >= 3 and len(nombre) <= 100

# ============= FUNCIONES DE AUTENTICACIÓN =============

def verificar_credenciales(usuario: str, contraseña: str) -> bool:
    """Verificar credenciales del usuario"""
    return usuario in USUARIOS_AUTORIZADOS and USUARIOS_AUTORIZADOS[usuario] == contraseña

def crear_sesion_persistente(usuario: str) -> tuple:
    """Crear sesión persistente en Supabase"""
    try:
        token = secrets.token_urlsafe(32)
        expiracion = (datetime.now() + timedelta(days=7)).isoformat()
        
        supabase.table("sesiones").insert({
            "usuario": usuario,
            "token": token,
            "expiracion": expiracion,
            "creado_en": datetime.now().isoformat()
        }).execute()
        
        st.session_state.auth_token = token
        st.session_state.usuario_actual = usuario
        
        return True, token
    except Exception as e:
        return False, str(e)

def validar_sesion_persistente(token: str) -> tuple:
    """Validar si la sesión es válida"""
    try:
        if not token:
            return False, None
        
        response = supabase.table("sesiones").select("*").eq("token", token).execute()
        
        if not response.data:
            return False, None
        
        sesion = response.data[0]
        expiracion = datetime.fromisoformat(sesion["expiracion"])
        
        if datetime.now() > expiracion:
            supabase.table("sesiones").delete().eq("token", token).execute()
            return False, None
        
        return True, sesion["usuario"]
    except Exception as e:
        return False, None

def cerrar_sesion(token: str) -> None:
    """Cerrar sesión actual"""
    try:
        if token:
            supabase.table("sesiones").delete().eq("token", token).execute()
        st.session_state.auth_token = None
        st.session_state.usuario_actual = None
    except Exception as e:
        pass

# ============= INICIALIZAR SESSION STATE =============

if 'auth_token' not in st.session_state:
    st.session_state.auth_token = None

if 'usuario_actual' not in st.session_state:
    st.session_state.usuario_actual = None

if 'selected_tab' not in st.session_state:
    st.session_state.selected_tab = 0

# ============= VALIDAR SESIÓN ACTUAL =============

token_actual = st.session_state.auth_token
sesion_valida = False
usuario_logueado = None

if token_actual:
    sesion_valida, usuario_logueado = validar_sesion_persistente(token_actual)
    if sesion_valida:
        st.session_state.usuario_actual = usuario_logueado

# ============= FUNCIONES DE BASE DE DATOS =============

def producto_existe(sku: str) -> bool:
    """Verificar si un producto existe"""
    try:
        response = supabase.table("productos").select("id").eq("sku", sku.upper()).limit(1).execute()
        return len(response.data) > 0
    except Exception as e:
        st.error(f"❌ Error verificando producto: {str(e)}")
        return False

def cargar_productos() -> list:
    """Cargar todos los productos"""
    try:
        response = supabase.table("productos").select("*").order("creado_en", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"❌ Error cargando productos: {str(e)}")
        return []

def crear_producto(sku: str, nombre: str, und_x_embalaje: int) -> tuple:
    """Crear un nuevo producto"""
    try:
        # Validaciones
        if not validar_sku(sku):
            return False, "❌ SKU inválido. Usa: A-Z, 0-9, guiones (3-20 caracteres)"
        
        if not validar_nombre(nombre):
            return False, "❌ Nombre inválido (3-100 caracteres)"
        
        if und_x_embalaje < 1:
            return False, "❌ UND x Embalaje debe ser >= 1"
        
        supabase.table("productos").insert({
            "sku": sku.upper(),
            "nombre": nombre.strip(),
            "und_x_embalaje": int(und_x_embalaje),
            "stock_total": 0,
            "creado_en": datetime.now().isoformat(),
            "actualizado_en": datetime.now().isoformat()
        }).execute()
        
        return True, "✅ Producto creado exitosamente"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def agregar_stock(sku: str, cantidad: int, und_x_embalaje: int, usuario: str) -> tuple:
    """Agregar stock a un producto"""
    try:
        if cantidad < 1:
            return False, "❌ La cantidad debe ser mayor a 0"
        
        response = supabase.table("productos").select("stock_total").eq("sku", sku.upper()).execute()
        
        if not response.data:
            return False, "❌ Producto no encontrado"
        
        stock_actual = response.data[0]["stock_total"]
        nuevo_stock = stock_actual + int(cantidad)
        
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
        
        return True, f"✅ Stock actualizado: +{cantidad} UND"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def cargar_salidas() -> list:
    """Cargar historial de ventas"""
    try:
        response = supabase.table("salidas").select("*").order("fecha", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"❌ Error cargando ventas: {str(e)}")
        return []

def agregar_salida(sku: str, cantidad: int, canal: str, usuario: str) -> tuple:
    """Registrar una venta"""
    try:
        if cantidad < 1:
            return False, "❌ La cantidad debe ser mayor a 0"
        
        response = supabase.table("productos").select("stock_total").eq("sku", sku.upper()).execute()
        
        if not response.data:
            return False, "❌ Producto no encontrado"
        
        stock_actual = response.data[0]["stock_total"]
        
        if stock_actual < cantidad:
            return False, f"❌ Stock insuficiente. Disponible: {stock_actual}"
        
        nuevo_stock = stock_actual - int(cantidad)
        
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
        
        return True, "✅ Venta registrada correctamente"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def cargar_entradas() -> list:
    """Cargar historial de entradas"""
    try:
        response = supabase.table("entradas").select("*").order("fecha", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"❌ Error cargando entradas: {str(e)}")
        return []

# ============= INTERFAZ DE LOGIN =============

if not sesion_valida:
    st.markdown("<div style='text-align: center;'><h1 style='margin-top: 1rem; margin-bottom: 0.3rem;'>📦 M&M Hogar</h1></div>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center;'><p style='margin-top: 0; margin-bottom: 2rem; font-size: 1.1rem;'>Sistema de Inventario</p></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### 🔐 Inicia Sesión")
        
        usuario_input = st.text_input(
            "👤 Usuario:",
            placeholder="Ingresa tu usuario",
            key="login_user"
        )
        
        contraseña_input = st.text_input(
            "🔑 Contraseña:",
            type="password",
            placeholder="Tu contraseña",
            key="login_pass"
        )
        
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("✅ Ingresar", use_container_width=True, type="primary"):
                if not usuario_input or not contraseña_input:
                    st.error("❌ Usuario y contraseña son obligatorios")
                elif verificar_credenciales(usuario_input, contraseña_input):
                    success, token = crear_sesion_persistente(usuario_input)
                    if success:
                        st.success(f"✅ ¡Bienvenido {usuario_input}!")
                        st.rerun()
                    else:
                        st.error(f"❌ Error al crear sesión")
                else:
                    st.error("❌ Usuario o contraseña incorrectos")
        
        with col_btn2:
            if st.button("🗑️ Limpiar", use_container_width=True):
                st.rerun()
    
    st.stop()

# ============= HEADER PRINCIPAL =============

col1, col2, col3 = st.columns([0.2, 2.5, 0.3])

with col1:
    if logo:
        st.image(logo, width=35)
    else:
        st.markdown("## 📦")

with col2:
    st.markdown("<h3 style='margin: 0; padding: 0;'>M&M Hogar - Sistema de Inventario</h3>", unsafe_allow_html=True)

with col3:
    if st.button("🚪 Salir", use_container_width=True):
        cerrar_sesion(st.session_state.auth_token)
        st.rerun()

st.divider()

st.markdown(f"<p style='text-align: center; color: #666; margin: 0.5rem 0;'>👤 <b>{usuario_logueado}</b> | ⏰ Válida 7 días</p>", unsafe_allow_html=True)

st.divider()

# ============= NAVEGACIÓN =============

tab_names = ["📦 Inventario", "💳 Venta", "📊 Ventas", "📥 Entradas", "📈 Stock"]

selected_tab = st.selectbox(
    "Selecciona sección:",
    range(len(tab_names)),
    format_func=lambda x: tab_names[x],
    index=st.session_state.selected_tab,
    key="nav_selectbox",
    label_visibility="collapsed"
)
st.session_state.selected_tab = selected_tab

st.divider()

# ============= TAB 0: INVENTARIO =============

if selected_tab == 0:
    st.subheader("📦 Gestión de Inventario")
    
    productos = cargar_productos()
    
    query = st.text_input(
        "🔍 Buscar SKU o nombre:",
        placeholder="Escribe SKU o parte del nombre...",
        key="buscador_inventario"
    )
    
    if query:
        productos_filtrados = [
            p for p in productos
            if query.upper() in p["sku"].upper() or query.lower() in p["nombre"].lower()
        ]
    else:
        productos_filtrados = []
    
    # Mostrar resultados de búsqueda
    if query:
        if productos_filtrados:
            st.markdown(f"### ✅ {len(productos_filtrados)} resultado(s)")
            
            for p in productos_filtrados[:10]:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        st.markdown(f"**SKU:** `{p['sku']}`")
                        st.markdown(f"**Producto:** {p['nombre']}")
                        st.caption(f"UND x Emb: {p.get('und_x_embalaje', 1)}")
                    
                    with col2:
                        st.metric("Stock", p.get('stock_total', 0))
                    
                    with col3:
                        if st.button("✅ Usar", key=f"btn_usar_{p['sku']}", use_container_width=True):
                            st.session_state.sku_seleccionado = p['sku']
                            st.session_state.nombre_seleccionado = p['nombre']
                            st.session_state.und_seleccionado = p.get('und_x_embalaje', 1)
                            st.rerun()
        else:
            st.warning(f"❌ No hay productos que coincidan con '{query}'")
    
    st.divider()
    
    st.subheader("📝 Agregar o Actualizar Producto")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        sku = st.text_input(
            "SKU",
            value=st.session_state.get('sku_seleccionado', ''),
            placeholder="BS-001",
            key="sku_input",
            help="Formato: letras, números, guiones (3-20 caracteres)"
        ).upper().strip()
    
    with col2:
        nombre = st.text_input(
            "Nombre del Producto",
            value=st.session_state.get('nombre_seleccionado', ''),
            placeholder="Nombre del producto...",
            key="nombre_input",
            help="Mínimo 3 caracteres"
        ).strip()
    
    producto_existe_ahora = producto_existe(sku) if sku else False
    
    with col3:
        und_x_embalaje = st.number_input(
            "UND x Embalaje",
            min_value=1,
            value=st.session_state.get('und_seleccionado', 1),
            key="und_input",
            disabled=producto_existe_ahora,
            help="Unidades por embalaje (solo para nuevos productos)"
        )
    
    cantidad = st.number_input(
        "Cantidad a Agregar",
        min_value=1,
        value=1,
        key="cantidad_inventario",
        help="Unidades a ingresar al inventario"
    )
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("💾 Guardar", use_container_width=True, type="primary", key="btn_guardar_inventario"):
            if not sku or not nombre:
                st.error("❌ SKU y Nombre son obligatorios")
            elif not validar_sku(sku):
                st.error("❌ SKU inválido. Usa: A-Z, 0-9, guiones (3-20 caracteres)")
            elif not validar_nombre(nombre):
                st.error("❌ Nombre inválido (3-100 caracteres)")
            else:
                existe = producto_existe(sku)
                
                if existe:
                    success, msg = agregar_stock(sku, cantidad, und_x_embalaje, usuario_logueado)
                    if success:
                        st.success(msg)
                        for key in ['sku_seleccionado', 'nombre_seleccionado', 'und_seleccionado']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    success_crear, msg_crear = crear_producto(sku, nombre, und_x_embalaje)
                    if success_crear:
                        success_agregar, msg_agregar = agregar_stock(sku, cantidad, und_x_embalaje, usuario_logueado)
                        if success_agregar:
                            st.success(f"{msg_crear} y {msg_agregar}")
                            for key in ['sku_seleccionado', 'nombre_seleccionado', 'und_seleccionado']:
                                if key in st.session_state:
                                    del st.session_state[key]
                            st.rerun()
                        else:
                            st.error(msg_agregar)
                    else:
                        st.error(msg_crear)
    
    with col_btn2:
        if st.button("🗑️ Limpiar Formulario", use_container_width=True, key="btn_limpiar_inventario"):
            for key in ['sku_seleccionado', 'nombre_seleccionado', 'und_seleccionado']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
    
    st.divider()
    
    st.subheader("📊 Todos los Productos")
    
    if productos:
        st.info(f"📦 Total: **{len(productos)}** productos | Stock total: **{sum(p.get('stock_total', 0) for p in productos)}** UND")
        
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
        st.info("📭 No hay productos registrados aún")

# ============= TAB 1: REGISTRAR VENTA =============

elif selected_tab == 1:
    st.subheader("💳 Registrar Venta")
    
    productos = cargar_productos()
    
    if productos:
        opciones = [f"{p['sku']} - {p['nombre']}" for p in productos]
        
        col1, col2 = st.columns(2)
        
        with col1:
            producto_sel = st.selectbox(
                "Producto:",
                opciones,
                key="producto_venta",
                help="Selecciona el producto a vender"
            )
        
        with col2:
            cantidad_venta = st.number_input(
                "Cantidad:",
                min_value=1,
                value=1,
                key="cantidad_venta",
                help="Unidades a vender"
            )
        
        canal = st.selectbox(
            "Canal de Venta:",
            ["Mercadolibre", "Falabella", "Walmart", "Hites", "Paris", "Ripley",
             "Directo - Web", "Directo - WhatsApp", "Directo - Retiro"],
            key="canal_venta",
            help="Selecciona el canal de distribución"
        )
        
        if st.button("✅ Guardar Venta", use_container_width=True, type="primary", key="btn_venta"):
            sku = producto_sel.split(" - ")[0]
            success, msg = agregar_salida(sku, cantidad_venta, canal, usuario_logueado)
            
            if success:
                st.success(msg)
                st.balloons()
                st.rerun()
            else:
                st.error(msg)
    else:
        st.warning("⚠️ Agrega productos primero en la sección de Inventario")

# ============= TAB 2: HISTORIAL DE VENTAS =============

elif selected_tab == 2:
    st.subheader("📊 Historial de Ventas")
    
    salidas = cargar_salidas()
    
    if salidas:
        st.info(f"📊 Total ventas: **{len(salidas)}** | Total unidades: **{sum(v['cantidad'] for v in salidas)}**")
        
        df_salidas = pd.DataFrame([
            {
                "Fecha": v["fecha"][:10],
                "Hora": v["fecha"][11:19] if len(v["fecha"]) > 11 else "N/A",
                "SKU": v["sku"],
                "Cantidad": v["cantidad"],
                "Canal": v["canal"],
                "Usuario": v["usuario"]
            }
            for v in salidas
        ])
        
        st.dataframe(df_salidas, use_container_width=True, hide_index=True)
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = df_salidas.to_csv(index=False)
            st.download_button(
                "📥 Descargar CSV",
                csv_data,
                file_name=f"ventas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                use_container_width=True,
                key="download_ventas"
            )
        
        with col2:
            excel_data = df_salidas.to_excel(
                index=False,
                engine='openpyxl'
            ) if 'openpyxl' in __import__('sys').modules else None
            if excel_data is None:
                st.info("Para descargar Excel, instala: pip install openpyxl")
    else:
        st.info("📭 Sin ventas registradas aún")

# ============= TAB 3: HISTORIAL DE ENTRADAS =============

elif selected_tab == 3:
    st.subheader("📥 Historial de Entradas")
    
    entradas = cargar_entradas()
    
    if entradas:
        st.info(f"📥 Total ingresos: **{len(entradas)}** | Total unidades: **{sum(e['cantidad'] for e in entradas)}**")
        
        df_entradas = pd.DataFrame([
            {
                "Fecha": e["fecha"][:10],
                "Hora": e["fecha"][11:19] if len(e["fecha"]) > 11 else "N/A",
                "SKU": e["sku"],
                "Cantidad": e["cantidad"],
                "UND x Emb": e.get("und_x_embalaje", 1),
                "Usuario": e.get("usuario", "Sistema")
            }
            for e in entradas
        ])
        
        st.dataframe(df_entradas, use_container_width=True, hide_index=True)
        
        st.divider()
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = df_entradas.to_csv(index=False)
            st.download_button(
                "📥 Descargar CSV",
                csv_data,
                file_name=f"entradas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                use_container_width=True,
                key="download_entradas"
            )
        
        with col2:
            st.info("Para descargar Excel, instala: pip install openpyxl")
    else:
        st.info("📭 Sin ingresos registrados aún")

# ============= TAB 4: CONSULTA DE STOCK =============

elif selected_tab == 4:
    st.subheader("📦 Consultar Stock")
    
    productos = cargar_productos()
    
    query_stock = st.text_input(
        "🔍 Buscar producto (SKU o nombre):",
        placeholder="Escribe SKU o parte del nombre...",
        key="buscador_stock",
        help="Búsqueda rápida de productos"
    )
    
    if query_stock:
        productos_filtrados = [
            p for p in productos
            if query_stock.upper() in p["sku"].upper() or query_stock.lower() in p["nombre"].lower()
        ]
    else:
        productos_filtrados = []
    
    if query_stock:
        if productos_filtrados:
            st.markdown(f"### ✅ {len(productos_filtrados)} resultado(s)")
            
            df_resultados = pd.DataFrame([
                {
                    "SKU": p["sku"],
                    "Nombre": p["nombre"],
                    "Stock": p.get("stock_total", 0),
                    "UND x Emb": p.get("und_x_embalaje", 1),
                    "Actualizado": p.get("actualizado_en", "")[:10] if p.get("actualizado_en") else "N/A"
                }
                for p in productos_filtrados
            ])
            
            st.dataframe(df_resultados, use_container_width=True, hide_index=True)
        else:
            st.warning(f"❌ No hay productos que coincidan con '{query_stock}'")
    else:
        st.info("🔎 Usa el buscador para consultar el stock de tus productos")
        
        if productos:
            st.divider()
            st.markdown("### 📋 Todos los Productos")
            
            df_all = pd.DataFrame([
                {
                    "SKU": p["sku"],
                    "Nombre": p["nombre"],
                    "Stock": p.get("stock_total", 0)
                }
                for p in productos
            ])
            
            st.dataframe(df_all, use_container_width=True, hide_index=True)
