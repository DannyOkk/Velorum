from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'Test simple para verificar que el envío de emails funciona'

    def add_arguments(self, parser):
        parser.add_argument(
            '--to',
            type=str,
            required=True,
            help='Email destino para el test',
        )

    def handle(self, *args, **options):
        email_destino = options['to']
        
        self.stdout.write(f'\n📧 Enviando email de prueba a: {email_destino}')
        self.stdout.write(f'📮 Servidor SMTP: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}')
        self.stdout.write(f'👤 Usuario: {settings.EMAIL_HOST_USER}')
        self.stdout.write(f'🔐 TLS: {settings.EMAIL_USE_TLS}')
        
        try:
            send_mail(
                subject='Test de Email - Velorum',
                message='Este es un email de prueba desde tu aplicación Django.\n\nSi recibiste este mensaje, el sistema de emails está funcionando correctamente.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email_destino],
                fail_silently=False,
            )
            
            self.stdout.write(self.style.SUCCESS('\n✅ Email enviado exitosamente!'))
            self.stdout.write(f'✅ Revisá la casilla de {email_destino}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error enviando email:'))
            self.stdout.write(self.style.ERROR(f'   {str(e)}'))
            self.stdout.write('\n💡 Verificá:')
            self.stdout.write('   1. EMAIL_HOST_USER y EMAIL_HOST_PASSWORD en .env')
            self.stdout.write('   2. Que el servidor SMTP sea accesible desde Render')
            self.stdout.write('   3. Que las credenciales sean correctas')
