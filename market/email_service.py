# Servicio de envío de emails
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import time
import logging

logger = logging.getLogger(__name__)


def send_payment_confirmation(order, payment_info, max_retries=3):
    """
    Envía email de confirmación de pago con sistema de reintentos
    
    Args:
        order: Objeto Order con los datos del pedido
        payment_info: dict con información del pago de Mercado Pago
            - status: estado del pago (approved, pending, rejected, etc.)
            - payment_method_id: método de pago usado
            - payment_id: ID del pago en Mercado Pago
            - transaction_amount: monto de la transacción
        max_retries: número máximo de intentos (default: 3)
    
    Returns:
        True si el email se envió correctamente, False en caso contrario
    """
    # Verificar que la orden tenga un usuario con email
    if not order.usuario or not order.usuario.email:
        logger.warning(f"La orden {order.id} no tiene un usuario con email asociado")
        return False
    
    subject = f'Confirmación de pago - Pedido #{order.id}'
    
    # Contexto para la plantilla
    context = {
        'order': order,
        'user': order.usuario,
        'payment_info': payment_info,
        'order_items': order.detalles.all(),
        'total': order.total,
    }
    
    # Renderizar template HTML
    html_message = render_to_string('emails/payment_confirmation.html', context)
    plain_message = strip_tags(html_message)
    
    # Sistema de reintentos con backoff exponencial
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Intento {attempt}/{max_retries} de envío de email para orden {order.id}")
            
            # Enviar email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[order.usuario.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"✅ Email enviado exitosamente a {order.usuario.email} para pedido #{order.id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en intento {attempt}/{max_retries} enviando email: {str(e)}")
            
            if attempt < max_retries:
                # Espera exponencial: 2^attempt segundos (2s, 4s, 8s)
                wait_time = 2 ** attempt
                logger.info(f"⏳ Reintentando en {wait_time} segundos...")
                time.sleep(wait_time)
            else:
                logger.error(f"❌ Falló el envío de email después de {max_retries} intentos para orden {order.id}")
                return False
    
    return False
