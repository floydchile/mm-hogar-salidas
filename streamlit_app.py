import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import os
import pandas as pd
from PIL import Image
import re

st.set_page_config(
    page_title="M&M Hogar",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
        .block-container {
            padding-top: 0.5rem;
            padding-bottom: 0rem;
        }
        .stMetric {
            background-color: transparent;
        }
    </style>
""", unsafe_allow_html=True)

try:
    logo = Image.open("assets/mym_hogar.png")
except FileNotFoundError:
    logo = None

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

USUARIOS_VALIDOS = ["pau", "dany", "miguel"]

def validar_sku(sku: str) -> bool:
    return bool(re.match(r'^[A-Z0-9\-]{3,20}$', sku.upper()))

def validar_nombre(nombre: str) -> bool:
    return len(nombre.strip()) >= 3 and len(nombre) <= 100

if 'selected_tab' not in st.session_state:
    st.session_state.selected_tab = 0

if 'usuario_ingresado' not in st.session_state:
    st.session_state.usuario_ingresado = None

def producto_existe(sku: str) -> bool:
    try:
        response = supabase.table("productos").select("id").eq("sku", sku.upper()).limit(1).execute()
        return len(response.data) > 0
    except Exception as e:
        st.error(f"❌ Error verificando producto: {str(e)}")
        return False

def cargar_productos() -> list:
    try:
        response = supabase.table("productos").select("*").order("creado_en", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"❌ Error cargando productos: {str(e)}")
        return []

def crear_producto(sku: str, nombre: str, und_x_embalaje: int, precio_costo: float = 0) -> tuple:
    try:
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
            "precio_costo_contenedor": float(precio_costo),
            "creado_en": datetime.now().isoformat(),
            "actualizado_en": datetime.now().isoformat()
        }).execute()
        
        return True, "✅ Producto creado exitosamente"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def actualizar_precio_costo(sku: str, precio_costo: float) -> tuple:
    try:
        if precio_costo < 0:
            return False, "❌ El precio no puede ser negativo"
        
        supabase.table("productos").update({
            "precio_costo_contenedor": float(precio_costo),
            "actualizado_en": datetime.now().isoformat()
        }).eq("sku", sku.upper()).execute()
        
        return True, f"✅ Precio costo actualizado: ${precio_costo:,.0f}"
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

def agregar_stock(sku: str, cantidad: int, und_x_embalaje: int, usuario: str) -> tuple:
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
    try:
        response = supabase.table("salidas").select("*").order("fecha", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"❌ Error cargando ventas: {str(e)}")
        return []

def agregar_salida(sku: str, cantidad: int, canal: str, usuario: str) -> tuple:
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
    try:
        response = supabase.table("entradas").select("*").order("fecha", desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"❌ Error cargando entradas: {str(e)}")
        return []

def requiere_usuario(funcion_nombre: str) -> bool:
    if not st.session_state.usuario_ingresado:
        st.error(f"❌ Debes seleccionar un usuario para {funcion_nombre}")
        return False
    return True

with st.sidebar:
    usuario_actual = st.session_state.usuario_ingresado
    
    if usuario_actual:
        st.markdown("### ✅ Usuario Activo")
        st.markdown(f"<div style='background-color: #d4edda; border: 2px solid #28a745; border-radius: 8px; padding: 12px; text-align: center; margin-bottom: 16px;'><p style='margin: 0; font-size: 18px; font-weight: bold; color: #155724;'>{usuario_actual.upper()}</p></div>", unsafe_allow_html=True)
        
        if st.button("🚪 Cerrar Sesión", use_container_width=True, key="btn_logout"):
            st.session_state.usuario_ingresado = None
            st.info("👋 Sesión cerrada")
            st.rerun()
    else:
        st.markdown("### 👤 Ingresar Usuario")
        
        usuario_input = st.text_input(
            "Ingresa tu usuario:",
            value="",
            key="usuario_input_field",
            label_visibility="collapsed"
        ).lower().strip()
        
        if st.button("✅ Ingresar", use_container_width=True, type="primary", key="btn_confirmar_usuario"):
            if usuario_input in USUARIOS_VALIDOS:
                st.session_state.usuario_ingresado = usuario_input
                st.success(f"✅ ¡Bienvenido {usuario_input.capitalize()}!")
                st.rerun()
            elif usuario_input:
                st.error(f"❌ Usuario inválido. Usa: pau, dany o miguel")
            else:
                st.error(f"❌ Campo vacío")
        
        st.caption("💡 El usuario se guardará mientras mantengas la sesión abierta")
    
    st.divider()

col1, col2, col3 = st.columns([0.15, 2.35, 0.5])

with col1:
    if logo:
        st.image(logo, width=40)
    else:
        st.markdown("## 📦")

with col2:
    st.markdown("<h2 style='margin: 0; padding: 0; font-size: 1.5rem;'>M&M Hogar</h2>", unsafe_allow_html=True)
    st.markdown("<p style='margin: 0; padding: 0; font-size: 0.9rem; color: #666;'>Sistema de Inventario</p>", unsafe_allow_html=True)

with col3:
    usuario_actual = st.session_state.usuario_ingresado
    if usuario_actual:
        usuario_display = f"✅ {usuario_actual.capitalize()}"
        st.markdown(f"<p style='text-align: right; margin: 0; padding: 0.3rem 0; font-weight: bold; color: #28a745;'>{usuario_display}</p>", unsafe_allow_html=True)
    else:
        st.markdown(f"<p style='text-align: right; margin: 0; padding: 0.3rem 0; font-weight: bold; color: #dc3545;'>❌ Sin usuario</p>", unsafe_allow_html=True)

st.divider()

tab_names = ["📦 Inventario", "💳 Venta", "📋 Historial", "📈 Stock", "💰 Costos"]

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

if selected_tab == 0:
    st.subheader("📦 Gestión de Inventario")
    
    if not requiere_usuario("gestionar inventario"):
        st.stop()
    
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
                            st.session_state.precio_costo_seleccionado = p.get('precio_costo_contenedor', 0)
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
    
    col4, col5 = st.columns(2)
    
    with col4:
        precio_costo = st.number_input(
            "Precio Costo Contenedor (CLP)",
            min_value=0,
            value=int(st.session_state.get('precio_costo_seleccionado', 0)),
            key="precio_costo_input",
            help="Precio del contenedor en pesos chilenos"
        )
    
    with col5:
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
            if not requiere_usuario("guardar productos"):
                pass
            elif not sku or not nombre:
                st.error("❌ SKU y Nombre son obligatorios")
            elif not validar_sku(sku):
                st.error("❌ SKU inválido. Usa: A-Z, 0-9, guiones (3-20 caracteres)")
            elif not validar_nombre(nombre):
                st.error("❌ Nombre inválido (3-100 caracteres)")
            else:
                existe = producto_existe(sku)
                usuario_actual = st.session_state.usuario_ingresado.lower()
                
                if existe:
                    success_precio, msg_precio = actualizar_precio_costo(sku, precio_costo)
                    success, msg = agregar_stock(sku, cantidad, und_x_embalaje, usuario_actual)
                    if success and success_precio:
                        st.success(f"{msg} y {msg_precio}")
                        for key in ['sku_seleccionado', 'nombre_seleccionado', 'und_seleccionado', 'precio_costo_seleccionado']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()
                    else:
                        st.error(msg if not success else msg_precio)
                else:
                    success_crear, msg_crear = crear_producto(sku, nombre, und_x_embalaje, precio_costo)
                    if success_crear:
                        success_agregar, msg_agregar = agregar_stock(sku, cantidad, und_x_embalaje, usuario_actual)
                        if success_agregar:
                            st.success(f"{msg_crear} y {msg_agregar}")
                            for key in ['sku_seleccionado', 'nombre_seleccionado', 'und_seleccionado', 'precio_costo_seleccionado']:
                                if key in st.session_state:
                                    del st.session_state[key]
                            st.rerun()
                        else:
                            st.error(msg_agregar)
                    else:
                        st.error(msg_crear)
    
    with col_btn2:
        if st.button("🗑️ Limpiar Formulario", use_container_width=True, key="btn_limpiar_inventario"):
            for key in ['sku_seleccionado', 'nombre_seleccionado', 'und_seleccionado', 'precio_costo_seleccionado']:
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
                "Precio Costo": f"${p.get('precio_costo_contenedor', 0):,.0f}" if p.get('precio_costo_contenedor', 0) > 0 else "N/A",
                "Actualizado": p.get("actualizado_en", "")[:10] if p.get("actualizado_en") else "N/A"
            }
            for p in productos
        ])
        
        st.dataframe(df_productos, use_container_width=True, hide_index=True)
    else:
        st.info("📭 No hay productos registrados aún")

elif selected_tab == 1:
    st.subheader("💳 Registrar Venta")
    
    if not requiere_usuario("registrar ventas"):
        st.stop()
    
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
            usuario_actual = st.session_state.usuario_ingresado.lower()
            success, msg = agregar_salida(sku, cantidad_venta, canal, usuario_actual)
            
            if success:
                st.success(msg)
                st.balloons()
                st.rerun()
            else:
                st.error(msg)
    else:
        st.warning("⚠️ Agrega productos primero en la sección de Inventario")

elif selected_tab == 2:
    st.subheader("📋 Historial Completo")
    
    entradas = cargar_entradas()
    salidas = cargar_salidas()
    productos = cargar_productos()
    productos_dict = {p["sku"]: p["nombre"] for p in productos}
    
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        filtro_tipo = st.selectbox(
            "Tipo:",
            ["TODO", "Entrada 🟢", "Venta 🔴"],
            key="filtro_tipo"
        )
    
    with col_f2:
        filtro_usuario = st.selectbox(
            "Usuario:",
            ["TODO"] + USUARIOS_VALIDOS,
            key="filtro_usuario"
        )
    
    with col_f3:
        filtro_busqueda = st.text_input(
            "🔍 Buscar SKU:",
            key="filtro_busqueda"
        ).upper().strip()
    
    historial = []
    
    for e in entradas:
        historial.append({
            "Fecha": e["fecha"][:10],
            "Hora": e["fecha"][11:19] if len(e["fecha"]) > 11 else "N/A",
            "Tipo": "🟢 Entrada",
            "SKU": e["sku"],
            "Nombre": productos_dict.get(e["sku"], ""),
            "Cantidad": e["cantidad"],
            "Info": f"{e.get('und_x_embalaje', 1)} UND/Emb",
            "Usuario": e.get("usuario", "Sistema"),
            "Canal": "-"
        })
    
    for v in salidas:
        historial.append({
            "Fecha": v["fecha"][:10],
            "Hora": v["fecha"][11:19] if len(v["fecha"]) > 11 else "N/A",
            "Tipo": "🔴 Venta",
            "SKU": v["sku"],
            "Nombre": productos_dict.get(v["sku"], ""),
            "Cantidad": v["cantidad"],
            "Info": v.get("canal", "-"),
            "Usuario": v["usuario"],
            "Canal": v.get("canal", "-")
        })
    
    historial.sort(key=lambda x: x["Fecha"], reverse=True)
    
    if filtro_tipo != "TODO":
        tipo_busqueda = "🟢 Entrada" if filtro_tipo == "Entrada 🟢" else "🔴 Venta"
        historial = [h for h in historial if h["Tipo"] == tipo_busqueda]
    
    if filtro_usuario != "TODO":
        historial = [h for h in historial if h["Usuario"].lower() == filtro_usuario.lower()]
    
    if filtro_busqueda:
        historial = [h for h in historial if filtro_busqueda in h["SKU"]]
    
    if historial:
        st.info(f"📋 Total: **{len(historial)}** registros | Unidades: **{sum(h['Cantidad'] for h in historial)}**")
        
        df_historial = pd.DataFrame(historial)
        st.dataframe(df_historial, use_container_width=True, hide_index=True)
        
        csv_data = df_historial.to_csv(index=False)
        st.download_button(
            "📥 Descargar CSV",
            csv_data,
            file_name=f"historial_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            use_container_width=True
        )
    else:
        st.warning("❌ Sin registros")

elif selected_tab == 3:
    st.subheader("📦 Consultar Stock")
    
    productos = cargar_productos()
    
    query_stock = st.text_input(
        "🔍 Buscar producto:",
        placeholder="SKU o nombre...",
        key="buscador_stock"
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
                    "UND x Emb": p.get("und_x_embalaje", 1)
                }
                for p in productos_filtrados
            ])
            
            st.dataframe(df_resultados, use_container_width=True, hide_index=True)
        else:
            st.warning(f"❌ No encontrado: '{query_stock}'")
    else:
        st.info("🔎 Usa el buscador")
        
        if productos:
            df_all = pd.DataFrame([
                {
                    "SKU": p["sku"],
                    "Nombre": p["nombre"],
                    "Stock": p.get("stock_total", 0)
                }
                for p in productos
            ])
            
            st.dataframe(df_all, use_container_width=True, hide_index=True)

elif selected_tab == 4:
    st.subheader("💰 Análisis de Costos")
    
    productos = cargar_productos()
    
    query_costos = st.text_input(
        "🔍 Buscar producto:",
        key="buscador_costos"
    )
    
    if query_costos:
        productos_filtrados = [
            p for p in productos
            if query_costos.upper() in p["sku"].upper() or query_costos.lower() in p["nombre"].lower()
        ]
    else:
        productos_filtrados = []
    
    if query_costos:
        if productos_filtrados:
            st.markdown(f"### ✅ {len(productos_filtrados)} resultado(s)")
            
            df_costos = pd.DataFrame([
                {
                    "SKU": p["sku"],
                    "Nombre": p["nombre"],
                    "UND x Emb": p.get("und_x_embalaje", 1),
                    "Precio Costo": f"${p.get('precio_costo_contenedor', 0):,.0f}",
                    "Precio Unit.": f"${p.get('precio_costo_contenedor', 0) / max(p.get('und_x_embalaje', 1), 1):,.0f}",
                    "Stock": p.get("stock_total", 0),
                    "Inversión": f"${(p.get('precio_costo_contenedor', 0) / max(p.get('und_x_embalaje', 1), 1)) * p.get('stock_total', 0):,.0f}"
                }
                for p in productos_filtrados
            ])
            
            st.dataframe(df_costos, use_container_width=True, hide_index=True)
        else:
            st.warning(f"❌ No encontrado")
    else:
        st.info("🔎 Usa el buscador")
        
        if productos:
            productos_con_costo = [p for p in productos if p.get('precio_costo_contenedor', 0) > 0]
            
            if productos_con_costo:
                df_all_costos = pd.DataFrame([
                    {
                        "SKU": p["sku"],
                        "Nombre": p["nombre"],
                        "UND x Emb": p.get("und_x_embalaje", 1),
                        "Precio Costo": f"${p.get('precio_costo_contenedor', 0):,.0f}",
                        "Precio Unit.": f"${p.get('precio_costo_contenedor', 0) / max(p.get('und_x_embalaje', 1), 1):,.0f}",
                        "Stock": p.get("stock_total", 0),
                        "Inversión": f"${(p.get('precio_costo_contenedor', 0) / max(p.get('und_x_embalaje', 1), 1)) * p.get('stock_total', 0):,.0f}"
                    }
                    for p in productos_con_costo
                ])
                
                st.dataframe(df_all_costos, use_container_width=True, hide_index=True)
                
                st.divider()
                
                inversión_total = sum(
                    (p.get('precio_costo_contenedor', 0) / max(p.get('und_x_embalaje', 1), 1)) * p.get('stock_total', 0)
                    for p in productos_con_costo
                )
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Inversión Total", f"${inversión_total:,.0f}")
                with col2:
                    st.metric("Productos", len(productos_con_costo))
                with col3:
                    st.metric("Unidades", sum(p.get('stock_total', 0) for p in productos_con_costo))
            else:
                st.info("📭 Sin precios asignados")
