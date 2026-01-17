def enviar_stock_fala(sku, qty):
    # Construcción quirúrgica: Sin llaves, sin f-strings, sin errores.
    piezas = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<Request>',
        '  <Product>',
        '    <SellerSku>', str(sku), '</SellerSku>',
        '    <Quantity>', str(int(qty)), '</Quantity>',
        '  </Product>',
        '</Request>'
    ]
    xml_data = "".join(piezas)
    
    params = {
        "Action": "UpdatePriceQuantity",
        "Format": "JSON",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "UserID": F_USER_ID,
        "Version": "1.0"
    }
    
    try:
        url = firmar_fala(params)
        # Probamos enviando el XML como texto plano, que es lo que menos errores da
        res = requests.post(url, data=xml_data, headers={'Content-Type': 'application/xml'})
        
        # Si la respuesta no es JSON, capturamos el error de texto
        try:
            data = res.json()
        except:
            return False, "Respuesta no-JSON: " + res.text[:50]
        
        if "SuccessResponse" in data:
            return True, "OK"
            
        msg = data.get("ErrorResponse", {}).get("Head", {}).get("ErrorMessage", "Error")
        return False, msg
    except Exception as e:
        return False, "Error de red: " + str(e)
