import re
from datetime import date
from decimal import Decimal

from .access import require_location
from .errors import RequestError
from .movement_repository import decrease_stock, increase_stock, product_exists, save_movement


def parse_quantity(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,15}(\.[0-9]{1,3})?", value):
        raise RequestError("Ingresa una cantidad positiva con hasta tres decimales.")
    quantity = Decimal(value)
    if quantity <= 0:
        raise RequestError("La cantidad debe ser mayor que cero.")
    return quantity


def register_movement(connection, actor, *, product_id, location_id, kind, quantity,
                      movement_date, reference):
    require_location(connection, actor, location_id)
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

    if kind == "issue":
        stock = decrease_stock(connection, product_id, location_id, quantity)
        if stock is None:
            raise RequestError("Stock insuficiente para registrar la salida.", 409)
        variation = -quantity
    else:
        stock = increase_stock(connection, product_id, location_id, quantity)
        variation = quantity

    movement = save_movement(
        connection, actor_id=actor["id"], product_id=product_id, location_id=location_id,
        kind=kind, quantity=variation, movement_date=movement_date,
        reference=reference.strip() or None,
    )
    return {
        "id": movement["id"],
        "recordedAt": movement["recorded_at"].isoformat(),
        "balance": str(stock["quantity"]),
    }
