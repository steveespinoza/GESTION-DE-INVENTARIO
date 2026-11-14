import re
from datetime import date
from decimal import Decimal

from .access import require_location
from .errors import RequestError
from .receipt_repository import product_exists, save_receipt


def parse_quantity(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,15}(\.[0-9]{1,3})?", value):
        raise RequestError("Ingresa una cantidad positiva con hasta tres decimales.")
    quantity = Decimal(value)
    if quantity <= 0:
        raise RequestError("La cantidad debe ser mayor que cero.")
    return quantity


def register_receipt(connection, actor, *, product_id, location_id, kind, quantity,
                     movement_date, reference):
    require_location(connection, actor, location_id)
    if kind not in ("receipt", "opening"):
        raise RequestError("Selecciona un tipo de entrada válido.")
    if kind == "opening" and actor["role"] != "admin":
        raise RequestError("Solo un administrador puede registrar el saldo inicial.", 403)
    quantity = parse_quantity(quantity)
    try:
        movement_date = date.fromisoformat(movement_date)
    except (TypeError, ValueError):
        raise RequestError("Ingresa una fecha de movimiento válida.") from None
    if not isinstance(reference, str) or len(reference.strip()) > 120:
        raise RequestError("La referencia admite hasta 120 caracteres.")
    if not product_exists(connection, product_id):
        raise RequestError("El producto seleccionado no existe.", 404)

    return save_receipt(
        connection, actor_id=actor["id"], product_id=product_id, location_id=location_id,
        kind=kind, quantity=quantity, movement_date=movement_date,
        reference=reference.strip() or None,
    )
