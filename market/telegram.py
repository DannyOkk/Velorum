import threading
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def _send_text(token, chat_id, text, parse_mode="HTML"):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.exception("Error sending Telegram message: %s", e)
        return False


def send_order_paid_notification(order):
    """Envía una notificación a Telegram sobre un pedido pagado.

    Usa las variables de entorno `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID`
    expuestas en `settings`.
    """
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    chat_id = getattr(settings, "TELEGRAM_CHAT_ID", None)
    if not token or not chat_id:
        logger.debug("Telegram token o chat_id no configurados; omitiendo notificación")
        return

    lines = []
    lines.append("<b>Nuevo pago recibido</b>")
    lines.append(f"Pedido: <code>{order.id}</code>")
    lines.append(f"Estado: <b>{order.estado}</b>")
    try:
        total = float(order.total)
    except Exception:
        total = order.total
    lines.append(f"Total: ${total}")

    if getattr(order, 'usuario', None):
        try:
            lines.append(f"Usuario: {order.usuario.username} ({order.usuario.email})")
        except Exception:
            lines.append("Usuario: N/A")
    else:
        lines.append(f"Invitado: {getattr(order, 'email_invitado', 'N/A')}")

    try:
        detalles = order.detalles.all()
        if detalles:
            lines.append("Items:")
            for d in detalles:
                prod = getattr(d, 'producto', None)
                nombre = prod.nombre if prod else 'Producto'
                lines.append(f"- {nombre} x{d.cantidad} (${d.subtotal})")
    except Exception:
        # No fatal; seguimos
        pass

    text = "\n".join(lines)

    # Enviar en hilo para no bloquear la respuesta del webhook
    t = threading.Thread(target=_send_text, args=(token, chat_id, text))
    t.daemon = True
    t.start()
