elif selected_tab == 2:
    st.subheader("📋 Historial Completo (Entradas + Ventas)")
    
    entradas = cargar_entradas()
    salidas = cargar_salidas()
    
    # Cargar productos para búsqueda por nombre
    productos = cargar_productos()
    productos_dict = {p["sku"]: p["nombre"] for p in productos}
    
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        filtro_tipo = st.selectbox(
            "Tipo de Movimiento:",
            ["TODO", "Entrada 🟢", "Venta 🔴"],
            key="filtro_tipo",
            help="Filtra por tipo de movimiento"
        )
    
    with col_f2:
        filtro_usuario = st.selectbox(
            "Usuario:",
            ["TODO"] + USUARIOS_VALIDOS,
            key="filtro_usuario",
            help="Filtra por usuario"
        )
    
    with col_f3:
        filtro_busqueda = st.text_input(
            "🔍 Buscar SKU o Producto:",
            placeholder="Ej: BS-001 o parte del nombre",
            key="filtro_busqueda",
            help="Busca por SKU o nombre del producto"
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
        historial = [h for h in historial if filtro_busqueda in h["SKU"] or filtro_busqueda in h["Nombre"].upper()]
    
    if historial:
        st.info(f"📋 Total registros: **{len(historial)}** | Total unidades: **{sum(h['Cantidad'] for h in historial)}** UND")
        
        df_historial = pd.DataFrame(historial)
        
        st.dataframe(
            df_historial[[
                "Fecha", "Hora", "Tipo", "SKU", "Nombre", "Cantidad", "Info", "Usuario", "Canal"
            ]],
            use_container_width=True,
            hide_index=True
        )
        
        st.divider()
        
        csv_data = df_historial.to_csv(index=False)
        st.download_button(
            "📥 Descargar CSV (filtrado)",
            csv_data,
            file_name=f"historial_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            use_container_width=True,
            key="download_historial"
        )
    else:
        st.warning("❌ No hay registros que coincidan con los filtros")
    
    st.divider()
    st.subheader("👥 Estadísticas por Usuario")
    
    if historial:
        stats = {}
        for h in historial:
            usuario = h["Usuario"]
            if usuario not in stats:
                stats[usuario] = {"Entradas": 0, "Ventas": 0, "UND Entrada": 0, "UND Venta": 0}
            
            if h["Tipo"] == "🟢 Entrada":
                stats[usuario]["Entradas"] += 1
                stats[usuario]["UND Entrada"] += h["Cantidad"]
            else:
                stats[usuario]["Ventas"] += 1
                stats[usuario]["UND Venta"] += h["Cantidad"]
        
        df_stats = pd.DataFrame(stats).T
        df_stats.columns = ["Entradas", "Ventas", "UND Entrada", "UND Venta"]
        
        st.dataframe(df_stats, use_container_width=True)
    else:
        st.info("📊 Sin datos para mostrar estadísticas")
