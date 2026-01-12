import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="M&M Hogar - Salidas",
    page_icon="📦",
    layout="wide"
)

# Inicializar sesión
if 'usuario' not in st.session_state:
    st.session_state.usuario = None
if 'productos' not in st.session_state:
    st.session_state.productos = []
if 'salidas' not in st.session_state:
    st.session_state.salidas = []

# Sidebar
with st.sidebar:
    st.title("👤 Usuario")
    usuario = st.text_input("Tu nombre:", value=st.session_state.usuario or "")
    if usuario:
        st.session_state.usuario = usuario
        st.success(f"¡Bienvenido {usuario}!")

# Título
st.title("📦 M&M Hogar - Sistema de Salidas")
st.markdown("---")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📥 Productos", "📊 Registrar", "📈 Estadísticas", "📋 Historial"])

# TAB 1: PRODUCTOS
with tab1:
    st.header("Gestión de Productos")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Agregar Producto")
        sku = st.text_input("SKU", placeholder="BS-001")
        nombre = st.text_input("Nombre", placeholder="Babysec Premium")
        variante = st.text_area("Variante", placeholder="Talla P - 20 UND x paq / 8 paq x manga")
        
        if st.button("✅ Guardar", key="btn_guardar_prod"):
            if sku and nombre and variante:
                st.session_state.productos.append({
                    'sku': sku,
                    'nombre': nombre,
                    'variante': variante
                })
                st.success("✅ Producto agregado")
                st.rerun()
            else:
                st.warning("Completa todos los campos")
    
    with col2:
        st.subheader(f"Productos ({len(st.session_state.productos)})")
        if st.session_state.productos:
            for i, p in enumerate(st.session_state.productos):
                st.write(f"**{p['sku']}** - {p['nombre']}")
                if st.button("🗑️ Eliminar", key=f"del_{i}"):
                    st.session_state.productos.pop(i)
                    st.rerun()
        else:
            st.info("No hay productos")

# TAB 2: REGISTRAR SALIDAS
with tab2:
    st.header("Registrar Salida")
    
    if not st.session_state.productos:
        st.warning("Agrega productos primero")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            opciones = [f"{p['nombre']} - {p['variante']}" for p in st.session_state.productos]
            producto = st.selectbox("Producto:", opciones)
            cantidad = st.number_input("Cantidad:", min_value=1, value=1)
        
        with col2:
            canal = st.selectbox("Canal:", ["Marketplace 1", "Marketplace 2", "Web Propia", "Venta Directa", "Otro"])
        
        if st.button("💾 Guardar Salida"):
            if st.session_state.usuario:
                st.session_state.salidas.append({
                    'producto': producto,
                    'cantidad': cantidad,
                    'canal': canal,
                    'usuario': st.session_state.usuario,
                    'fecha': datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                st.success(f"✅ Registrado: {producto} x {cantidad}")
                st.balloons()
                st.rerun()
            else:
                st.warning("Ingresa tu nombre primero")

# TAB 3: ESTADÍSTICAS
with tab3:
    st.header("Estadísticas")
    
    if not st.session_state.salidas:
        st.info("Sin datos aún")
    else:
        col1, col2, col3, col4 = st.columns(4)
        
        total_unidades = sum([s['cantidad'] for s in st.session_state.salidas])
        productos_vendidos = len(set([s['producto'] for s in st.session_state.salidas]))
        canales = len(set([s['canal'] for s in st.session_state.salidas]))
        
        col1.metric("Total Unidades", total_unidades)
        col2.metric("Productos Vendidos", productos_vendidos)
        col3.metric("Canales", canales)
        col4.metric("Registros", len(st.session_state.salidas))
        
        st.markdown("---")
        
        # Ventas por canal
        st.subheader("Ventas por Canal")
        canales_dict = {}
        for s in st.session_state.salidas:
            canal = s['canal']
            canales_dict[canal] = canales_dict.get(canal, 0) + s['cantidad']
        
        for canal, total in canales_dict.items():
            st.write(f"**{canal}**: {total} unidades")
        
        # Top productos
        st.subheader("Top Productos")
        productos_dict = {}
        for s in st.session_state.salidas:
            prod = s['producto']
            productos_dict[prod] = productos_dict.get(prod, 0) + s['cantidad']
        
        top = sorted(productos_dict.items(), key=lambda x: x[1], reverse=True)[:10]
        for prod, cant in top:
            st.write(f"**{prod}**: {cant} unidades")

# TAB 4: HISTORIAL
with tab4:
    st.header("Historial")
    
    if not st.session_state.salidas:
        st.info("Sin historial")
    else:
        for s in st.session_state.salidas:
            st.write(f"**{s['fecha']}** | {s['producto']} x{s['cantidad']} | {s['canal']} | {s['usuario']}")
        
        # Exportar
        csv_data = "fecha,producto,cantidad,canal,usuario\n"
        for s in st.session_state.salidas:
            csv_data += f"{s['fecha']},{s['producto']},{s['cantidad']},{s['canal']},{s['usuario']}\n"
        
        st.download_button(
            "📥 Descargar CSV",
            csv_data,
            file_name=f"salidas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )

st.markdown("---")
st.markdown("**M&M Hogar © 2026** | Sistema de Registro de Salidas")
