def actualizar_stock_falabella(sku_fala, cantidad):
    # XML ajustado para la acción 'UpdateOffers'
    xml_template = """<?xml version="1.0" encoding="UTF-8"?>
<Offers>
    <Offer>
        <SellerSku>{sku}</SellerSku>
        <Quantity>{qty}</Quantity>
    </Offer>
</Offers>"""
    payload_xml = xml_template.format(sku=sku_fala, qty=int(cantidad))
    
    params = {
        "Action": "UpdateOffers",  # Cambio de acción a la estándar de Mirakl
        "Format": "JSON",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
        "UserID": F_USER_ID,
        "Version": "1.0"
    }
    
    url = firmar_falabella(params)
    try:
        # Enviamos el XML
        res = requests.post(url, data=payload_xml, headers={'Content-Type': 'application/xml'})
        data = res.json()
        
        # En esta acción, la respuesta exitosa suele traer un 'tracking_id'
        if "SuccessResponse" in data or "tracking_id" in str(data):
            return True, "En proceso (UpdateOffers)"
        
        # Si sigue dando E008, intentamos la última opción: 'PostOffers'
        error_code = data.get("ErrorResponse", {}).get("Head", {}).get("ErrorCode", "")
        if error_code == "E008":
            # Intento desesperado con PostOffers (Action común en algunas versiones)
            params["Action"] = "PostOffers"
            url_reintento = firmar_falabella(params)
            res_re = requests.post(url_reintento, data=payload_xml, headers={'Content-Type': 'application/xml'})
            if res_re.status_code == 200:
                return True, "En proceso (PostOffers)"

        return False, data.get("ErrorResponse", {}).get("Head", {}).get("ErrorMessage", "Error de Acción")
    except Exception as e:
        return False, str(e)
