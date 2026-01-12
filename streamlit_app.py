import streamlit as st

st.set_page_config(page_title="M&M Hogar", page_icon="📦", layout="wide")

if 'usuario' not in st.session_state:
    st.session_state.usuario = None
if 'productos' not in st.session_state:
    st.session_state.productos = []
if 'salidas' not in st.session_state:
    st.session_state.salidas = []

with st.sidebar:
    st.title("👤 Usuario")
    usuario = st.text_input("Tu nombre:")
    if usuario:
        st.session_state.usuario = usuario
        st.success(f"¡Bienvenido {usuario}!")

st.title("📦 M&M Hogar - Sistema de Salidas")
st.write("Sistema simple de registro de ventas")

tab1, tab2, tab3 = st.tabs(["Productos", "Registrar Venta", "Historial"])

with tab1:
    st.header("Gestión de Productos")
    sku = st.text_input("SKU")
    nombre = st.text_input("Nombre")
    
    if st.button("Agregar Producto"):
        if sku and nombre:
            st.session_state.productos.append({'sku': sku, 'nombre': nombre})
            st.success("✅ Producto agregado")
            st.rerun()
    
    st.write(f"**Total productos: {len(st.session_state.productos)}**")
    for p in st.session_state.productos:
        st.write(f"- {p['sku']}: {p['nombre']}")

with tab2:
    st.header("Registrar Venta")
    if st.session_state.productos:
        opciones = [f"{p['sku']} - {p['nombre']}" for p in st.session_state.productos]
        producto = st.selectbox("Producto:", opciones)
        cantidad = st.number_input("Cantidad:", min_value=1, value=1)
        canal = st.selectbox("Canal:", ["Mercadolibre", "Falabella", "Walmart", "Hites", "Paris", "Ripley", "Directo - Web", "Directo - WS", "Directo - Retiro"])

        
        if st.button("Guardar Venta"):
            if st.session_state.usuario:
                st.session_state.salidas.append({
                    'producto': producto,
                    'cantidad': cantidad,
                    'canal': canal,
                    'usuario': st.session_state.usuario
                })
                st.success("✅ Venta registrada")
                st.balloons()
                st.rerun()
            else:
                st.warning("Ingresa tu nombre primero")
    else:
        st.warning("Agrega productos primero")

with tab3:
    st.header("Historial de Ventas")
    st.write(f"**Total ventas: {len(st.session_state.salidas)}**")
    for venta in st.session_state.salidas:
        st.write(f"- {venta['producto']} x{venta['cantidad']} | {venta['canal']} | {venta['usuario']}")

