def actualizar_stock_falabella(sku_fala, cantidad):
    # Construcción manual del XML para evitar errores de llaves {}
    payload_xml = '<?xml version="1.0" encoding="UTF-8"?>'
    payload_xml += '<Offers>'
    payload_xml += '  <Offer>'
    payload_xml += '    <SellerSku>' + str(sku_fala) + '</SellerSku>'
    payload_xml += '    <Quantity>' + str(int(cantidad)) + '</Quantity>'
    payload_xml += '  </Offer>'
    payload_xml += '</Offers>'
    
    params = {
        "Action": "UpdateOffers", 
        "Format": "JSON",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "UserID": F_USER_ID,
        "Version": "1.0"
    }
    
    url = firmar_falabella(params)
    try:
        res = requests.post(url, data=payload_xml, headers={'Content-Type': 'application/xml'})
        data = res.json()
        
        # Si Falabella responde con éxito
        if "SuccessResponse" in data:
            return True, "Enviado a Falabella"
        
        # Si da error de acción, intentamos la última alternativa: PostOffers
        if data.get("ErrorResponse", {}).get("Head", {}).get("ErrorCode") == "E008":
            params["Action"] = "PostOffers"
            url_alt = firmar_falabella(params)
            res_alt = requests.post(url_alt, data=payload_xml, headers={'Content-Type': 'application/xml'})
            if res_alt.status_code == 200:
                return True, "Enviado a Falabella (v2)"

        return False, data.get("ErrorResponse", {}).get("Head", {}).get("ErrorMessage", "Error en Falabella")
    except Exception as e:
        return False, str(e)
