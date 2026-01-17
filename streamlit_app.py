def actualizar_stock_falabella(sku_fala, cantidad):
    # XML ajustado al estándar estricto de Falabella/Mirakl
    payload_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <Offers>
        <Offer>
            <SellerSku>{sku_fala}</SellerSku>
            <Quantity>{int(cantidad)}</Quantity>
        </Offer>
    </Offers>"""
    
    params = {
        "Action": "UpdatePriceQuantity", # También puedes probar con 'PostOffers' si este falla
        "Format": "JSON",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "UserID": F_USER_ID,
        "Version": "1.0"
    }
    
    url = firmar_falabella(params)
    try:
        # Importante: Falabella a veces prefiere que el XML vaya en un parámetro llamado 'Offers' o directo en el body
        res = requests.post(url, data=payload_xml, headers={'Content-Type': 'text/xml'})
        
        # LOG PARA DEPURAR (Veremos qué dice Falabella realmente)
        # st.write(res.json()) 
        
        # En Falabella, si hay un 'FeedId' en la respuesta, es que entró a cola de procesamiento
        if res.status_code == 200:
            return True
        return False
    except Exception as e:
        st.error(f"Error técnico: {e}")
        return False
