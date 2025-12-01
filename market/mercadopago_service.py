# Servicio de Mercado Pago
import mercadopago
from django.conf import settings
from django.core.cache import cache
from decimal import Decimal
import os
from .checkout_security import generate_checkout_token, create_token_data

def create_preference(order_data, request=None):
    """
    Crea una preferencia de pago en Mercado Pago con tokens de seguridad
    
    Args:
        order_data: dict con datos del pedido
            - order_id: ID del pedido
            - items: lista de productos
            - payer_email: email del comprador
            - total: total del pedido
        request: HttpRequest object (opcional, para generar tokens de seguridad)
    
    Returns:
        dict con preference_id, init_point y checkout_token
    """
    # Inicializar SDK de Mercado Pago
    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
    
    # Generar token de seguridad si hay request
    checkout_token = None
    if request:
        checkout_token = generate_checkout_token()
        token_data = create_token_data(checkout_token, request)
        
        # Guardar token en cache
        cache_key = f'checkout_token_{order_data["order_id"]}'
        cache.set(cache_key, token_data, settings.CHECKOUT_TOKEN_EXPIRATION)
        
        print(f"🔐 Token de checkout generado: {checkout_token[:20]}...")
    
    # Preparar items para MP
    items = []
    for item in order_data['items']:
        items.append({
            "title": item['name'],
            "quantity": item['quantity'],
            "unit_price": float(item['price']),
            "currency_id": "ARS"  # Pesos argentinos
        })
    
    # Preparar URLs antes del diccionario
    base_url = "https://velorum-front.onrender.com/checkout"
    
    if checkout_token:
        success_url = f"{base_url}/success?token={checkout_token}&order={order_data['order_id']}"
        failure_url = f"{base_url}/failure?token={checkout_token}&order={order_data['order_id']}"
        pending_url = f"{base_url}/pending?token={checkout_token}&order={order_data['order_id']}"
    else:
        success_url = f"{base_url}/success"
        failure_url = f"{base_url}/failure"
        pending_url = f"{base_url}/pending"
    
    preference_data = {
        "items": items,
        "payer": {
            "name": order_data.get('payer_name', 'Test User'),
            "surname": "Test",
            "email": order_data['payer_email'],
            "phone": {
                "area_code": "",
                "number": order_data.get('payer_phone', '')
            },
            "address": {
                "street_name": order_data.get('payer_address', {}).get('street_name', ''),
                "street_number": order_data.get('payer_address', {}).get('street_number', ''),
                "zip_code": order_data.get('payer_address', {}).get('zip_code', '')
            }
        },
        """
        No se puede usar localhost, debe ser
        una url diferente, para probar el pago pueden compartir los
        puertos 3000 y 8000 desde "puertos" a la derecha de "terminal"
        y pegar esa url antes de "/checkout"(la de 3000) y en "notification_url"
        (la de 8000). Tambien necesitan las credenciales, pidanmelas y se las paso (Alexander)
        """
        "back_urls": {
            "success": success_url,
            "failure": failure_url,
            "pending": pending_url
        },
        "auto_return": "approved",
        "external_reference": str(order_data['order_id']),
        "notification_url": "https://velorum-0821.onrender.com/api/market/mp/webhook/",
        "statement_descriptor": "VELORUM"
    }
    
    print(f"📤 Preference data a enviar: {preference_data}")
    
    # Crear preferencia
    preference_response = sdk.preference().create(preference_data)
    
    print(f"📨 Respuesta de MP: {preference_response}")
    
    # Verificar si hubo error
    if preference_response.get("status") != 201:
        error_msg = preference_response.get("response", {}).get("message", "Error desconocido de Mercado Pago")
        print(f"❌ Error de MP: {error_msg}")
        raise Exception(f"Error de Mercado Pago: {error_msg}")
    
    preference = preference_response["response"]
    
    # Verificar que tengamos los datos necesarios
    if "id" not in preference or "init_point" not in preference:
        print(f"❌ Respuesta de MP incompleta: {preference}")
        raise Exception("Mercado Pago no devolvió preference_id o init_point. Verificá tus credenciales.")
    
    return {
        "preference_id": preference["id"],
        "init_point": preference["init_point"],  # URL para redirigir al usuario
        "sandbox_init_point": preference.get("sandbox_init_point", ""),  # URL de prueba
        "checkout_token": checkout_token  # Token de seguridad generado
    }


def process_payment_notification(payment_id):
    """
    Procesa una notificación de pago de Mercado Pago
    
    Args:
        payment_id: ID del pago en Mercado Pago
    
    Returns:
        dict con información del pago
    """
    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
    
    # Obtener información del pago
    payment_info = sdk.payment().get(payment_id)
    payment = payment_info["response"]
    
    return {
        "status": payment["status"],  # approved, pending, rejected, etc.
        "status_detail": payment["status_detail"],
        "order_id": payment.get("external_reference"),  # Nuestro order_id
        "transaction_amount": payment["transaction_amount"],
        "payment_method_id": payment["payment_method_id"],
        "payment_id": payment["id"]
    }
