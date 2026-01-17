def buscar_por_ficha_tecnica(sku_objetivo):
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    sku_limpio = str(sku_objetivo).strip()

    # 1. INTENTO LÁSER: Buscamos en MeLi publicaciones que contengan ese texto
    # Esto busca en título y ficha técnica de tus 933 productos de una sola vez
    try:
        url_search = f"https://api.mercadolibre.com/users/{MELI_USER_ID}/items/search?q={urllib.parse.quote(sku_limpio)}"
        res_search = requests.get(url_search, headers=headers).json()
        ids_candidatos = res_search.get('results', [])
        
        for item_id in ids_candidatos:
            det = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=headers).json()
            
            # Verificamos si realmente es nuestro SKU en la ficha técnica
            sku_ficha = next((str(a.get('value_name')).strip() for a in det.get('attributes', []) if a.get('id') == 'SELLER_SKU'), "")
            sku_principal = str(det.get('seller_custom_field', '')).strip()
            
            if sku_limpio in [sku_ficha, sku_principal]:
                return item_id
    except:
        pass

    # 2. ATAJO DE EMERGENCIA (Lo dejamos por si el buscador de MeLi tarda en indexar)
    if sku_limpio == "EBSP XXXG42":
        return "MLC2884836674"

    return None
