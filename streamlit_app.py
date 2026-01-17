# --- SECCIÓN DE LECTURA DE VENTAS (NUEVO) ---
st.divider()
st.subheader("🕵️ Detector de Ventas - Falabella")

def revisar_pedidos_falabella():
    # Usamos las variables que ya definimos arriba
    params = {
        "Action": "GetOrders",
        "Format": "JSON",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "UserID": F_USER_ID,
        "Version": "1.0",
        "CreatedAfter": "2026-01-01T00:00:00" # Filtramos desde inicio de año para ver si hay algo
    }
    
    query = urllib.parse.urlencode(sorted(params.items()))
    # Usamos F_API_KEY que ya está en tu código
    sig = hmac.new(F_API_KEY.encode('utf-8'), query.encode('utf-8'), hashlib.sha256).hexdigest()
    
    try:
        res = requests.get(f"{F_BASE_URL}?{query}&Signature={sig}")
        return res.json()
    except Exception as e:
        return {"error": str(e)}

if st.button("🔍 Ver Ventas Recientes en Falabella"):
    with st.spinner("Consultando pedidos..."):
        ventas = revisar_pedidos_falabella()
        
        if ventas and "SuccessResponse" in ventas:
            ordenes = ventas["SuccessResponse"]["Body"].get("Orders", [])
            if ordenes:
                st.write(f"Se encontraron **{len(ordenes)}** pedidos.")
                st.json(ordenes) # Esto te mostrará la estructura para que veamos dónde viene el SKU
            else:
                st.info("No hay órdenes nuevas en este periodo.")
        else:
            st.error(f"Error al consultar: {ventas}")
