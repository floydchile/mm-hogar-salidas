import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

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
# INICIALIZAR SESIÓN
# ============================================================================

def init_session():
    """Inicializar variables de sesión"""
    if 'usuario' not in st.session_state:
        st.session_state.usuario = None
    if 'productos' not in st.session_state:
        st.session_state.productos = []
    if 'salidas' not in st.session_state:
        st.session_state.salidas = []

init_session()

# ============================================================================
# INTERFAZ PRINCIPAL
# ============================================================================

def main():
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
                        nuevo_producto = {
                            'id': len(st.session_state.productos) + 1,
                            'sku': sku,
                            'nombre': nombre,
                            'variante': variante,
                            'categoria': categoria,
                            'creado_en': datetime.now().isoformat()
                        }
                        st.session_state.productos.append(nuevo_producto)
                        st.success("✅ Producto agregado correctamente!")
                        st.rerun()
                    else:
                        st.warning("⚠️ Completa SKU, Nombre y Variante")
        
        with col2:
            st.subheader("📦 Productos Registrados")
            
            if st.session_state.productos:
                st.info(f"Total productos: {len(st.session_state.productos)}")
                
                # Tabla de productos
                df_productos = pd.DataFrame(st.session_state.productos)
                cols_mostrar = ['sku', 'nombre', 'variante']
                if 'categoria' in df_productos.columns:
                    cols_mostrar.append('categoria')
                
                df_mostrar = df_productos[cols_mostrar].copy()
                st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
                
                # Eliminar producto
                with st.expander("🗑️ Eliminar Producto"):
                    if st.session_state.productos:
                        opciones = [f"{p['nombre']} - {p['variante']}" for p in st.session_state.productos]
                        prod_seleccionado = st.selectbox(
                            "Selecciona producto a eliminar:",
                            opciones,
                            key="delete_prod"
                        )
                        if st.button("Eliminar", key="btn_delete", use_container_width=True):
                            idx = opciones.index(prod_seleccionado)
                            st.session_state.productos.pop(idx)
                            st.success("✅ Producto eliminado!")
                            st.rerun()
            else:
                st.info("📭 Sin productos registrados aún. Agrega uno para comenzar.")
    
    # ========================================================================
    # TAB 2: REGISTRAR SALIDAS
    # ========================================================================
    with tab2:
        st.header("Registrar Salida de Mercadería")
        
        if not st.session_state.productos:
            st.warning("⚠️ Debes agregar productos primero en la pestaña 'Cargar Productos'")
        else:
            with st.form("form_salida"):
                col1, col2 = st.columns(2)
                
                with col1:
                    # Búsqueda de producto
                    opciones_productos = [
                        f"{p['nombre']} - {p['variante']}" 
                        for p in st.session_state.productos
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
                        producto_id = st.session_state.productos[idx]['id']
                        
                        nueva_salida = {
                            'id': len(st.session_state.salidas) + 1,
                            'producto_id': producto_id,
                            'nombre': st.session_state.productos[idx]['nombre'],
                            'variante': st.session_state.productos[idx]['variante'],
                            'cantidad': int(cantidad),
                            'canal': canal,
                            'usuario': st.session_state.usuario,
                            'fecha': datetime.now().isoformat()
                        }
                        st.session_state.salidas.append(nueva_salida)
                        st.success(f"✅ Salida registrada: {producto_seleccionado} x {cantidad} ({canal})")
                        st.balloons()
                        st.rerun()
                    else:
                        st.warning("⚠️ Ingresa tu nombre de usuario primero")
    
    # ========================================================================
    # TAB 3: ESTADÍSTICAS
    # ========================================================================
    with tab3:
        st.header("📈 Estadísticas de Ventas")
        
        if not st.session_state.salidas:
            st.info("📭 Sin datos de salidas aún")
        else:
            df_salidas = pd.DataFrame(st.session_state.salidas)
            
            # Estadísticas generales
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Unidades", df_salidas['cantidad'].sum())
            with col2:
                st.metric("Productos Vendidos", df_salidas['producto_id'].nunique())
            with col3:
                st.metric("Canales", df_salidas['canal'].nunique())
            with col4:
                st.metric("Registros", len(df_salidas))
            
            st.markdown("---")
            
            # Gráficos simples con pandas
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 Ventas por Canal")
                canal_stats = df_salidas.groupby('canal')['cantidad'].sum().reset_index()
                st.bar_chart(canal_stats.set_index('canal'))
            
            with col2:
                st.subheader("🏆 Top 10 Productos")
                top_productos = df_salidas.groupby('nombre')['cantidad'].sum().nlargest(10).reset_index()
                st.bar_chart(top_productos.set_index('nombre'))
            
            # Tabla detallada
            st.subheader("📋 Detalle de Salidas")
            cols_mostrar = ['nombre', 'cantidad', 'canal', 'usuario', 'fecha']
            df_tabla = df_salidas[cols_mostrar].copy()
            df_tabla = df_tabla.sort_values('fecha', ascending=False)
            st.dataframe(df_tabla, use_container_width=True, hide_index=True)
    
    # ========================================================================
    # TAB 4: HISTORIAL
    # ========================================================================
    with tab4:
        st.header("📋 Historial Completo de Salidas")
        
        if not st.session_state.salidas:
            st.info("📭 Sin historial de salidas")
        else:
            df_historial = pd.DataFrame(st.session_state.salidas)
            
            # Opciones de filtro
            col1, col2 = st.columns(2)
            
            with col1:
                filtro_canal = st.multiselect(
                    "Filtrar por Canal:",
                    df_historial['canal'].unique().tolist(),
                    default=None
                )
            
            with col2:
                filtro_usuario = st.multiselect(
                    "Filtrar por Usuario:",
                    df_historial['usuario'].unique().tolist(),
                    default=None
                )
            
            # Aplicar filtros
            if filtro_canal:
                df_historial = df_historial[df_historial['canal'].isin(filtro_canal)]
            
            if filtro_usuario:
                df_historial = df_historial[df_historial['usuario'].isin(filtro_usuario)]
            
            df_historial = df_historial.sort_values('fecha', ascending=False)
            
            # Mostrar tabla
            cols_mostrar = ['nombre', 'variante', 'cantidad', 'canal', 'usuario', 'fecha']
            cols_disponibles = [col for col in cols_mostrar if col in df_historial.columns]
            
            st.dataframe(df_historial[cols_disponibles], use_container_width=True, hide_index=True)
            
            # Opción de exportar
            csv = df_historial.to_csv(index=False, encoding='utf-8')
            st.download_button(
                label="📥 Descargar como CSV",
                data=csv,
                file_name=f"salidas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
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
