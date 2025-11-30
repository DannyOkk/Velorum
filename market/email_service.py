# Servicio de envío de emails
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


def send_payment_confirmation(order, payment_info):
    """
    Envía email de confirmación de pago
    
    Args:
        order: Objeto Order con los datos del pedido
        payment_info: dict con información del pago de Mercado Pago
            - status: estado del pago (approved, pending, rejected, etc.)
            - payment_method_id: método de pago usado
            - payment_id: ID del pago en Mercado Pago
            - transaction_amount: monto de la transacción
    
    Returns:
        True si el email se envió correctamente, False en caso contrario
    """
    try:
        # Verificar que la orden tenga un usuario con email
        if not order.usuario or not order.usuario.email:
            print(f"⚠️ La orden {order.id} no tiene un usuario con email asociado")
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
        
        # Enviar email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.usuario.email],
            html_message=html_message,
            fail_silently=False,
        )
        
        print(f"✅ Email enviado a {order.usuario.email} para el pedido #{order.id}")
        return True
        
    except Exception as e:
        print(f"❌ Error al enviar email: {str(e)}")
        return False
