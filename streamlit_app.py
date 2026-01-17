def enviar_stock_fala(sku, qty):
    # Estructura exacta requerida por UpdatePriceQuantity en Falabella Chile
    xml_data = '<?xml version="1.0" encoding="UTF-8"?>'
    xml_data += '<Request>'
    xml_data += '  <Product>'
    xml_data += '    <SellerSku>' + str(sku) + '</SellerSku>'
    xml_data += '    <Quantity>' + str(int(qty)) + '</Quantity>'
    xml_data += '  </Product>'
    xml_data += '</Request>'
    
    params = {
        "Action": "UpdatePriceQuantity", # Volvemos a la acción base pero con XML corregido
        "Format": "JSON",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "UserID": F_USER_ID,
        "Version": "1.0"
    }
    
    try:
        url = firmar_fala(params)
        # Importante: Usamos content-type x-www-form-urlencoded y el body plano
        res = requests.post(url, data=xml_data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
        data = res.json()
        
        # Si hay SuccessResponse, Falabella aceptó el paquete
        if "SuccessResponse" in data:
            return True, "OK"
        
        # Si falla, capturamos el mensaje de error para diagnóstico
        msg_error = data.get("ErrorResponse", {}).get("Head", {}).get("ErrorMessage", "Error Desconocido")
        return False, msg_error
    except Exception as e:
        return False, str(e)
