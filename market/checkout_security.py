# Sistema de seguridad para checkout con tokens temporales
import secrets
from django.utils import timezone
from django.conf import settings


def generate_checkout_token():
    """
    Genera un token único y seguro para checkout
    Returns: str de 43 caracteres (32 bytes en base64url)
    """
    return secrets.token_urlsafe(32)


def validate_ip_similarity(ip1, ip2):
    """
    Compara IPs para determinar si son similares (mismos primeros 3 octetos)
    Útil para redes dinámicas donde cambia el último octeto
    """
    if not ip1 or not ip2:
        return False

    try:
        octets1 = ip1.split('.')[:3]  # Primeros 3 octetos
        octets2 = ip2.split('.')[:3]
        return octets1 == octets2
    except (AttributeError, IndexError):
        return False


def validate_user_agent_compatibility(ua1, ua2):
    """
    Verifica que los user agents sean compatibles (mismo navegador principal)
    """
    if not ua1 or not ua2:
        return False

    # Navegadores principales a verificar
    browsers = ['Chrome', 'Firefox', 'Safari', 'Edge', 'Opera']

    # Verificar si ambos user agents contienen el mismo navegador
    for browser in browsers:
        if browser in ua1 and browser in ua2:
            return True

    return False


def create_token_data(token, request):
    """
    Crea la estructura de datos completa para un token de checkout

    Args:
        token: Token generado
        request: HttpRequest object

    Returns: dict con toda la información del token
    """
    return {
        'token': token,
        'usos': 0,
        'ip_origen': request.META.get('REMOTE_ADDR') if request else '127.0.0.1',
        'user_agent': request.META.get('HTTP_USER_AGENT') if request else 'Django-Test/1.0',
        'created_at': timezone.now(),
        'last_used_at': None,
    }


def is_token_expired(token_data):
    """
    Verifica si un token ha expirado basado en la configuración
    """
    if not token_data or 'created_at' not in token_data:
        return True

    elapsed = timezone.now() - token_data['created_at']
    max_age = settings.CHECKOUT_TOKEN_EXPIRATION
    return elapsed.total_seconds() > max_age


def can_use_token(token_data):
    """
    Verifica si un token puede seguir usándose
    """
    if not token_data:
        return False, "Token no encontrado"

    if is_token_expired(token_data):
        return False, "Token expirado"

    if token_data.get('usos', 0) >= settings.CHECKOUT_TOKEN_MAX_USOS:
        return False, "Límite de usos excedido"

    return True, "Token válido"


def increment_token_usage(token_data):
    """
    Incrementa el contador de usos del token
    """
    token_data['usos'] = token_data.get('usos', 0) + 1
    token_data['last_used_at'] = timezone.now()
    return token_data