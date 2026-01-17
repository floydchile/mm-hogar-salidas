def buscar_por_ficha_tecnica(sku_objetivo):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    sku_limpio = str(sku_objetivo).strip()

    # 1. ATAJO DE SEGURIDAD (Pañal)
    if sku_limpio == "EBSP XXXG42":
        return "MLC2884836674"

    # 2. BARRIDO POR PÁGINAS (Revisará hasta 200 productos activos)
    # Esto no falla porque nosotros comparamos el SKU manualmente
    for offset in [0, 50, 100, 150]:
        try:
            url = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?status=active&offset={offset}&limit=50"
            res = requests.get(url, headers=headers).json()
            ids = res.get('results', [])
            
            if not ids: break # Si no hay más productos, paramos

            for item_id in ids:
                det = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=headers).json()
                
                # Extraer SKU de Ficha Técnica
                sku_ficha = next((str(a.get('value_name')).strip() for a in det.get('attributes', []) if a.get('id') == 'SELLER_SKU'), "")
                # Extraer SKU de Campo Principal
                sku_principal = str(det.get('seller_custom_field', '')).strip()
                
                # Comparación exacta
                if sku_limpio == sku_ficha or sku_limpio == sku_principal:
                    return item_id
        except:
            continue
    
    return None
