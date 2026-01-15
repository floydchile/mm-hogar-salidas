# --- TAB 4: CONFIGURACIÓN (LÓGICA DE SOLO LECTURA PARA SKU) ---
with t4:
    st.subheader("Configuración de Productos")
    
    c_edit, c_new = st.columns(2)
    
    with c_edit:
        st.markdown("### ✏️ Editar Producto")
        edit_query = st.text_input("Buscar para editar:", key="edit_search").upper()
        if edit_query:
            prods_edit = buscar_productos(edit_query)
            if prods_edit:
                p_to_edit = st.selectbox("Seleccione producto:", prods_edit, format_func=lambda x: f"{x['sku']} - {x['nombre']}")
                
                with st.form("form_edit"):
                    # CAMBIO CLAVE: SKU en modo deshabilitado (Solo lectura)
                    sku_fijo = p_to_edit['sku']
                    st.text_input("SKU (No editable):", value=sku_fijo, disabled=True)
                    
                    new_name = st.text_input("Nombre:", value=p_to_edit['nombre'])
                    new_und = st.number_input("Unidades x Embalaje:", min_value=1, value=int(p_to_edit['und_x_embalaje']))
                    new_costo = st.number_input("Costo Contenedor (CLP):", min_value=0, value=int(p_to_edit['precio_costo_contenedor']))
                    
                    if st.form_submit_button("Actualizar Producto", type="primary", use_container_width=True):
                        try:
                            # Solo enviamos los campos que NO son el SKU
                            supabase.table("productos").update({
                                "nombre": new_name,
                                "und_x_embalaje": new_und,
                                "precio_costo_contenedor": new_costo
                            }).eq("sku", sku_fijo).execute()
                            
                            st.success(f"✅ {sku_fijo} actualizado con éxito")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar: {e}")

    with c_new:
        st.markdown("### 🆕 Nuevo Producto")
        with st.form("crear_nuevo", clear_on_submit=True):
            f_sku = st.text_input("SKU:").upper().strip()
            f_nom = st.text_input("Nombre:")
            f_und = st.number_input("Unidades x Embalaje:", min_value=1, value=1)
            f_costo = st.number_input("Costo Contenedor Inicial (CLP):", min_value=0, value=0)
            
            if st.form_submit_button("Crear Producto", use_container_width=True):
                if f_sku and f_nom:
                    try:
                        supabase.table("productos").insert({
                            "sku": f_sku, "nombre": f_nom, "und_x_embalaje": f_und, 
                            "stock_total": 0, "precio_costo_contenedor": f_costo
                        }).execute()
                        st.success("✅ Creado con éxito")
                        st.rerun()
                    except: st.error("❌ El SKU ya existe.")
