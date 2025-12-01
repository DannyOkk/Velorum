from django.core.management.base import BaseCommand
from market.models import Order
from market.email_service import send_payment_confirmation
from market.mercadopago_service import process_payment_notification
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Reenvía emails de confirmación a órdenes pagadas que no los recibieron'

    def add_arguments(self, parser):
        parser.add_argument(
            '--order-id',
            type=int,
            help='ID específico de orden para reenviar email',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Muestra qué órdenes recibirían email sin enviarlo',
        )

    def handle(self, *args, **options):
        order_id = options.get('order_id')
        dry_run = options.get('dry_run', False)
        
        # Filtrar órdenes pagadas sin email enviado
        if order_id:
            orders = Order.objects.filter(
                id=order_id,
                estado='pagado',
                email_confirmacion_enviado=False
            )
        else:
            orders = Order.objects.filter(
                estado='pagado',
                email_confirmacion_enviado=False
            ).order_by('-fecha')
        
        if not orders.exists():
            self.stdout.write(self.style.WARNING('No hay órdenes pendientes de email'))
            return
        
        self.stdout.write(f'\n📧 Encontradas {orders.count()} órdenes sin email de confirmación:\n')
        
        enviados = 0
        fallidos = 0
        
        for order in orders:
            self.stdout.write(f'\n{"[DRY RUN] " if dry_run else ""}Orden #{order.id}:')
            self.stdout.write(f'  • Usuario: {order.usuario.username if order.usuario else "N/A"}')
            self.stdout.write(f'  • Email: {order.usuario.email if order.usuario else "N/A"}')
            self.stdout.write(f'  • Total: ${order.total}')
            self.stdout.write(f'  • Fecha: {order.fecha}')
            
            if dry_run:
                self.stdout.write(self.style.SUCCESS('  ✓ Se enviaría email'))
                continue
            
            if not order.usuario or not order.usuario.email:
                self.stdout.write(self.style.ERROR('  ✗ Sin email asociado - OMITIDO'))
                fallidos += 1
                continue
            
            try:
                # Obtener información del pago (si existe)
                payment_info = {
                    'status': 'approved',
                    'payment_method_id': 'unknown',
                    'payment_id': 'unknown',
                    'transaction_amount': float(order.total)
                }
                
                # Intentar obtener info real del pago si existe
                try:
                    pay = order.pays.filter(estado='completado').first()
                    if pay and pay.metadata:
                        payment_info['payment_id'] = pay.metadata.get('mp_payment_id', 'unknown')
                        payment_info['payment_method_id'] = pay.metadata.get('payment_method_id', 'unknown')
                except:
                    pass
                
                # Enviar email
                email_sent = send_payment_confirmation(order, payment_info)
                
                if email_sent:
                    order.email_confirmacion_enviado = True
                    order.email_confirmacion_fecha = timezone.now()
                    order.save()
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Email enviado exitosamente'))
                    enviados += 1
                else:
                    self.stdout.write(self.style.ERROR('  ✗ Falló el envío (ver logs)'))
                    fallidos += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
                fallidos += 1
        
        self.stdout.write(f'\n{"=" * 60}')
        self.stdout.write(self.style.SUCCESS(f'\n✅ Resumen:'))
        self.stdout.write(f'  • Total procesadas: {orders.count()}')
        self.stdout.write(self.style.SUCCESS(f'  • Enviados: {enviados}'))
        if fallidos > 0:
            self.stdout.write(self.style.ERROR(f'  • Fallidos: {fallidos}'))
        self.stdout.write('')
