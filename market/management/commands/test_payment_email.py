# Comando para probar el envío de emails de confirmación de pago
from django.core.management.base import BaseCommand, CommandError
from market.models import Order
from market.email_service import send_payment_confirmation


class Command(BaseCommand):
    help = 'Envía un email de prueba de confirmación de pago para una orden específica'

    def add_arguments(self, parser):
        parser.add_argument(
            '--order_id',
            type=int,
            help='ID de la orden para la cual enviar el email de confirmación',
            required=True
        )

    def handle(self, *args, **options):
        order_id = options['order_id']
        
        try:
            # Buscar la orden
            order = Order.objects.prefetch_related('detalles__producto', 'usuario').get(id=order_id)
            
            self.stdout.write(self.style.SUCCESS(f'\n📦 Orden encontrada: #{order.id}'))
            self.stdout.write(f'   Usuario: {order.usuario.username if order.usuario else "Sin usuario"}')
            self.stdout.write(f'   Email: {order.usuario.email if order.usuario else "Sin email"}')
            self.stdout.write(f'   Total: ${order.total}')
            self.stdout.write(f'   Estado: {order.estado}')
            self.stdout.write(f'   Productos: {order.detalles.count()}')
            
            if not order.usuario:
                raise CommandError('❌ La orden no tiene un usuario asociado')
            
            if not order.usuario.email:
                raise CommandError('❌ El usuario no tiene un email configurado')
            
            # Simular información de pago de Mercado Pago
            payment_info = {
                'status': 'approved',
                'payment_method_id': 'visa',
                'payment_id': 'TEST-123456789',
                'transaction_amount': float(order.total),
                'status_detail': 'accredited'
            }
            
            self.stdout.write(self.style.WARNING('\n📧 Enviando email de confirmación...'))
            self.stdout.write('─' * 60)
            
            # Enviar el email
            success = send_payment_confirmation(order, payment_info)
            
            if success:
                self.stdout.write('─' * 60)
                self.stdout.write(self.style.SUCCESS('\n✅ Email enviado correctamente'))
                self.stdout.write(self.style.SUCCESS(f'   Destinatario: {order.usuario.email}'))
                self.stdout.write(self.style.SUCCESS(f'   Asunto: Confirmación de pago - Pedido #{order.id}\n'))
            else:
                raise CommandError('❌ Hubo un error al enviar el email')
                
        except Order.DoesNotExist:
            raise CommandError(f'❌ No se encontró ninguna orden con ID {order_id}')
        except Exception as e:
            raise CommandError(f'❌ Error: {str(e)}')
