from datetime import date

from flask import Blueprint, g, request
from psycopg.errors import NumericValueOutOfRange

from .access import require_location, require_session, visible_locations
from .catalog import list_products
from .db import database
from .errors import RequestError
from .movements import register_movement
from .validation import parse_id

inventory = Blueprint("inventory", __name__, url_prefix="/api/inventory")


@inventory.get("/options")
@require_session
def options():
    with database() as connection:
        locations = visible_locations(connection, g.actor)
        products = list_products(connection)
    return {"locations": locations, "products": products}


@inventory.get("/locations/<int:location_id>")
@require_session
def location_inventory(location_id):
    parse_id(location_id)
    try:
        page = int(request.args.get("page", "1"))
        page_size = int(request.args.get("pageSize", "100"))
    except ValueError:
        raise RequestError("Indica una página y un tamaño de página válidos.") from None
    if not 1 <= page <= 2147483647 or not 1 <= page_size <= 100:
        raise RequestError("Indica una página y un tamaño de página válidos.")

    search = request.args.get("q", "").strip()
    if len(search) > 120 or "\0" in search:
        raise RequestError("Ingresa una búsqueda válida de hasta 120 caracteres.")

    kind = request.args.get("kind") or None
    if kind not in (None, "incoming", "receipt", "opening", "issue", "transfer"):
        raise RequestError("Selecciona un tipo de movimiento válido.")
    kinds = ["receipt", "opening"] if kind == "incoming" else [kind] if kind else None
    try:
        start_date = date.fromisoformat(request.args["from"]) if request.args.get("from") else None
        end_date = date.fromisoformat(request.args["to"]) if request.args.get("to") else None
    except ValueError:
        raise RequestError("Selecciona fechas de consulta válidas.") from None
    if start_date and end_date and start_date > end_date:
        raise RequestError("La fecha inicial debe ser anterior o igual a la final.")
    with database() as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        require_location(connection, g.actor, location_id)
        balances = connection.execute("""
            SELECT p.id AS "productId", p.sku, p.name, p.unit, s.quantity::text AS quantity
            FROM stock s JOIN products p ON p.id = s.product_id
            WHERE s.location_id = %s ORDER BY p.name, p.id
        """, (location_id,)).fetchall()
        movements = connection.execute("""
            SELECT m.id, m.kind, m.movement_date::text AS "movementDate",
                   m.recorded_at AS "recordedAt", m.reference, u.username AS actor,
                   p.name AS product, p.unit, d.quantity::text AS quantity
            FROM movement_details d JOIN movements m ON m.id = d.movement_id
            JOIN products p ON p.id = d.product_id JOIN users u ON u.id = m.actor_id
            WHERE d.location_id = %s
              AND (%s::text[] IS NULL OR m.kind = ANY(%s::text[]))
              AND (%s::date IS NULL OR m.movement_date >= %s)
              AND (%s::date IS NULL OR m.movement_date <= %s)
              AND (%s = '' OR strpos(
                  lower(concat_ws(' ', p.name, p.sku, u.username, m.reference)),
                  lower(%s)
              ) > 0)
            ORDER BY m.id DESC, d.product_id
            LIMIT %s OFFSET %s
        """, (location_id, kinds, kinds, start_date, start_date, end_date, end_date,
              search, search, page_size + 1, (page - 1) * page_size)).fetchall()
    for movement in movements:
        movement["recordedAt"] = movement["recordedAt"].isoformat()
    return {
        "balances": balances, "movements": movements[:page_size], "hasMore": len(movements) > page_size
    }


@inventory.post("/receipts")
@require_session
def create_receipt():
    body = request.get_json()
    if not isinstance(body, dict):
        raise RequestError("Envía los datos de la entrada.")
    kind = body.get("kind")
    if kind not in ("receipt", "opening"):
        raise RequestError("Selecciona un tipo de entrada válido.")
    return create_movement(body, kind)


@inventory.post("/issues")
@require_session
def create_issue():
    body = request.get_json()
    if not isinstance(body, dict):
        raise RequestError("Envía los datos de la salida.")
    return create_movement(body, "issue")


@inventory.post("/transfers")
@require_session
def create_transfer():
    body = request.get_json()
    if not isinstance(body, dict):
        raise RequestError("Envía los datos del traslado.")
    return create_movement(body, "transfer", destination_id=parse_id(body.get("destinationId")))


def create_movement(body, kind, *, destination_id=None):
    try:
        with database() as connection:
            result = register_movement(
                connection, g.actor, product_id=parse_id(body.get("productId")),
                location_id=parse_id(body.get("locationId")), kind=kind,
                quantity=body.get("quantity"), movement_date=body.get("movementDate"),
                reference=body.get("reference", ""), destination_id=destination_id,
            )
    except NumericValueOutOfRange:
        raise RequestError("El saldo resultante supera el máximo permitido.", 409) from None
    return result, 201
