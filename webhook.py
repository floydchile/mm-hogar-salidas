from fastapi import FastAPI, Request, BackgroundTasks
import os
import requests
from supabase import create_client

app = FastAPI()

# Configuración (Usa las mismas variables que ya tienes en Railway)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
MELI_TOKEN = os.getenv("MELI_ACCESS_TOKEN")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.post("/meli-webhook")
async def receive_notification(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    
    # Mercado Libre envía notificaciones de tipo 'orders_v2' o 'items'
    if data.get("topic") == "orders_v2":
        # Ejecutamos la lógica en segundo plano para responder rápido a MeLi (200 OK)
        resource = data.get("resource") # Ejemplo: /orders/12345678
        background_tasks.add_task(procesar_venta, resource)
        
    return {"status": "received"}

def procesar_venta(resource):
    # 1. Consultar el detalle de la orden a MeLi
    headers = {'Authorization': f'Bearer {MELI_TOKEN}'}
    order_url = f"https://api.mercadolibre.com{resource}"
    order_data = requests.get(order_url, headers=headers).json()
    
    # 2. Extraer SKU y Cantidad
    for item in order_data.get('order_items', []):
        sku = item.get('item', {}).get('seller_custom_field') # El SKU que guardaste en MeLi
        cantidad = item.get('quantity')
        
        if sku:
            # 3. Descontar en Supabase usando tu función existente
            supabase.rpc("registrar_salida", {
                "p_sku": sku, 
                "p_cantidad": int(cantidad), 
                "p_canal": "Mercadolibre", 
                "p_usuario": "BOT_MELI"
            }).execute()
