# Comando para probar el sistema de seguridad de checkout
from django.core.management.base import BaseCommand, CommandError
from django.core.cache import cache
from django.test import RequestFactory
from market.models import Order
from market.checkout_security import (
    generate_checkout_token,
    create_token_data,
    validate_ip_similarity,
    validate_user_agent_compatibility,
    can_use_token,
    increment_token_usage
)
from market.views import validate_checkout_access


class Command(BaseCommand):
    help = 'Prueba el sistema de seguridad de checkout con tokens temporales'

    def add_arguments(self, parser):
        parser.add_argument(
            '--order_id',
            type=int,
            help='ID de la orden para probar',
            required=True
        )

        parser.add_argument(
            '--action',
            choices=['create', 'validate', 'test_limits', 'test_security', 'cleanup'],
            default='create',
            help='Acción a realizar'
        )

        parser.add_argument(
            '--token',
            type=str,
            help='Token específico para validar (solo con --action=validate)'
        )

    def handle(self, *args, **options):
        order_id = options['order_id']
        action = options['action']

        try:
            # Verificar que la orden existe
            order = Order.objects.get(id=order_id)
            self.stdout.write(
                self.style.SUCCESS(f'📦 Orden encontrada: #{order.id} - {order.usuario.username if order.usuario else "Sin usuario"}')
            )

        except Order.DoesNotExist:
            raise CommandError(f'❌ Orden {order_id} no encontrada')

        # Ejecutar acción correspondiente
        if action == 'create':
            self._create_token(order)
        elif action == 'validate':
            self._validate_token(order, options.get('token'))
        elif action == 'test_limits':
            self._test_usage_limits(order)
        elif action == 'test_security':
            self._test_security_validations(order)
        elif action == 'cleanup':
            self._cleanup_tokens(order)

    def _create_token(self, order):
        """Crea un token de prueba para la orden"""
        self.stdout.write(self.style.WARNING('\n🔐 Creando token de checkout...'))

        # Simular request
        factory = RequestFactory()
        request = factory.get('/')

        # Generar token
        token = generate_checkout_token()
        token_data = create_token_data(token, request)

        # Guardar en cache
        cache_key = f'checkout_token_{order.id}'
        cache.set(cache_key, token_data, 1800)

        self.stdout.write(self.style.SUCCESS('✅ Token creado exitosamente'))
        self.stdout.write(f'   Token: {token}')
        self.stdout.write(f'   IP origen: {token_data["ip_origen"]}')
        self.stdout.write(f'   User Agent: {token_data["user_agent"][:50] if token_data["user_agent"] else "None"}...')
        self.stdout.write(f'   Cache key: {cache_key}')

        # Mostrar URLs de ejemplo
        self.stdout.write(self.style.WARNING('\n🌐 URLs de ejemplo:'))
        base_url = "http://localhost:3000"
        self.stdout.write(f'   Success: {base_url}/checkout/success?token={token}&order={order.id}')
        self.stdout.write(f'   Failure: {base_url}/checkout/failure?token={token}&order={order.id}')
        self.stdout.write(f'   Pending: {base_url}/checkout/pending?token={token}&order={order.id}')

    def _validate_token(self, order, provided_token=None):
        """Valida un token específico"""
        if not provided_token:
            raise CommandError('❌ Debes proporcionar --token para validar')

        self.stdout.write(self.style.WARNING(f'\n🔍 Validando token: {provided_token[:20]}...'))

        cache_key = f'checkout_token_{order.id}'
        token_data = cache.get(cache_key)

        if not token_data:
            self.stdout.write(self.style.ERROR('❌ Token no encontrado en cache'))
            return

        # Verificar token
        if token_data['token'] != provided_token:
            self.stdout.write(self.style.ERROR('❌ Token no coincide'))
            return

        # Verificar si puede usarse
        can_use, reason = can_use_token(token_data)
        if not can_use:
            self.stdout.write(self.style.ERROR(f'❌ {reason}'))
            return

        # Simular uso
        token_data = increment_token_usage(token_data)
        cache.set(cache_key, token_data, 1800)

        self.stdout.write(self.style.SUCCESS('✅ Token válido y usado'))
        self.stdout.write(f'   Usos actuales: {token_data["usos"]}')
        self.stdout.write(f'   Máximo usos: 3')

    def _test_usage_limits(self, order):
        """Prueba el límite de usos del token"""
        self.stdout.write(self.style.WARNING('\n🔄 Probando límites de uso...'))

        cache_key = f'checkout_token_{order.id}'
        token_data = cache.get(cache_key)

        if not token_data:
            self.stdout.write(self.style.ERROR('❌ No hay token creado. Ejecuta --action=create primero'))
            return

        # Simular múltiples usos
        for i in range(5):  # Intentar 5 usos
            can_use, reason = can_use_token(token_data)
            if can_use:
                token_data = increment_token_usage(token_data)
                cache.set(cache_key, token_data, 1800)
                self.stdout.write(self.style.SUCCESS(f'✅ Uso {i+1}: OK (usos totales: {token_data["usos"]})'))
            else:
                self.stdout.write(self.style.ERROR(f'❌ Uso {i+1}: {reason}'))
                break

    def _test_security_validations(self, order):
        """Prueba las validaciones de seguridad (IP y User Agent)"""
        self.stdout.write(self.style.WARNING('\n🛡️ Probando validaciones de seguridad...'))

        cache_key = f'checkout_token_{order.id}'
        token_data = cache.get(cache_key)

        if not token_data:
            self.stdout.write(self.style.ERROR('❌ No hay token creado. Ejecuta --action=create primero'))
            return

        # Test IP similarity
        test_ips = [
            (token_data['ip_origen'], token_data['ip_origen'], True),  # Misma IP
            (token_data['ip_origen'], '192.168.1.100', True),  # Mismo rango
            (token_data['ip_origen'], '10.0.0.1', False),  # Rango diferente
        ]

        self.stdout.write('IP Similarity Tests:')
        for ip1, ip2, expected in test_ips:
            result = validate_ip_similarity(ip1, ip2)
            status = '✅' if result == expected else '❌'
            self.stdout.write(f'   {status} {ip1} vs {ip2}: {result} (expected: {expected})')

        # Test User Agent compatibility
        ua1 = token_data['user_agent']
        test_uas = [
            (ua1, ua1, True),  # Mismo UA
            (ua1, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36', ua1 and 'Chrome' in ua1),  # Chrome
            (ua1, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0', ua1 and 'Firefox' in ua1),  # Firefox diferente
        ]

        self.stdout.write('\nUser Agent Compatibility Tests:')
        for ua_test, ua_comp, expected in test_uas:
            if ua_test:  # Solo probar si tenemos user agent
                result = validate_user_agent_compatibility(ua_test, ua_comp)
                status = '✅' if result == expected else '❌'
                browser = 'Chrome' if 'Chrome' in ua_comp else 'Firefox' if 'Firefox' in ua_comp else 'Other'
                self.stdout.write(f'   {status} vs {browser}: {result} (expected: {expected})')
            else:
                self.stdout.write('   ⚠️  No User Agent disponible para testing')

    def _cleanup_tokens(self, order):
        """Limpia tokens de la cache"""
        cache_key = f'checkout_token_{order.id}'
        cache.delete(cache_key)
        self.stdout.write(self.style.SUCCESS(f'🧹 Token limpiado: {cache_key}'))