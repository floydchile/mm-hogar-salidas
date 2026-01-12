import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go

# ============================================================================
# CONFIGURACIÓN STREAMLIT
# ============================================================================

st.set_page_config(
    page_title="M&M Hogar - Salidas",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CONFIGURACIÓN SUPABASE
# ============================================================================

SUPABASE_URL = "https://nijzonhfxyihpgozinge.supabase.co"
SUPABASE_KEY = "sb_publishable_OxdVTgYO8qizBUYrtvEkVA_LX3fY1-x"

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase: Client = init_supabase()

# ============================================================================
# INICIALIZAR SESIÓN Y BASE DE DATOS
# ============================================================================

def init_session():
    """Inicializar variables de sesión"""
    if 'usuario' not in st.session_state:
        st.session_state.usuario = None
    if 'usuario_id' not in st.session_state:
        st.session_state.usuario_id = None

def crear_tablas_si_no_existen():
    """Crear tablas en Supabase si no existen"""
    try:
        # Verificar si tabla productos existe
        supabase.table('productos').select('id').limit(1).execute()
    except:
        # Crear tabla productos
        try:
            supabase.rpc('create_tabla_productos').execute()
        except:
            pass
    
    try:
        # Verificar si tabla salidas existe
        supabase.table('salidas').select('id').limit(1).execute()
    except:
        # Crear tabla salidas
        try:
            supabase.rpc('create_tabla_salidas').execute()
        except:
            pass

# ============================================================================
# FUNCIONES DE BASE DE DATOS
# ============================================================================

def cargar_productos():
    """Cargar todos los productos"""
    try:
        response = supabase.table('productos').select('*').execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except:
        return pd.DataFrame()

def agregar_producto(sku, nombre, variante, categoria=""):
    """Agregar nuevo producto"""
    try:
        data = {
            'sku': sku,
            'nombre': nombre,
            'variante': variante,
            'categoria': categoria,
            'creado_en': datetime.now().isoformat()
        }
        supabase.table('productos').insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Error al agregar producto: {str(e)}")
        return False

def eliminar_producto(id_producto):
    """Eliminar un producto"""
    try:
        supabase.table('productos').delete().eq('id', id_producto).execute()
        return True
    except:
        return False

def registrar_salida(producto_id, cantidad, canal, usuario):
    """Registrar una salida de mercadería"""
    try:
        data = {
            'producto_id': producto_id,
            'cantidad': int(cantidad),
            'canal': canal,
            'usuario': usuario,
            'fecha': datetime.now().isoformat()
        }
        supabase.table('salidas').insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Error al registrar salida: {str(e)}")
        return False

def cargar_salidas(fecha_inicio=None, fecha_fin=None):
    """Cargar salidas con filtros opcionales"""
    try:
        query = supabase.table('salidas').select('*')
        
        if fecha_inicio:
            query = query.gte('fecha', fecha_inicio.isoformat())
        if fecha_fin:
            query = query.lte('fecha', (fecha_fin + timedelta(days=1)).isoformat())
        
        response = query.execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            # Cargar nombres de productos
            productos = cargar_productos()
            if not productos.empty:
                df = df.merge(productos[['id', 'nombre', 'variante']], 
                            left_on='producto_id', right_on='id', how='left')
            return df
        return pd.DataFrame()
    except:
        return pd.DataFrame()

# ============================================================================
# UI PRINCIPAL
# ============================================================================

def main():
    init_session()
    crear_tablas_si_no_existen()
    
    # Sidebar para usuario
    with st.sidebar:
        st.title("👤 Usuario")
        usuario_nombre = st.text_input("Nombre de usuario:", value=st.session_state.usuario or "")
        if usuario_nombre:
            st.session_state.usuario = usuario_nombre
            st.success(f"Bienvenido, {usuario_nombre}!")
    
    # Título principal
    st.title("📦 M&M Hogar - Sistema de Salidas")
    st.markdown("---")
    
    # Tabs principales
    tab1, tab2, tab3, tab4 = st.tabs([
        "📥 Cargar Productos",
        "📊 Registrar Salidas",
        "📈 Estadísticas",
        "📋 Historial"
    ])
    
    # ========================================================================
    # TAB 1: CARGAR PRODUCTOS
    # ========================================================================
    with tab1:
        st.header("Gestión de Productos")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("➕ Agregar Nuevo Producto")
            with st.form("form_producto"):
                sku = st.text_input("SKU (ej: BS-001)", placeholder="BS-001")
                nombre = st.text_input("Nombre Producto (ej: Babysec Premium)")
                variante = st.text_area("Variante (ej: Talla P - 20 UND x paq / 8 paq x manga)")
                categoria = st.text_input("Categoría (opcional)", placeholder="ej: Pañales")
                
                submitted = st.form_submit_button("✅ Guardar Producto", use_container_width=True)
                
                if submitted:
                    if sku and nombre and variante:
                        if agregar_producto(sku, nombre, variante, categoria):
                            st.success("✅ Producto agregado correctamente!")
                            st.rerun()
                        else:
                            st.error("❌ Error al agregar producto")
                    else:
                        st.warning("⚠️ Completa SKU, Nombre y Variante")
        
        with col2:
            st.subheader("📦 Productos Registrados")
            productos = cargar_productos()
            
            if not productos.empty:
                st.info(f"Total productos: {len(productos)}")
                
                # Tabla de productos
                cols_mostrar = ['sku', 'nombre', 'variante']
                if 'categoria' in productos.columns:
                    cols_mostrar.append('categoria')
                
                df_mostrar = productos[cols_mostrar].copy()
                st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
                
                # Eliminar producto
                with st.expander("🗑️ Eliminar Producto"):
                    if not productos.empty:
                        prod_seleccionado = st.selectbox(
                            "Selecciona producto a eliminar:",
                            productos['nombre'] + " - " + productos['variante'],
                            key="delete_prod"
                        )
                        if st.button("Eliminar", key="btn_delete", use_container_width=True):
                            idx = list(productos['nombre'] + " - " + productos['variante']).index(prod_seleccionado)
                            if eliminar_producto(productos.iloc[idx]['id']):
                                st.success("✅ Producto eliminado!")
                                st.rerun()
            else:
                st.info("📭 Sin productos registrados aún. Agrega uno para comenzar.")
    
    # ========================================================================
    # TAB 2: REGISTRAR SALIDAS
    # ========================================================================
    with tab2:
        st.header("Registrar Salida de Mercadería")
        
        productos = cargar_productos()
        
        if productos.empty:
            st.warning("⚠️ Debes agregar productos primero en la pestaña 'Cargar Productos'")
        else:
            with st.form("form_salida"):
                col1, col2 = st.columns(2)
                
                with col1:
                    # Búsqueda de producto
                    opciones_productos = [
                        f"{row['nombre']} - {row['variante']}" 
                        for _, row in productos.iterrows()
                    ]
                    
                    producto_seleccionado = st.selectbox(
                        "🔍 Buscar Producto:",
                        opciones_productos,
                        key="select_producto"
                    )
                    
                    cantidad = st.number_input(
                        "📦 Cantidad Vendida:",
                        min_value=1,
                        step=1,
                        value=1
                    )
                
                with col2:
                    # Canal de venta
                    canales = [
                        "Marketplace 1",
                        "Marketplace 2",
                        "Web Propia",
                        "Venta Directa",
                        "Otro"
                    ]
                    
                    canal = st.selectbox(
                        "📍 Canal de Venta:",
                        canales,
                        key="select_canal"
                    )
                
                # Botón guardar
                submitted = st.form_submit_button(
                    "💾 Guardar Salida",
                    use_container_width=True
                )
                
                if submitted:
                    if st.session_state.usuario:
                        # Obtener ID del producto seleccionado
                        idx = opciones_productos.index(producto_seleccionado)
                        producto_id = productos.iloc[idx]['id']
                        
                        if registrar_salida(producto_id, cantidad, canal, st.session_state.usuario):
                            st.success(f"✅ Salida registrada: {producto_seleccionado} x {cantidad} ({canal})")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error("❌ Error al registrar salida")
                    else:
                        st.warning("⚠️ Ingresa tu nombre de usuario primero")
    
    # ========================================================================
    # TAB 3: ESTADÍSTICAS
    # ========================================================================
    with tab3:
        st.header("📈 Estadísticas de Ventas")
        
        # Filtros de fecha
        col1, col2, col3 = st.columns(3)
        
        with col1:
            rango = st.selectbox(
                "Período:",
                ["Hoy", "Última Semana", "Este Mes", "Personalizado"]
            )
        
        fecha_inicio = None
        fecha_fin = datetime.now()
        
        if rango == "Hoy":
            fecha_inicio = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        elif rango == "Última Semana":
            fecha_inicio = datetime.now() - timedelta(days=7)
        elif rango == "Este Mes":
            fecha_inicio = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif rango == "Personalizado":
            with col2:
                fecha_inicio = st.date_input("Desde:", value=datetime.now() - timedelta(days=30))
            with col3:
                fecha_fin = st.date_input("Hasta:", value=datetime.now())
        
        # Cargar datos
        salidas = cargar_salidas(fecha_inicio, fecha_fin)
        
        if salidas.empty:
            st.info("📭 Sin datos para mostrar en este período")
        else:
            # Estadísticas generales
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Unidades", salidas['cantidad'].sum())
            with col2:
                st.metric("Productos Vendidos", salidas['producto_id'].nunique())
            with col3:
                st.metric("Canales", salidas['canal'].nunique())
            with col4:
                st.metric("Registros", len(salidas))
            
            st.markdown("---")
            
            # Gráficos
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Ventas por Canal")
                canal_counts = salidas.groupby('canal')['cantidad'].sum().reset_index()
                fig_canal = px.pie(
                    canal_counts,
                    values='cantidad',
                    names='canal',
                    hole=0.4
                )
                st.plotly_chart(fig_canal, use_container_width=True)
            
            with col2:
                st.subheader("🏆 Top 10 Productos")
                top_productos = salidas.groupby('nombre')['cantidad'].sum().nlargest(10).reset_index()
                fig_top = px.bar(
                    top_productos,
                    x='cantidad',
                    y='nombre',
                    orientation='h',
                    color='cantidad',
                    color_continuous_scale='Viridis'
                )
                fig_top.update_layout(showlegend=False)
                st.plotly_chart(fig_top, use_container_width=True)
            
            # Tabla detallada
            st.subheader("📋 Detalle de Salidas")
            cols_mostrar = ['nombre', 'cantidad', 'canal', 'usuario', 'fecha']
            df_tabla = salidas[cols_mostrar].copy()
            df_tabla = df_tabla.sort_values('fecha', ascending=False)
            st.dataframe(df_tabla, use_container_width=True, hide_index=True)
    
    # ========================================================================
    # TAB 4: HISTORIAL
    # ========================================================================
    with tab4:
        st.header("📋 Historial Completo de Salidas")
        
        # Opciones de filtro
        col1, col2 = st.columns(2)
        
        with col1:
            filtro_canal = st.multiselect(
                "Filtrar por Canal:",
                ["Marketplace 1", "Marketplace 2", "Web Propia", "Venta Directa", "Otro"],
                default=None
            )
        
        with col2:
            filtro_usuario = st.multiselect(
                "Filtrar por Usuario:",
                [],
                default=None
            )
        
        # Cargar historial completo
        historial = cargar_salidas()
        
        if not historial.empty:
            # Aplicar filtros
            if filtro_canal:
                historial = historial[historial['canal'].isin(filtro_canal)]
            
            if filtro_usuario:
                historial = historial[historial['usuario'].isin(filtro_usuario)]
            
            historial = historial.sort_values('fecha', ascending=False)
            
            # Mostrar tabla
            cols_mostrar = ['nombre', 'variante', 'cantidad', 'canal', 'usuario', 'fecha']
            cols_disponibles = [col for col in cols_mostrar if col in historial.columns]
            
            st.dataframe(historial[cols_disponibles], use_container_width=True, hide_index=True)
            
            # Opción de exportar
            csv = historial.to_csv(index=False, encoding='utf-8')
            st.download_button(
                label="📥 Descargar como CSV",
                data=csv,
                file_name=f"salidas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("📭 Sin historial de salidas")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray; font-size: 12px;'>
        M&M Hogar © 2026 | Sistema de Registro de Salidas de Mercadería
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()